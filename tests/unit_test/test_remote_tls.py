"""Real TLS transport and persistent certificate lifecycle checks."""
import http.client
import socket
import ssl
import os
from datetime import datetime, timedelta, timezone

import pytest

from frontengine.utils.remote import remote_server


def test_phone_links_require_https():
    assert remote_server.remote_url("127.0.0.1", 8770, "abc").startswith("https://")


def test_trusted_tls_rejects_bad_tokens_and_executes_allowed_actions(tmp_path, monkeypatch):
    monkeypatch.setattr(remote_server, "local_address", lambda: "127.0.0.1")
    seen = []
    server = remote_server.RemoteServer(on_action=seen.append, port=0,
                                        certificate_dir=tmp_path / "credentials")
    assert server.start(), server.last_error
    try:
        context = ssl.create_default_context(cafile=str(server.certificate.certificate_path))
        connection = http.client.HTTPSConnection(server.address, server.port,
                                                  context=context, timeout=3)
        connection.request("GET", "/?token=wrong")
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        connection.request("GET", "/?token=" + server.token)
        response = connection.getresponse()
        assert response.status == 200
        assert b"FrontEngine" in response.read()
        connection.request("POST", "/action?token=" + server.token + "&name=hide_all")
        response = connection.getresponse()
        assert response.status == 200
        response.read()
        connection.request("POST", "/action?token=wrong&name=close_all")
        response = connection.getresponse()
        assert response.status == 403
        response.read()
        assert seen == ["hide_all"]
        connection.close()
    finally:
        server.stop()


def test_plain_http_is_never_accepted(tmp_path, monkeypatch):
    monkeypatch.setattr(remote_server, "local_address", lambda: "127.0.0.1")
    server = remote_server.RemoteServer(port=0, certificate_dir=tmp_path)
    assert server.start(), server.last_error
    try:
        with socket.create_connection((server.address, server.port), timeout=3) as connection:
            connection.sendall(b"GET / HTTP/1.0\r\n\r\n")
            try:
                reply = connection.recv(1024)
            except ConnectionResetError:
                reply = b""
            assert b"HTTP/" not in reply
    finally:
        server.stop()


def test_certificate_is_reused_and_renewed_for_expiry_or_changed_address(tmp_path):
    from frontengine.utils.remote.tls_certificate import CertificateStore

    now = datetime.now(timezone.utc)
    store = CertificateStore(tmp_path, clock=lambda: now)
    first = store.provision("127.0.0.1")
    assert store.provision("127.0.0.1").fingerprint == first.fingerprint
    changed = store.provision("192.168.1.100")
    assert changed.fingerprint != first.fingerprint
    store.clock = lambda: now + timedelta(days=366)
    renewed = store.provision("192.168.1.100")
    assert renewed.fingerprint != changed.fingerprint
    assert renewed.expires_at > store.clock()


def test_export_contains_only_public_certificate_and_regeneration_rotates_identity(tmp_path):
    from frontengine.utils.remote.tls_certificate import CertificateStore

    store = CertificateStore(tmp_path / "private")
    first = store.provision("127.0.0.1")
    target = tmp_path / "public.crt"
    store.export(target)
    assert target.read_bytes() == first.certificate_path.read_bytes()
    assert b"PRIVATE KEY" not in target.read_bytes()
    assert store.provision("127.0.0.1", regenerate=True).fingerprint != first.fingerprint


def test_tls_failure_leaves_no_listener(tmp_path, monkeypatch):
    monkeypatch.setattr(remote_server, "local_address", lambda: "127.0.0.1")
    server = remote_server.RemoteServer(port=0, certificate_dir=tmp_path)
    monkeypatch.setattr(server._certificate_store, "provision",
                        lambda *_args: (_ for _ in ()).throw(OSError("key unavailable")))
    assert server.start() is False
    assert server.running is False
    assert "key unavailable" in server.last_error


@pytest.mark.skipif(os.name == "nt", reason="POSIX permission semantics")
def test_private_key_and_directory_are_owner_only(tmp_path):
    from frontengine.utils.remote.tls_certificate import CertificateStore

    store = CertificateStore(tmp_path / "private")
    certificate = store.provision("127.0.0.1")
    assert store.directory.stat().st_mode & 0o777 == 0o700
    assert certificate.key_path.stat().st_mode & 0o777 == 0o600


@pytest.mark.skipif(os.name != "nt", reason="Windows native DACL semantics")
def test_windows_private_key_has_a_protected_current_user_only_dacl(tmp_path):
    import csv
    import ctypes
    import re
    import subprocess
    from ctypes import wintypes
    from frontengine.utils.remote.tls_certificate import CertificateStore

    current_user = subprocess.run([str(__import__("pathlib").Path(os.environ["WINDIR"])
                                         / "System32" / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
                                  capture_output=True, check=True, shell=False, text=True)
    sid = next(csv.reader(current_user.stdout.strip().splitlines()))[1]
    certificate = CertificateStore(tmp_path / "private").provision("127.0.0.1")
    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.GetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p,
                                       wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW.argtypes = [
        ctypes.c_void_p, wintypes.DWORD, wintypes.DWORD, ctypes.POINTER(wintypes.LPWSTR),
        ctypes.POINTER(wintypes.DWORD)]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    size = wintypes.DWORD()
    advapi.GetFileSecurityW(str(certificate.key_path), 4, None, 0, ctypes.byref(size))
    buffer = ctypes.create_string_buffer(size.value)
    assert advapi.GetFileSecurityW(str(certificate.key_path), 4, buffer, size, ctypes.byref(size))
    sddl = wintypes.LPWSTR()
    assert advapi.ConvertSecurityDescriptorToStringSecurityDescriptorW(
        buffer, 1, 4, ctypes.byref(sddl), None)
    try:
        assert sddl.value.startswith("D:P")
        assert re.findall(r"\(([^)]+)\)", sddl.value) == ["A;;FA;;;" + sid]
    finally:
        kernel.LocalFree(ctypes.cast(sddl, ctypes.c_void_p))


def test_untrusted_tls_certificate_is_rejected_by_default_client(tmp_path, monkeypatch):
    monkeypatch.setattr(remote_server, "local_address", lambda: "127.0.0.1")
    server = remote_server.RemoteServer(port=0, certificate_dir=tmp_path)
    assert server.start(), server.last_error
    try:
        connection = http.client.HTTPSConnection(server.address, server.port, timeout=3)
        with pytest.raises(ssl.SSLCertVerificationError):
            connection.request("GET", "/?token=" + server.token)
        connection.close()
    finally:
        server.stop()

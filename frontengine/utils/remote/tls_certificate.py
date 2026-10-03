"""Per-user TLS identity for the phone remote; export only its public certificate."""
from __future__ import annotations

import ctypes
import ipaddress
import os
import socket
import ssl
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Optional

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID


@dataclass(frozen=True)
class Certificate:
    certificate_path: Path
    key_path: Path
    fingerprint: str
    expires_at: datetime


def user_certificate_directory() -> Path:
    """Use an OS user data location, never the working directory or settings export."""
    if os.name == "nt":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    elif __import__("sys").platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / "FrontEngine" / "remote_tls"


def _windows_sid() -> str:
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetCurrentProcess.restype = wintypes.HANDLE
    advapi.OpenProcessToken.argtypes = [wintypes.HANDLE, wintypes.DWORD,
                                       ctypes.POINTER(wintypes.HANDLE)]
    advapi.GetTokenInformation.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p,
                                          wintypes.DWORD, ctypes.POINTER(wintypes.DWORD)]
    advapi.ConvertSidToStringSidW.argtypes = [ctypes.c_void_p,
                                            ctypes.POINTER(wintypes.LPWSTR)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    token = wintypes.HANDLE()
    if not advapi.OpenProcessToken(kernel.GetCurrentProcess(), 8, ctypes.byref(token)):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        size = wintypes.DWORD()
        advapi.GetTokenInformation(token, 1, None, 0, ctypes.byref(size))
        buffer = ctypes.create_string_buffer(size.value)
        if not advapi.GetTokenInformation(token, 1, buffer, size, ctypes.byref(size)):
            raise ctypes.WinError(ctypes.get_last_error())
        sid = ctypes.cast(buffer, ctypes.POINTER(ctypes.c_void_p))[0]
        text = wintypes.LPWSTR()
        if not advapi.ConvertSidToStringSidW(sid, ctypes.byref(text)):
            raise ctypes.WinError(ctypes.get_last_error())
        try:
            return text.value
        finally:
            kernel.LocalFree(ctypes.cast(text, ctypes.c_void_p))
    finally:
        kernel.CloseHandle(token)


def protect_private_path(path: Path) -> None:
    """Fail closed if owner-only POSIX permissions or Windows DACL cannot be set."""
    if path.is_symlink():
        raise OSError("TLS credential paths must not be symbolic links")
    if os.name != "nt":
        path.chmod(0o700 if path.is_dir() else 0o600)
        return
    from ctypes import wintypes

    advapi = ctypes.WinDLL("advapi32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW.argtypes = [
        wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(ctypes.c_void_p), ctypes.c_void_p]
    advapi.SetFileSecurityW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.c_void_p]
    kernel.LocalFree.argtypes = [ctypes.c_void_p]
    inheritance = "OICI" if path.is_dir() else ""
    descriptor = f"D:P(A;{inheritance};FA;;;{_windows_sid()})"
    security = ctypes.c_void_p()
    if not advapi.ConvertStringSecurityDescriptorToSecurityDescriptorW(
            descriptor, 1, ctypes.byref(security), None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        if not advapi.SetFileSecurityW(str(path), 0x80000004, security):
            raise ctypes.WinError(ctypes.get_last_error())
    finally:
        kernel.LocalFree(security)


def _san_names(address: str) -> list:
    names = {"localhost", socket.gethostname(), "127.0.0.1", "::1", address}
    result = []
    for name in sorted(names):
        try:
            result.append(x509.IPAddress(ipaddress.ip_address(name)))
        except ValueError:
            result.append(x509.DNSName(name.encode("idna").decode("ascii")))
    return result


class CertificateStore:
    def __init__(self, directory: Optional[Path] = None,
                 clock: Optional[Callable[[], datetime]] = None) -> None:
        self.directory = Path(directory) if directory is not None else user_certificate_directory()
        self.clock = clock or (lambda: datetime.now(timezone.utc))
        self.certificate_path = self.directory / "certificate.pem"
        self.key_path = self.directory / "private_key.pem"

    def provision(self, address: str, regenerate: bool = False) -> Certificate:
        self.directory.mkdir(mode=0o700, parents=True, exist_ok=True)
        protect_private_path(self.directory)
        if not regenerate:
            try:
                protect_private_path(self.key_path)
                certificate = x509.load_pem_x509_certificate(self.certificate_path.read_bytes())
                names = certificate.extensions.get_extension_for_class(
                    x509.SubjectAlternativeName).value
                if (certificate.not_valid_after_utc > self.clock() + timedelta(days=30)
                        and certificate.not_valid_before_utc <= self.clock()
                        and all(name in names for name in _san_names(address))):
                    self.ssl_context()
                    return self._info(certificate)
            except (OSError, ValueError, ssl.SSLError, x509.ExtensionNotFound):
                pass
        return self._generate(address)

    def _generate(self, address: str) -> Certificate:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "FrontEngine phone remote")])
        now = self.clock()
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
                       .public_key(key.public_key()).serial_number(x509.random_serial_number())
                       .not_valid_before(now - timedelta(minutes=5))
                       .not_valid_after(now + timedelta(days=365))
                       .add_extension(x509.SubjectAlternativeName(_san_names(address)), False)
                       .add_extension(x509.BasicConstraints(ca=False, path_length=None), True)
                       .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), False)
                       .sign(key, hashes.SHA256()))
        self._atomic_write(self.key_path, key.private_bytes(
            serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
            serialization.NoEncryption()))
        self._atomic_write(self.certificate_path, certificate.public_bytes(serialization.Encoding.PEM))
        self.ssl_context()
        return self._info(certificate)

    def _atomic_write(self, path: Path, content: bytes) -> None:
        if path.is_symlink():
            raise OSError("TLS credential paths must not be symbolic links")
        descriptor, name = tempfile.mkstemp(dir=self.directory, prefix=".tls-")
        temporary = Path(name)
        try:
            with os.fdopen(descriptor, "wb") as output:
                protect_private_path(temporary)
                output.write(content)
            temporary.replace(path)
            protect_private_path(path)
        finally:
            temporary.unlink(missing_ok=True)

    def _info(self, certificate: x509.Certificate) -> Certificate:
        fingerprint = ":".join(f"{byte:02X}" for byte in certificate.fingerprint(hashes.SHA256()))
        return Certificate(self.certificate_path, self.key_path, fingerprint,
                           certificate.not_valid_after_utc)

    def ssl_context(self) -> ssl.SSLContext:
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.minimum_version = ssl.TLSVersion.TLSv1_2
        context.load_cert_chain(str(self.certificate_path), str(self.key_path))
        return context

    def export(self, target: Path) -> None:
        target = Path(target)
        if target.resolve() in (self.key_path.resolve(), self.certificate_path.resolve()):
            raise ValueError("Export destination must differ from the TLS credential files")
        target.write_bytes(self.certificate_path.read_bytes())

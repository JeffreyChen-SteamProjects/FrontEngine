"""CoreMIDI public C API with explicit callback and native handle lifetimes."""
import ctypes
import platform


class MIDIParser:
    def __init__(self) -> None:
        self.status = 0
        self.data = []
        self.sysex = False

    def feed(self, raw: bytes) -> list[int]:
        messages = []
        for byte in raw:
            if byte >= 0xF8:
                continue
            if byte & 0x80:
                self.data.clear()
                self.sysex = byte == 0xF0
                self.status = byte if 0x80 <= byte <= 0xEF else 0
                continue
            if self.sysex or not self.status:
                continue
            self.data.append(byte)
            length = 1 if self.status & 0xF0 in (0xC0, 0xD0) else 2
            if len(self.data) == length:
                messages.append(self.status | self.data[0] << 8 |
                                (self.data[1] << 16 if length == 2 else 0))
                self.data.clear()
        return messages


class CoreMIDIInput:
    def __init__(self, callback, library=None, foundation=None) -> None:
        self.callback = callback
        self.client = ctypes.c_uint32()
        self.port = ctypes.c_uint32()
        self.source = 0
        self._callback = None
        self.parser = MIDIParser()
        self.lib = library or ctypes.CDLL('/System/Library/Frameworks/CoreMIDI.framework/CoreMIDI')
        self.foundation = foundation or ctypes.CDLL('/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation')
        self.foundation.CFStringCreateWithCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32]
        self.foundation.CFStringCreateWithCString.restype = ctypes.c_void_p
        self.foundation.CFRelease.argtypes = [ctypes.c_void_p]
        self.lib.MIDIClientCreate.argtypes = [ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p,
                                             ctypes.POINTER(ctypes.c_uint32)]
        self.lib.MIDIInputPortCreate.argtypes = [ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p,
                                                ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32)]
        self.lib.MIDIPortConnectSource.argtypes = [ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        self.lib.MIDIPortDisconnectSource.argtypes = [ctypes.c_uint32, ctypes.c_uint32]
        self.lib.MIDIPortDispose.argtypes = [ctypes.c_uint32]
        self.lib.MIDIClientDispose.argtypes = [ctypes.c_uint32]

    @staticmethod
    def list_devices() -> list[tuple[int, str]]:
        from CoreMIDI import MIDIGetNumberOfSources, MIDIGetSource, MIDIObjectGetStringProperty, kMIDIPropertyDisplayName
        result = []
        for index in range(MIDIGetNumberOfSources()):
            status, name = MIDIObjectGetStringProperty(MIDIGetSource(index), kMIDIPropertyDisplayName, None)
            result.append((index, str(name) if status == 0 else f'MIDI {index + 1}'))
        return result

    def start(self, index: int) -> bool:
        from CoreMIDI import MIDIGetNumberOfSources, MIDIGetSource
        if index < 0 or index >= MIDIGetNumberOfSources():
            raise OSError('No such CoreMIDI source')
        # Keep a real CFStringRef: PyObjC converts CFString values into Python strings.
        name = self.foundation.CFStringCreateWithCString(None, b'FrontEngine', 0x08000100)
        if not name:
            raise OSError('CFStringCreateWithCString failed')
        proc = ctypes.CFUNCTYPE(None, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_void_p)
        self._callback = proc(self._receive)
        try:
            if self.lib.MIDIClientCreate(name, None, None, ctypes.byref(self.client)):
                raise OSError('MIDIClientCreate failed')
            if self.lib.MIDIInputPortCreate(self.client, name, self._callback, None,
                                            ctypes.byref(self.port)):
                raise OSError('MIDIInputPortCreate failed')
            self.source = MIDIGetSource(index)
            if self.lib.MIDIPortConnectSource(self.port, self.source, None):
                raise OSError('MIDIPortConnectSource failed')
            return True
        except Exception:
            self.stop()
            raise
        finally:
            self.foundation.CFRelease(name)

    def _receive(self, packet_list, _context, _source) -> None:
        count = ctypes.c_uint32.from_address(packet_list).value
        address = packet_list + 4
        # MIDIPacketNext aligns packets on ARM; Intel packets are unaligned.
        align = platform.machine().lower() in ('arm64', 'aarch64')
        for _ in range(count):
            length = ctypes.c_uint16.from_address(address + 8).value
            for message in self.parser.feed(ctypes.string_at(address + 10, length)):
                self.callback(message)
            address += 10 + length
            if align:
                address = (address + 3) & ~3

    def stop(self) -> None:
        if self.port.value:
            if self.source:
                self.lib.MIDIPortDisconnectSource(self.port, self.source)
            self.lib.MIDIPortDispose(self.port)
        if self.client.value:
            self.lib.MIDIClientDispose(self.client)
        self.client.value = self.port.value = self.source = 0
        self._callback = None

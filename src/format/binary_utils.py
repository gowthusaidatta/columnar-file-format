import struct

# Little-endian helpers

def write_int(value: int) -> bytes:
    return struct.pack("<i", value)

def write_long(value: int) -> bytes:
    return struct.pack("<q", value)

def write_double(value: float) -> bytes:
    return struct.pack("<d", value)


def read_int(data: bytes) -> int:
    return struct.unpack("<i", data)[0]

def read_long(data: bytes) -> int:
    return struct.unpack("<q", data)[0]

def read_double(data: bytes) -> float:
    return struct.unpack("<d", data)[0]

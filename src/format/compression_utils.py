import zlib

def compress(data: bytes) -> bytes:
    return zlib.compress(data)

def decompress(data: bytes, expected_size: int) -> bytes:
    result = zlib.decompress(data)
    if len(result) != expected_size:
        raise ValueError(
            f"Decompression size mismatch: expected {expected_size}, got {len(result)}"
        )
    return result

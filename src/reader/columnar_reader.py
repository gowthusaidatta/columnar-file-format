from enum import Enum
from typing import List, Dict

from src.format.binary_utils import read_int, read_long, read_double
from src.format.compression_utils import decompress


class ColumnType(Enum):
    INT32 = 1
    FLOAT64 = 2
    STRING = 3


class ColumnMeta:
    def __init__(self, name, ctype, offset, comp_size, raw_size):
        self.name = name
        self.ctype = ctype
        self.offset = offset
        self.comp_size = comp_size
        self.raw_size = raw_size


class ColumnarReader:
    def __init__(self, path: str):
        self.path = path
        self.num_rows = 0
        self.columns: Dict[str, ColumnMeta] = {}

        self._read_header()

    # =========================
    # Header Parsing
    # =========================

    def _read_header(self):
        with open(self.path, "rb") as f:
            magic = f.read(4)
            if magic != b"COLF":
                raise ValueError("Not a COLF file")

            version = f.read(1)
            if version != b"\x01":
                raise ValueError("Unsupported version")

            num_cols = read_int(f.read(4))
            self.num_rows = read_long(f.read(8))

            for _ in range(num_cols):
                name_len = read_int(f.read(4))
                name = f.read(name_len).decode("utf-8")

                ctype = ColumnType(f.read(1)[0])
                offset = read_long(f.read(8))
                comp_size = read_int(f.read(4))
                raw_size = read_int(f.read(4))

                self.columns[name] = ColumnMeta(
                    name, ctype, offset, comp_size, raw_size
                )

    # =========================
    # Column Reading
    # =========================

    def read_columns(self, names: List[str]) -> Dict[str, List]:
        result = {}

        with open(self.path, "rb") as f:
            for name in names:
                meta = self.columns[name]

                f.seek(meta.offset)
                compressed = f.read(meta.comp_size)
                raw = decompress(compressed, meta.raw_size)

                result[name] = self._decode_column(meta, raw)

        return result

    def _decode_column(self, meta: ColumnMeta, data: bytes) -> List:
        if meta.ctype == ColumnType.INT32:
            return [
                read_int(data[i:i + 4])
                for i in range(0, len(data), 4)
            ]

        if meta.ctype == ColumnType.FLOAT64:
            return [
                read_double(data[i:i + 8])
                for i in range(0, len(data), 8)
            ]

        if meta.ctype == ColumnType.STRING:
            offsets = [
                read_int(data[i:i + 4])
                for i in range(0, self.num_rows * 4, 4)
            ]

            strings = []
            start = self.num_rows * 4
            prev = 0

            for end in offsets:
                strings.append(
                    data[start + prev:start + end].decode("utf-8")
                )
                prev = end

            return strings

        raise ValueError("Unsupported column type")

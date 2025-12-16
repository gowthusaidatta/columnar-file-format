import csv
from collections import OrderedDict
from enum import Enum
from typing import List

from src.format.binary_utils import write_int, write_long, write_double
from src.format.compression_utils import compress


class ColumnType(Enum):
    INT32 = 1
    FLOAT64 = 2
    STRING = 3


class ColumnarWriter:
    def __init__(self):
        self.schema = []              # list of (column_name, ColumnType)
        self.columns = OrderedDict()  # column_name -> list[str]
        self.row_count = 0

    # =========================
    # Public API
    # =========================

    def write(self, csv_path: str, output_path: str):
        self._read_csv(csv_path)
        self._infer_schema()

        raw_columns = self._encode_columns()
        compressed_columns = [compress(col) for col in raw_columns]

        self._write_file(output_path, raw_columns, compressed_columns)

    # =========================
    # CSV + Schema
    # =========================

    def _read_csv(self, csv_path: str):
        with open(csv_path, newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            headers = next(reader)

            for h in headers:
                self.columns[h] = []

            for row in reader:
                if len(row) != len(headers):
                    raise ValueError("Malformed CSV row")

                for h, value in zip(headers, row):
                    self.columns[h].append(value)

                self.row_count += 1

    def _infer_schema(self):
        for name, values in self.columns.items():
            self.schema.append((name, self._infer_column_type(values)))

    def _infer_column_type(self, values):
        try:
            for v in values:
                int(v)
            return ColumnType.INT32
        except ValueError:
            pass

        try:
            for v in values:
                float(v)
            return ColumnType.FLOAT64
        except ValueError:
            pass

        return ColumnType.STRING

    # =========================
    # Encoding
    # =========================

    def _encode_columns(self) -> List[bytes]:
        encoded = []

        for name, ctype in self.schema:
            values = self.columns[name]

            if ctype == ColumnType.INT32:
                encoded.append(self._encode_int(values))
            elif ctype == ColumnType.FLOAT64:
                encoded.append(self._encode_float(values))
            elif ctype == ColumnType.STRING:
                encoded.append(self._encode_string(values))
            else:
                raise ValueError("Unsupported column type")

        return encoded

    def _encode_int(self, values):
        buf = bytearray()
        for v in values:
            buf.extend(write_int(int(v)))
        return bytes(buf)

    def _encode_float(self, values):
        buf = bytearray()
        for v in values:
            buf.extend(write_double(float(v)))
        return bytes(buf)

    def _encode_string(self, values):
        offsets = bytearray()
        data = bytearray()
        current_offset = 0

        for v in values:
            encoded = v.encode("utf-8")
            data.extend(encoded)
            current_offset += len(encoded)
            offsets.extend(write_int(current_offset))

        return bytes(offsets + data)

    # =========================
    # File Writing
    # =========================

    def _write_file(self, output_path, raw_cols, comp_cols):
        with open(output_path, "wb") as f:
            # Magic + version
            f.write(b"COLF")
            f.write(b"\x01")

            # Counts
            f.write(write_int(len(self.schema)))
            f.write(write_long(self.row_count))

            # Calculate header size
            header_size = 4 + 1 + 4 + 8
            for name, _ in self.schema:
                header_size += 4 + len(name.encode("utf-8")) + 1 + 8 + 4 + 4

            # Compute column offsets
            offsets = []
            current_offset = header_size
            for comp in comp_cols:
                offsets.append(current_offset)
                current_offset += len(comp)

            # Write schema + metadata
            for (name, ctype), raw, comp, offset in zip(
                self.schema, raw_cols, comp_cols, offsets
            ):
                name_bytes = name.encode("utf-8")
                f.write(write_int(len(name_bytes)))
                f.write(name_bytes)
                f.write(bytes([ctype.value]))
                f.write(write_long(offset))
                f.write(write_int(len(comp)))
                f.write(write_int(len(raw)))

            # Write column blocks
            for comp in comp_cols:
                f.write(comp)

# COLF File Format Specification

## Overview

COLF (Columnar File Format) is a binary file format designed for efficient columnar storage of tabular data with per-column compression and selective column reads.

**Version:** 1.0  
**Endianness:** Little-endian  
**Compression:** zlib

---

## File Structure

```
┌─────────────────────────────────┐
│         File Header             │
│  - Magic Number (4 bytes)       │
│  - Version (1 byte)              │
│  - Column Count (4 bytes)        │
│  - Row Count (8 bytes)           │
├─────────────────────────────────┤
│      Column Metadata (×N)       │
│  For each column:                │
│  - Name Length (4 bytes)         │
│  - Name (variable UTF-8)         │
│  - Type (1 byte)                 │
│  - Offset (8 bytes)              │
│  - Compressed Size (4 bytes)     │
│  - Uncompressed Size (4 bytes)   │
├─────────────────────────────────┤
│    Column Data Blocks (×N)      │
│  - Compressed binary data        │
│    (one block per column)        │
└─────────────────────────────────┘
```

---

## Binary Layout Details

### 1. File Header

| Field            | Type     | Size    | Description                          |
|------------------|----------|---------|--------------------------------------|
| Magic Number     | char[4]  | 4 bytes | Always `COLF` (0x43 4F 4C 46)       |
| Version          | uint8    | 1 byte  | Format version (currently 0x01)      |
| Column Count     | int32    | 4 bytes | Number of columns in the dataset     |
| Row Count        | int64    | 8 bytes | Total number of rows                 |

**Total Header Size:** 17 bytes (fixed)

---

### 2. Column Metadata Section

For **each column** (repeated `Column Count` times):

| Field              | Type      | Size         | Description                                    |
|--------------------|-----------|--------------|------------------------------------------------|
| Name Length        | int32     | 4 bytes      | Length of column name in bytes                 |
| Name               | UTF-8     | variable     | Column name (UTF-8 encoded string)             |
| Data Type          | uint8     | 1 byte       | Type code: 1=INT32, 2=FLOAT64, 3=STRING        |
| Absolute Offset    | int64     | 8 bytes      | Byte offset from file start to column data     |
| Compressed Size    | int32     | 4 bytes      | Size of compressed column block in bytes       |
| Uncompressed Size  | int32     | 4 bytes      | Original size before compression               |

**Size per column:** 17 + len(name) bytes

---

### 3. Column Data Blocks

Each column's data is stored as a **separate compressed binary block**.

The blocks are written sequentially in the order defined in the metadata section.

#### Data Type Encoding

##### **INT32 (Type Code: 1)**

- Each integer value is encoded as a **little-endian signed 32-bit integer** (4 bytes)
- Total uncompressed size: `row_count × 4` bytes

**Example:**
```
Value: 42
Binary: 0x2A 0x00 0x00 0x00
```

##### **FLOAT64 (Type Code: 2)**

- Each floating-point value is encoded as a **little-endian IEEE 754 double-precision float** (8 bytes)
- Total uncompressed size: `row_count × 8` bytes

**Example:**
```
Value: 98.5
Binary: 0x00 0x00 0x00 0x00 0x00 0xA0 0x58 0x40
```

##### **STRING (Type Code: 3)**

Strings use a two-part encoding scheme:

1. **Offset Array:** An array of `row_count` INT32 values representing cumulative byte offsets
2. **Data Section:** Concatenated UTF-8 encoded string bytes

**Structure:**
```
┌──────────────────────────┐
│  Offset Array            │
│  (row_count × 4 bytes)   │
├──────────────────────────┤
│  Concatenated Strings    │
│  (UTF-8 bytes)           │
└──────────────────────────┘
```

**Example (3 rows: "Alice", "Bob", "Charlie"):**
```
Offsets:
  5 (end of "Alice")
  8 (end of "Bob")
  15 (end of "Charlie")

Binary Offsets:
  0x05 0x00 0x00 0x00
  0x08 0x00 0x00 0x00
  0x0F 0x00 0x00 0x00

Data:
  "Alice" = 0x41 0x6C 0x69 0x63 0x65
  "Bob"   = 0x42 0x6F 0x62
  "Charlie" = 0x43 0x68 0x61 0x72 0x6C 0x69 0x65
```

To decode:
- Read `row_count` INT32 offsets
- Extract each string using: `data[prev_offset : current_offset]`

---

## Compression

- **Algorithm:** zlib (RFC 1950)
- **Granularity:** Per-column (each column compressed independently)
- **Level:** Default (usually level 6)

**Benefits:**
- Columns can be decompressed independently
- Enables selective column reads without decompressing entire file

---

## Selective Column Reads (Column Pruning)

The format supports efficient selective reads through:

1. **Absolute Offsets:** Each column's metadata stores its exact byte position in the file
2. **Independent Compression:** Columns can be decompressed individually
3. **Seek-Based Access:** Reader can jump directly to required columns using `seek()`

**Algorithm:**
```
1. Read and parse file header
2. Read all column metadata
3. For each requested column:
   a. Seek to column's absolute offset
   b. Read compressed_size bytes
   c. Decompress to uncompressed_size bytes
   d. Decode based on data type
```

**Performance:** Reading 1 column from a 100-column file reads only ~1% of the data.

---

## Design Rationale

### Why Columnar?
- **Analytics workloads** typically access few columns across many rows
- Column-wise storage enables reading only required columns
- Better compression ratios (similar data types compress well)

### Why Absolute Offsets?
- Enables direct seeking to any column
- No need to read/skip preceding columns
- Supports random access patterns

### Why Per-Column Compression?
- Independent decompression reduces overhead
- Trade-off: slightly worse compression than whole-file compression
- Benefit: enables column pruning (key feature)

### Why Offset-Based Strings?
- Variable-length data requires special handling
- Offset array enables O(1) string lookup by row index
- Avoids scanning for delimiters

---

## Compatibility and Extensibility

### Version Management
- The version byte allows future format evolution
- Readers should check version and reject unsupported formats

### Adding New Types
Future versions could support:
- INT64, INT16, INT8
- FLOAT32
- BOOLEAN (bit-packed)
- DATE/TIMESTAMP
- DECIMAL (fixed-point)
- BINARY (raw bytes)

### Metadata Extensions
Future enhancements could include:
- Statistics (min/max/null count per column)
- Bloom filters for selective scans
- Dictionary encoding for low-cardinality strings
- Run-length encoding (RLE)

---

## Implementation Notes

### Writing COLF Files

1. Parse input data (e.g., CSV)
2. Infer or specify schema
3. Encode each column into binary format
4. Compress each column with zlib
5. Calculate absolute offsets (after header + metadata)
6. Write header
7. Write column metadata
8. Write compressed column blocks

### Reading COLF Files

1. Read magic number and validate format
2. Read version and check compatibility
3. Read column count and row count
4. Read all column metadata into memory
5. For selective reads:
   - Look up metadata for requested columns
   - Seek to each column's offset
   - Read and decompress
   - Decode based on type

### Error Handling

Readers should validate:
- Magic number matches `COLF`
- Version is supported
- File size matches expected structure
- Decompressed size matches metadata
- UTF-8 strings are valid

---

## Example File Layout

### Sample Data
```csv
id,score,name
1,98.5,Alice
2,87.0,Bob
3,91.2,Charlie
```

### Resulting COLF File Structure

```
Offset | Content                              | Size
-------|--------------------------------------|-------
0x00   | Magic: "COLF"                        | 4
0x04   | Version: 0x01                        | 1
0x05   | Column Count: 3                      | 4
0x09   | Row Count: 3                         | 8
-------|--------------------------------------|-------
0x11   | Column 0 Metadata (id):              |
       |   Name Length: 2                     | 4
       |   Name: "id"                         | 2
       |   Type: INT32 (1)                    | 1
       |   Offset: 0x5A                       | 8
       |   Compressed Size: X                 | 4
       |   Uncompressed Size: 12              | 4
-------|--------------------------------------|-------
0x2A   | Column 1 Metadata (score):           |
       |   Name Length: 5                     | 4
       |   Name: "score"                      | 5
       |   Type: FLOAT64 (2)                  | 1
       |   Offset: 0x5A + X                   | 8
       |   Compressed Size: Y                 | 4
       |   Uncompressed Size: 24              | 4
-------|--------------------------------------|-------
0x46   | Column 2 Metadata (name):            |
       |   Name Length: 4                     | 4
       |   Name: "name"                       | 4
       |   Type: STRING (3)                   | 1
       |   Offset: 0x5A + X + Y               | 8
       |   Compressed Size: Z                 | 4
       |   Uncompressed Size: 27              | 4
-------|--------------------------------------|-------
0x5A   | Compressed Column Data (id)          | X bytes
0x5A+X | Compressed Column Data (score)       | Y bytes
...    | Compressed Column Data (name)        | Z bytes
```

---

## Performance Characteristics

### Write Performance
- **Bottleneck:** Compression (CPU-bound)
- **Optimization:** Parallel compression of columns (not implemented in reference)

### Read Performance
- **Full scan:** Similar to row-based formats (must decompress all columns)
- **Selective read:** **Significantly faster** (only decompress needed columns)
- **Random row access:** Not optimized (requires decompressing entire column)

### Storage Efficiency
- Compression ratios depend on data characteristics
- Typical: 2-10× compression for mixed data types
- Homogeneous data (e.g., sorted integers) compresses better

---

## Comparison to Real-World Formats

| Feature              | COLF      | Parquet   | ORC       |
|----------------------|-----------|-----------|-----------|
| Columnar             | ✅        | ✅        | ✅        |
| Compression          | zlib      | Multiple  | Multiple  |
| Nested Types         | ❌        | ✅        | ✅        |
| Predicate Pushdown   | ❌        | ✅        | ✅        |
| Statistics           | ❌        | ✅        | ✅        |
| Encoding Schemes     | 1         | Many      | Many      |
| Production Ready     | ❌ (Demo) | ✅        | ✅        |

COLF is a **simplified educational implementation** demonstrating core columnar storage principles.

---

## License

This specification is part of the COLF project, created for educational purposes.

---

## References

- Apache Parquet Format Specification
- Apache ORC Format Specification
- RFC 1950 (zlib Compression)
- IEEE 754 Floating Point Standard

---

**Specification Version:** 1.0  
**Last Updated:** December 16, 2025  
**Author:** V V Satya Sai Datta Manikanta Gowthu

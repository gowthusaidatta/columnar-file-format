import sys
import os
import csv

# add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.reader.columnar_reader import ColumnarReader


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: colf_to_csv <input.colf> <output.csv>")
        sys.exit(1)

    colf_path = sys.argv[1]
    csv_path = sys.argv[2]

    reader = ColumnarReader(colf_path)
    data = reader.read_columns(list(reader.columns.keys()))

    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        headers = list(data.keys())
        writer.writerow(headers)

        for i in range(reader.num_rows):
            writer.writerow([data[h][i] for h in headers])

    print(f"Wrote {csv_path}")

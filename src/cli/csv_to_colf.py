import sys
import os

# add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from src.writer.columnar_writer import ColumnarWriter


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: csv_to_colf <input.csv> <output.colf>")
        sys.exit(1)

    csv_path = sys.argv[1]
    colf_path = sys.argv[2]

    ColumnarWriter().write(csv_path, colf_path)
    print(f"Wrote {colf_path}")

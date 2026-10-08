"""commit-msg hook: the commit header must be in English."""

import sys
from pathlib import Path


def main(path: str) -> int:
    header = Path(path).read_text(encoding="utf-8").splitlines()[0] if Path(path).stat().st_size else ""
    if header.isascii():
        return 0
    sys.stderr.write(f"Commit header must be in English: {header}\n")
    return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1]))

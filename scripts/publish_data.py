#!/usr/bin/env python3
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "data" / "derived"
PUBLIC_DIR = ROOT / "public" / "data"


def main():
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    for json_file in SOURCE_DIR.glob("*.json"):
        shutil.copy2(json_file, PUBLIC_DIR / json_file.name)
    print(f"Published JSON to {PUBLIC_DIR}")


if __name__ == "__main__":
    main()

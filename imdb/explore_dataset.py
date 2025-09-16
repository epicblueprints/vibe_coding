#!/usr/bin/env python3
"""Quick utilities to inspect TSV datasets in a directory."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

# Maximize CSV field size to handle very long TSV columns (e.g., character lists).
try:
    csv.field_size_limit(sys.maxsize)
except OverflowError:
    # Some platforms cap the limit below sys.maxsize; settle near 32-bit max.
    csv.field_size_limit(2**31 - 1)

DEFAULT_SAMPLE_ROWS = 5


def iter_dataset_files(path: Path) -> Iterable[Path]:
    """Yield dataset files sorted by name."""
    if not path.exists():
        raise FileNotFoundError(f"Dataset directory '{path}' does not exist")
    if not path.is_dir():
        raise NotADirectoryError(f"Dataset path '{path}' is not a directory")
    for child in sorted(path.iterdir()):
        if child.is_file():
            yield child


def summarize_file(path: Path, sample_rows: int, count_rows: bool) -> str:
    """Return a formatted summary string for a single TSV file."""
    lines: List[str] = []
    lines.append(f"=== {path.name} ===")
    size_bytes = path.stat().st_size
    size_mb = size_bytes / (1024 * 1024)
    lines.append(f"Size: {size_bytes:,} bytes ({size_mb:.2f} MiB)")

    with path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        try:
            header = next(reader)
        except StopIteration:
            lines.append("File is empty")
            return "\n".join(lines)
        lines.append(f"Columns ({len(header)}): {', '.join(header)}")

        if sample_rows > 0:
            sample: List[Sequence[str]] = []
            for _ in range(sample_rows):
                try:
                    sample.append(next(reader))
                except StopIteration:
                    break
            if sample:
                lines.append("Sample rows:")
                for row_index, row in enumerate(sample, start=1):
                    preview = ", ".join(f"{col}={value}" for col, value in zip(header, row))
                    lines.append(f"  {row_index}. {preview}")
            else:
                lines.append("File has header but no data rows")

        if count_rows:
            total_rows = 0
            for _ in reader:
                total_rows += 1
            lines.append(f"Total data rows (excluding header): {total_rows:,}")

    return "\n".join(lines)


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Explore TSV files in an IMDB dataset directory")
    parser.add_argument(
        "dataset_dir",
        nargs="?",
        default=None,
        help="Directory containing the dataset files (defaults to 'datasets' if it exists, otherwise 'dataset')",
    )
    parser.add_argument(
        "--sample-rows",
        type=int,
        default=DEFAULT_SAMPLE_ROWS,
        help="Number of data rows to preview from each file (default: %(default)s)",
    )
    parser.add_argument(
        "--count-rows",
        action="store_true",
        help="Count total data rows in each file (may take a while)",
    )
    args = parser.parse_args(argv)

    if args.dataset_dir is None:
        # Prefer the plural directory name if present, match user's expectation otherwise.
        candidate_dirs = [Path("datasets"), Path("dataset")]
        for candidate in candidate_dirs:
            if candidate.exists():
                dataset_dir = candidate
                break
        else:
            parser.error("Could not locate a dataset directory. Please specify the path explicitly.")
    else:
        dataset_dir = Path(args.dataset_dir)

    for file_path in iter_dataset_files(dataset_dir):
        print(summarize_file(file_path, args.sample_rows, args.count_rows))
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

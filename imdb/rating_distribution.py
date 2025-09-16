#!/usr/bin/env python3
"""Compute histogram of IMDb title ratings.

The script reads `title.ratings.tsv` (or a supplied TSV) and counts how many
records fall within user-specified rating buckets.
"""
from __future__ import annotations

import argparse
import csv
import sys
from decimal import Decimal, InvalidOperation, getcontext
from pathlib import Path
from typing import List, Sequence

# Ratings are simple decimals, so standard precision suffices.
getcontext().prec = 28


def parse_decimal(value: str, *, name: str) -> Decimal:
    """Parse a string into a Decimal, raising argparse-friendly errors."""
    try:
        return Decimal(value)
    except InvalidOperation as exc:  # pragma: no cover - defensive
        raise argparse.ArgumentTypeError(f"{name} must be a finite number") from exc


def build_buckets(min_rating: Decimal, max_rating: Decimal, step: Decimal) -> List[Decimal]:
    """Return bucket boundaries [start0, end0, start1, end1, ...]."""
    if step <= 0:
        raise ValueError("Step size must be positive")
    if min_rating >= max_rating:
        raise ValueError("Minimum rating must be less than maximum rating")

    boundaries: List[Decimal] = []
    current = min_rating
    while current < max_rating:
        next_edge = current + step
        if next_edge > max_rating:
            next_edge = max_rating
        boundaries.extend([current, next_edge])
        if next_edge == current:
            # Guard against zero progress due to subnormal step sizes.
            raise ValueError("Step size too small to progress")
        current = next_edge
    return boundaries


def summarize_distribution(
    dataset_path: Path,
    min_rating: Decimal,
    max_rating: Decimal,
    step: Decimal,
) -> None:
    """Read the TSV and print bucket counts."""
    boundaries = build_buckets(min_rating, max_rating, step)
    bucket_count = len(boundaries) // 2
    counts: List[int] = [0] * bucket_count
    underflow = 0
    overflow = 0

    with dataset_path.open("r", encoding="utf-8", errors="replace", newline="") as handle:
        reader = csv.reader(handle, delimiter="\t")
        header = next(reader, None)
        if not header:
            print("Dataset is empty")
            return
        try:
            rating_index = header.index("averageRating")
        except ValueError as exc:
            raise RuntimeError("averageRating column not found") from exc

        for row in reader:
            if len(row) <= rating_index:
                continue
            rating_text = row[rating_index]
            if rating_text == "\\N":
                continue
            try:
                rating = Decimal(rating_text)
            except InvalidOperation:
                continue
            if rating < min_rating:
                underflow += 1
                continue
            if rating > max_rating:
                overflow += 1
                continue
            # Exact max values should fall into the final bucket.
            if rating == max_rating:
                counts[-1] += 1
                continue
            index = int((rating - min_rating) // step)
            if index < 0:
                underflow += 1
            elif index >= bucket_count:
                overflow += 1
            else:
                counts[index] += 1

    for bucket_index in range(bucket_count):
        start = boundaries[2 * bucket_index]
        end = boundaries[2 * bucket_index + 1]
        print(f"[{start}, {end})\t{counts[bucket_index]}")

    print(f"< {min_rating}\t{underflow}")
    print(f"> {max_rating}\t{overflow}")


def main(argv: Sequence[str]) -> int:
    parser = argparse.ArgumentParser(description="Compute rating distribution buckets from a TSV file.")
    parser.add_argument(
        "--dataset",
        type=Path,
        default=Path("datasets") / "title.ratings.tsv",
        help="Path to the TSV file (default: datasets/title.ratings.tsv)",
    )
    parser.add_argument("--min", dest="min_rating", default="0", help="Minimum rating inclusive (default: 0)")
    parser.add_argument("--max", dest="max_rating", default="10", help="Maximum rating inclusive (default: 10)")
    parser.add_argument(
        "--step",
        dest="step",
        default="0.5",
        help="Bucket size (default: 0.5). Buckets span [min, max) with explicit inclusion of max.",
    )
    args = parser.parse_args(argv)

    min_rating = parse_decimal(str(args.min_rating), name="min")
    max_rating = parse_decimal(str(args.max_rating), name="max")
    step = parse_decimal(str(args.step), name="step")

    try:
        summarize_distribution(args.dataset, min_rating, max_rating, step)
    except ValueError as exc:
        parser.error(str(exc))

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))

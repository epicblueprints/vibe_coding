#!/usr/bin/env python3
"""Analyze relationship between movie title initials and ratings for Indian releases."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Dict, Tuple

import pandas as pd

from analysis_utils import (
    DatasetPaths,
    detect_dataset_paths,
    extract_first_letter,
    load_indian_titles,
    load_movie_basics,
    load_ratings,
)


def compute_anova_components(group_stats: pd.DataFrame) -> Tuple[float, float, float]:
    total_count = int(group_stats["count"].sum())
    overall_mean = group_stats["sum"].sum() / total_count
    ss_between = float(((group_stats["mean"] - overall_mean) ** 2 * group_stats["count"]).sum())
    ss_within = float((group_stats["sum_sq"] - group_stats["sum"] ** 2 / group_stats["count"]).sum())
    ss_total = ss_between + ss_within
    return ss_between, ss_within, ss_total


def analyze(dataset_paths: DatasetPaths, min_votes: int) -> Dict[str, pd.DataFrame | Dict[str, float]]:
    indian_titles = load_indian_titles(dataset_paths.akas)
    if indian_titles.empty:
        raise RuntimeError("No Indian titles found in akas dataset")

    basics = load_movie_basics(dataset_paths.basics)
    ratings = load_ratings(dataset_paths.ratings, min_votes)

    merged = (
        ratings.merge(basics, on="tconst", how="inner")
        .merge(indian_titles, on="tconst", how="inner")
    )
    if merged.empty:
        raise RuntimeError("No Indian movies matched the rating and basics filters")

    merged["chosenTitle"] = merged["regionalTitle"].fillna(merged["primaryTitle"])
    merged["firstLetter"] = merged["chosenTitle"].map(extract_first_letter)
    merged = merged[merged["firstLetter"].notna()].copy()
    merged["ratingSq"] = merged["averageRating"] ** 2

    merged["weightedRating"] = merged["averageRating"] * merged["numVotes"]

    group = merged.groupby("firstLetter").agg(
        count=("averageRating", "size"),
        mean=("averageRating", "mean"),
        median=("averageRating", "median"),
        sum=("averageRating", "sum"),
        sum_sq=("ratingSq", "sum"),
        total_votes=("numVotes", "sum"),
        weighted_rating=("weightedRating", "sum"),
    )

    group["weighted_mean"] = group["weighted_rating"] / group["total_votes"]

    ss_between, ss_within, ss_total = compute_anova_components(group)
    k = len(group)
    n = int(group["count"].sum())

    stats = {
        "movie_count": n,
        "letter_count": k,
        "overall_mean": float(merged["averageRating"].mean()),
        "overall_weighted_mean": float(merged["weightedRating"].sum() / merged["numVotes"].sum()),
        "ss_between": ss_between,
        "ss_within": ss_within,
        "ss_total": ss_total,
        "eta_squared": ss_between / ss_total if ss_total > 0 else math.nan,
        "df_between": k - 1,
        "df_within": n - k,
    }
    if stats["df_between"] > 0 and stats["df_within"] > 0 and ss_within > 0:
        ms_between = ss_between / stats["df_between"]
        ms_within = ss_within / stats["df_within"]
        stats["f_statistic"] = ms_between / ms_within
    else:
        stats["f_statistic"] = math.nan

    group.sort_values("mean", ascending=False, inplace=True)
    return {"group": group, "stats": stats}


def format_table(df: pd.DataFrame) -> str:
    headers = ["Letter", "Titles", "Avg Rating", "Weighted Avg", "Median", "Total Votes"]
    lines = ["\t".join(headers)]
    for letter, row in df.iterrows():
        lines.append(
            "\t".join(
                [
                    letter,
                    f"{int(row['count']):d}",
                    f"{row['mean']:.2f}",
                    f"{row['weighted_mean']:.2f}",
                    f"{row['median']:.2f}",
                    f"{int(row['total_votes']):d}",
                ]
            )
        )
    return "\n".join(lines)


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets-dir", type=Path, default=None, help="Directory containing IMDB TSV files")
    parser.add_argument("--min-votes", type=int, default=500, help="Minimum votes for a title to be included")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    dataset_paths = detect_dataset_paths(args.datasets_dir)

    results = analyze(dataset_paths, args.min_votes)

    stats = results["stats"]
    print("Movies analyzed:", stats["movie_count"])
    print("Unique initials:", stats["letter_count"])
    print(f"Overall mean rating: {stats['overall_mean']:.2f}")
    print(f"Overall weighted mean rating: {stats['overall_weighted_mean']:.2f}")
    print(f"Eta squared (effect size): {stats['eta_squared']:.4f}")
    if not math.isnan(stats["f_statistic"]):
        print(
            "F statistic: "
            f"{stats['f_statistic']:.3f} (df_between={stats['df_between']}, df_within={stats['df_within']})"
        )
    print()
    print(format_table(results["group"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

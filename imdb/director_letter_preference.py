#!/usr/bin/env python3
"""Assess whether movie directors favor specific starting letters."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Dict

import pandas as pd

from analysis_utils import (
    DatasetPaths,
    detect_dataset_paths,
    extract_first_letter,
    load_movie_basics,
    load_ratings,
)

CREW_COLUMNS = ["tconst", "directors"]
NAME_COLUMNS = ["nconst", "primaryName"]


@dataclass
class DirectorPreference:
    nconst: str
    name: str
    preferred_letter: str
    movie_count: int
    preferred_count: int
    preferred_share: float
    preferred_mean: float
    preferred_weighted_mean: float
    overall_mean: float
    overall_weighted_mean: float


def load_director_assignments(crew_path: Path) -> pd.DataFrame:
    crew = pd.read_csv(
        crew_path,
        sep="\t",
        usecols=CREW_COLUMNS,
        dtype={"tconst": "string", "directors": "string"},
        na_values="\\N",
        keep_default_na=False,
    )
    crew = crew[crew["directors"].notna()].copy()
    crew["nconst"] = crew["directors"].str.split(",")
    crew = crew.explode("nconst")
    crew = crew[crew["nconst"].notna()]
    crew.drop(columns=["directors"], inplace=True)
    return crew


def load_names_subset(names_path: Path, ids: set[str]) -> pd.DataFrame:
    if not ids:
        return pd.DataFrame(columns=NAME_COLUMNS)
    chunk_iter = pd.read_csv(
        names_path,
        sep="\t",
        usecols=NAME_COLUMNS,
        dtype={"nconst": "string", "primaryName": "string"},
        na_values="\\N",
        keep_default_na=False,
        chunksize=250_000,
    )
    chunks: list[pd.DataFrame] = []
    for chunk in chunk_iter:
        subset = chunk[chunk["nconst"].isin(ids)]
        if not subset.empty:
            chunks.append(subset)
    if not chunks:
        return pd.DataFrame(columns=NAME_COLUMNS)
    return pd.concat(chunks, ignore_index=True)


def analyze_preferences(
    dataset_paths: DatasetPaths,
    *,
    min_votes: int,
    min_movies: int,
    top_n: int,
) -> Dict[str, object]:
    if dataset_paths.crew is None or dataset_paths.names is None:
        raise RuntimeError("Crew and name datasets are required but were not located")

    basics = load_movie_basics(dataset_paths.basics)
    ratings = load_ratings(dataset_paths.ratings, min_votes)
    crew = load_director_assignments(dataset_paths.crew)
    director_ids = set(crew["nconst"].dropna().unique())
    names = load_names_subset(dataset_paths.names, director_ids)

    merged = (
        ratings.merge(basics, on="tconst", how="inner")
        .merge(crew, on="tconst", how="inner")
        .merge(names, on="nconst", how="left")
    )

    if merged.empty:
        raise RuntimeError("No movies with directors matched the filters")

    merged["chosenTitle"] = merged["primaryTitle"]
    merged["firstLetter"] = merged["chosenTitle"].map(extract_first_letter)
    merged = merged[merged["firstLetter"].notna()].copy()
    merged["weightedRating"] = merged["averageRating"] * merged["numVotes"]

    merged.drop_duplicates(subset=["nconst", "tconst"], inplace=True)

    letter_stats = merged.groupby(["nconst", "firstLetter"]).agg(
        movie_count=("tconst", "size"),
        mean_rating=("averageRating", "mean"),
        total_votes=("numVotes", "sum"),
        weighted_rating=("weightedRating", "sum"),
    )
    letter_stats["weighted_mean"] = letter_stats["weighted_rating"] / letter_stats["total_votes"].where(
        letter_stats["total_votes"] > 0,
        other=pd.NA,
    )

    director_totals = merged.groupby("nconst").agg(
        name=("primaryName", "first"),
        movie_count=("tconst", "size"),
        mean_rating=("averageRating", "mean"),
        total_votes=("numVotes", "sum"),
        weighted_rating=("weightedRating", "sum"),
    )
    director_totals["weighted_mean"] = director_totals["weighted_rating"] / director_totals["total_votes"].where(
        director_totals["total_votes"] > 0,
        other=pd.NA,
    )

    eligible_directors = director_totals[director_totals["movie_count"] >= min_movies]
    if eligible_directors.empty:
        raise RuntimeError("No directors met the minimum movie requirement")

    eligible_letters = letter_stats.join(eligible_directors[["movie_count"]], how="inner", rsuffix="_total")
    eligible_letters["share"] = eligible_letters["movie_count"] / eligible_letters["movie_count_total"]

    top_letters = (
        eligible_letters.reset_index()
        .sort_values(["share", "movie_count"], ascending=[False, False])
        .groupby("nconst", as_index=False)
        .first()
    )

    summary = top_letters.merge(
        eligible_directors,
        on="nconst",
        suffixes=('_preferred', '_overall'),
    )
    summary["name"] = summary["name"].fillna("(unknown)")
    summary["weighted_mean_preferred"] = summary["weighted_mean_preferred"].fillna(
        summary["mean_rating_preferred"]
    )
    summary["weighted_mean_overall"] = summary["weighted_mean_overall"].fillna(
        summary["mean_rating_overall"]
    )

    summary.sort_values([
        "share",
        "movie_count_overall",
        "mean_rating_preferred",
    ], ascending=[False, False, False], inplace=True)

    selected = summary.head(top_n)

    preferences = [
        DirectorPreference(
            nconst=row["nconst"],
            name=row["name"],
            preferred_letter=row["firstLetter"],
            movie_count=int(row["movie_count_overall"]),
            preferred_count=int(row["movie_count_preferred"]),
            preferred_share=float(row["share"]),
            preferred_mean=float(row["mean_rating_preferred"]),
            preferred_weighted_mean=float(row["weighted_mean_preferred"])
            if pd.notna(row["weighted_mean_preferred"])
            else float(row["mean_rating_preferred"]),
            overall_mean=float(row["mean_rating_overall"]),
            overall_weighted_mean=float(row["weighted_mean_overall"])
            if pd.notna(row["weighted_mean_overall"])
            else float(row["mean_rating_overall"]),
        )
        for _, row in selected.iterrows()
    ]

    global_stats = {
        "directors_considered": int(len(eligible_directors)),
        "movies_considered": int(eligible_directors["movie_count"].sum()),
    }

    return {"preferences": preferences, "global": global_stats}


def format_preferences(preferences: list[DirectorPreference]) -> str:
    headers = [
        "Director",
        "Movies",
        "Preferred Letter",
        "Share",
        "Preferred Avg",
        "Preferred Weighted",
        "Overall Avg",
        "Overall Weighted",
    ]
    lines = ["\t".join(headers)]
    for item in preferences:
        lines.append(
            "\t".join(
                [
                    item.name,
                    f"{item.movie_count}",
                    item.preferred_letter,
                    f"{item.preferred_share:.2f}",
                    f"{item.preferred_mean:.2f}",
                    f"{item.preferred_weighted_mean:.2f}",
                    f"{item.overall_mean:.2f}",
                    f"{item.overall_weighted_mean:.2f}",
                ]
            )
        )
    return "\n".join(lines)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets-dir", type=Path, default=None, help="Directory containing IMDB TSV files")
    parser.add_argument("--min-votes", type=int, default=500, help="Minimum votes per title")
    parser.add_argument("--min-movies", type=int, default=3, help="Minimum movies per director to include")
    parser.add_argument("--top-n", type=int, default=20, help="Number of directors to display")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    dataset_paths = detect_dataset_paths(
        args.datasets_dir,
        require_crew=True,
        require_names=True,
    )

    results = analyze_preferences(
        dataset_paths,
        min_votes=args.min_votes,
        min_movies=args.min_movies,
        top_n=args.top_n,
    )

    print("Directors considered:", results["global"]["directors_considered"])
    print("Movies considered:", results["global"]["movies_considered"])
    print()
    print(format_preferences(results["preferences"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

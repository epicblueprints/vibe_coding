"""Shared data loading helpers for IMDB-based analyses."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import pandas as pd

DATA_DIR_DEFAULTS: Sequence[Path] = (Path("datasets"), Path("dataset"))
AKAS_COLUMNS = ["titleId", "ordering", "title", "region", "isOriginalTitle"]
BASICS_COLUMNS = ["tconst", "titleType", "primaryTitle", "isAdult"]
RATINGS_COLUMNS = ["tconst", "averageRating", "numVotes"]


@dataclass
class DatasetPaths:
    akas: Path
    basics: Path
    ratings: Path
    crew: Path | None = None
    names: Path | None = None


def detect_dataset_paths(base: Path | None, *, require_crew: bool = False, require_names: bool = False) -> DatasetPaths:
    if base is None:
        for candidate in DATA_DIR_DEFAULTS:
            if candidate.exists():
                dataset_dir = candidate
                break
        else:
            raise FileNotFoundError("Dataset directory not found. Pass --datasets-dir explicitly.")
    else:
        dataset_dir = base

    crew_path = dataset_dir / "title.crew.tsv"
    names_path = dataset_dir / "name.basics.tsv"

    if require_crew and not crew_path.exists():
        raise FileNotFoundError("title.crew.tsv is required for this analysis but was not found")
    if require_names and not names_path.exists():
        raise FileNotFoundError("name.basics.tsv is required for this analysis but was not found")

    return DatasetPaths(
        akas=dataset_dir / "title.akas.tsv",
        basics=dataset_dir / "title.basics.tsv",
        ratings=dataset_dir / "title.ratings.tsv",
        crew=crew_path if crew_path.exists() else None,
        names=names_path if names_path.exists() else None,
    )


def extract_first_letter(title: str | float) -> str | None:
    if not isinstance(title, str):
        return None
    for char in title.strip():
        if char.isalpha():
            return char.upper()
        if char.isdigit():
            return "#"
    return None


def load_indian_titles(akas_path: Path) -> pd.DataFrame:
    chunk_iter = pd.read_csv(
        akas_path,
        sep="\t",
        usecols=AKAS_COLUMNS,
        dtype={
            "titleId": "string",
            "ordering": "int64",
            "title": "string",
            "region": "string",
            "isOriginalTitle": "string",
        },
        na_values="\\N",
        keep_default_na=False,
        chunksize=250_000,
    )
    chunks: list[pd.DataFrame] = []
    for chunk in chunk_iter:
        filtered = chunk[chunk["region"] == "IN"].copy()
        if filtered.empty:
            continue
        filtered["isOriginalTitle"] = filtered["isOriginalTitle"].fillna("0").astype(int)
        chunks.append(filtered)
    if not chunks:
        return pd.DataFrame(columns=["tconst", "regionalTitle"], dtype="string")
    akas_in = pd.concat(chunks, ignore_index=True)
    akas_in.sort_values(["titleId", "isOriginalTitle", "ordering"], ascending=[True, False, True], inplace=True)
    preferred = akas_in.drop_duplicates("titleId", keep="first").copy()
    preferred.rename(columns={"titleId": "tconst", "title": "regionalTitle"}, inplace=True)
    return preferred[["tconst", "regionalTitle"]]


def load_movie_basics(basics_path: Path) -> pd.DataFrame:
    basics = pd.read_csv(
        basics_path,
        sep="\t",
        usecols=BASICS_COLUMNS,
        dtype={
            "tconst": "string",
            "titleType": "string",
            "primaryTitle": "string",
            "isAdult": "string",
        },
        na_values="\\N",
        keep_default_na=False,
    )
    mask = (basics["titleType"] == "movie") & (basics["isAdult"] != "1")
    return basics.loc[mask, ["tconst", "primaryTitle"]]


def load_ratings(ratings_path: Path, min_votes: int) -> pd.DataFrame:
    ratings = pd.read_csv(
        ratings_path,
        sep="\t",
        usecols=RATINGS_COLUMNS,
        dtype={"tconst": "string", "averageRating": "float64", "numVotes": "int64"},
        na_values="\\N",
        keep_default_na=False,
    )
    return ratings[ratings["numVotes"] >= min_votes]

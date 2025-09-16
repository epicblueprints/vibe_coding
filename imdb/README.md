# IMDb Dataset Analyses (Completely vibe coded)

This directory assembles IMDb's public TSV exports alongside a set of command-line
utilities for inspecting the data and reproducing rating analyses. The work focuses
on understanding how title initials relate to viewer scores, both overall and for
movies released in India, and on exploring whether directors gravitate toward
specific starting letters for their filmography.

## Repository Contents
- `datasets/`: Local mirror of the IMDb dataset TSV files referenced by every analysis.
- `DATASET.md`: Notes on each TSV, shared columns, and how tables join together.
- `download_imdb_datasets.sh`: Convenience script that downloads the latest TSV
  exports from https://datasets.imdbws.com.
- `analysis_utils.py`: Shared helpers for locating datasets, extracting first
  letters, and loading filtered slices of the large TSV files with pandas.
- `explore_dataset.py`: Utility for printing per-file size, schema, and sample
  rows to sanity-check local data drops.
- `rating_distribution.py`: Histogram generator that buckets `title.ratings.tsv`
  entries between configurable minimum/maximum values.
- `letter_rating_analysis.py`: Main analysis measuring how Indian-release title
  initials correlate with IMDb ratings, including ANOVA-style statistics and
  weighted means by initial.
- `letter_rating_analysis.txt`: Saved console output from `letter_rating_analysis.py`
  using a 500-vote threshold (28,963 movies, 66 unique initials).
- `director_letter_preference.py`: Follow-up study that evaluates whether
  individual directors favor particular starting letters, reporting the share of
  a director's catalog that starts with the preferred letter and the associated
  rating deltas.

## Environment Setup
All scripts target Python 3.10+ and depend on `pandas`.

```bash
python -m venv venv
source venv/bin/activate
pip install pandas
```

The analyses expect the uncompressed TSV files in `datasets/`. Download them with
`download_imdb_datasets.sh` or place your own exports in that directory. Missing
crew/name tables will trigger informative errors when required.

## Running the Tools
- Explore the raw files:
  ```bash
  ./explore_dataset.py --sample-rows 3 --count-rows
  ```
- Build a rating histogram:
  ```bash
  ./rating_distribution.py --min 1 --max 10 --step 0.5
  ```
- Reproduce the Indian-initials study (default 500-vote minimum):
  ```bash
  ./letter_rating_analysis.py --min-votes 500
  ```
- Inspect director letter preferences (requires crew and name datasets):
  ```bash
  ./director_letter_preference.py --min-votes 500 --min-movies 3 --top-n 20
  ```

Each script autodetects `datasets/` by default; pass `--datasets-dir` to point at
other locations.


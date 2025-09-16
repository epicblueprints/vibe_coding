#!/usr/bin/env bash
set -euo pipefail

BASE_URL="https://datasets.imdbws.com"
FILES=(
  "name.basics.tsv.gz"
  "title.akas.tsv.gz"
  "title.basics.tsv.gz"
  "title.crew.tsv.gz"
  "title.episode.tsv.gz"
  "title.principals.tsv.gz"
  "title.ratings.tsv.gz"
)

OUTPUT_DIR="${1:-.}"
mkdir -p "$OUTPUT_DIR"

for file in "${FILES[@]}"; do
  url="${BASE_URL}/${file}"
  dest="${OUTPUT_DIR}/${file}"
  echo "Downloading ${url} -> ${dest}"
  curl -fL --progress-bar "$url" -o "$dest"
done

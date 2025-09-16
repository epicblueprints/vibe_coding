# IMDb Dataset Overview

This repository currently mirrors the public IMDb datasets in `datasets/`. The files share a tab-separated format (TSV) with a header row followed by data rows. Missing values are encoded as `\N`. Identifiers follow IMDb conventions (`nconst` for names, `tconst` for titles), enabling joins across files.

## Shared Structure
- Text is UTF-8 encoded and fields are tab-separated; quoted strings are rare.
- Reference columns such as `tconst`, `nconst`, and `titleId` allow cross-file relationships between titles and people.
- Boolean flags are represented as `0` or `1`. Numeric columns may include `\N` when data is unknown.

## File Details
### datasets/name.basics.tsv
- Size ≈ 862.43 MiB; 14,715,143 data rows.
- Person directory keyed by `nconst` with primary name, birth/death years, primary professions, and up to four known-for title IDs.
- Useful for enriching credits with biographical details or filtering by profession.

### datasets/title.akas.tsv
- Size ≈ 2,553.41 MiB; 53,194,135 data rows.
- Alternate titles (`aka`s) for each work referenced by `titleId`/`tconst`, covering localized titles, release aliases, and display variants.
- Includes region, language, and flags for original titles plus optional attributes describing special contexts (e.g., “literal title”).

### datasets/title.basics.tsv
- Size ≈ 982.82 MiB; 11,912,581 data rows.
- Master list of titles keyed by `tconst`, with type (movie, short, episode, etc.), primary/original titles, release years, runtime, and genre list.
- Foundation table for title-level analyses; other files join to it via `tconst`.

### datasets/title.crew.tsv
- Size ≈ 374.91 MiB; 11,912,581 data rows.
- Links titles (`tconst`) to principal creative contributors: director(s) and writer(s) as comma-separated `nconst` lists.
- Complements `title.basics.tsv` when attributing creative roles; aligns row-for-row with it.

### datasets/title.episode.tsv
- Size ≈ 229.38 MiB; 9,172,468 data rows.
- Episode-to-series mapping: each `tconst` references an episode and `parentTconst` its series or season container.
- Provides season and episode numbers (may be `\N`) for ordering episodic content.

### datasets/title.principals.tsv
- Size ≈ 4,027.92 MiB; 94,747,067 data rows.
- Detailed casting and crew credits keyed by `tconst` plus `nconst`, with role category, optional job description, and character names.
- High-cardinality table capturing on-screen and behind-the-scenes contributors; ordering column ranks credit prominence.

### datasets/title.ratings.tsv
- Size ≈ 26.81 MiB; 1,614,145 data rows.
- Aggregated user ratings per `tconst`, including average rating and vote count.
- Join with `title.basics.tsv` to analyze popularity or quality trends.

## Relationships and Usage Notes
- Join `title.basics.tsv` ⇔ `title.principals.tsv`/`title.crew.tsv`/`title.ratings.tsv` via `tconst` to build comprehensive title views.
- Connect people to their credits through `nconst` (`name.basics.tsv`) and cross-reference with `title.principals.tsv` or `title.crew.tsv`.
- Use `title.episode.tsv` to map episodic works back to parent series, then pull metadata from `title.basics.tsv` and ratings for rollups.
- Alternate titles (`title.akas.tsv`) expand coverage for internationalization, search, and display contexts.

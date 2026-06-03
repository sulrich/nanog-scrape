# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Web scraping and data extraction toolkit for NANOG (North American Network Operators' Group) conference data. Extracts agendas, speaker info, attendee lists, and YouTube transcripts from archive.nanog.org to build a consolidated speaker/presentation database spanning NANOG 6+.

## Running Scripts

Scripts use [uv](https://docs.astral.sh/uv/) with PEP 723 inline metadata - no venv or `pip install` needed. PDF parsing (NANOG 61-78 attendees) requires a Java runtime for tabula-py.

```bash
# scrape a single agenda (NANOG 13-76)
uv run nanog-agenda.py --nanog 42 --url archive.nanog.org --csv csv/nanog-42-agenda.csv agendas/nanog42-agenda.html

# scrape attendees - format depends on era
uv run nanog-attendees.py --nanog 42 --csv csv/nanog-42-attendees.csv attendees/nanog42-attendees.html   # legacy HTML
uv run nanog-attendees.py --nanog 70 --csv csv/nanog-70-attendees.csv attendees/nanog70-attendees.pdf    # PDF
uv run nanog-attendees.py --nanog 83 --csv csv/nanog-83-attendees.csv attendees/nanog83-attendees.html   # new HTML
uv run nanog-attendees.py --nanog 96 --csv csv/nanog-96-attendees.csv attendees/nanog96-attendees.json   # JSON API

# batch export all agendas and attendees
./export-nanog.sh export-agendas
./export-nanog.sh export-attendees

# download YouTube transcripts
uv run nanog-get-youtube-transcript.py --csv agendas-13-76.csv --output transcripts/
```

No test framework is configured. Validation is manual (inspect CSV output).

## Architecture

**Data pipeline:** HTML/PDF source files -> per-script extraction -> individual CSVs -> consolidation via `export-nanog.sh` -> merge tools for enrichment

**Key scripts:**
- `nanog-agenda.py` - Extracts speakers, affiliations, titles, YouTube links, presentation files from agenda HTML. Has two parsing paths: NANOG <= 70 (uses `<li>` tags) vs NANOG >= 71 (uses `<dd>` tags).
- `nanog-attendees.py` - Extracts attendee names/orgs. Four format eras, routed by file extension and NANOG number:
  - Legacy HTML from archive.nanog.org (NANOG 12-60)
  - PDF via tabula (NANOG 61-78). Multiple sub-eras: 61-66 have comma-separated "Last, First" names; 66-67 have a leading empty column; 70-77 have separate Last/First/Company/ASN columns; 78 swaps ASN and Company columns.
  - nanog.org server-rendered HTML (NANOG 79-83)
  - nanog.org JSON API (NANOG 84-96)
- `nanog-get-youtube-transcript.py` - Downloads YouTube closed-caption transcripts, caches to text files.
- `nanog-merge.py` - One-shot merge of manually curated "raw" speaker data with scraped data using fuzzy matching (thefuzz) on speaker name + title + NANOG number.
- `liz-merge.py` - Merges "golden master" data with a tagged fork to add TAGS/TOPICS/ACADEMIC metadata.
- `export-nanog.sh` - Orchestration: batch-runs scrapers, consolidates per-meeting CSVs into master files, cleans up scratch files.

**Data directories:**
- `agendas/` - Source HTML files (nanog{N}-agenda.html)
- `attendees/` - Source HTML/PDF/JSON files
- `data/nanog-dates-locs.csv` - Meeting dates/locations lookup
- `csv/` - Scratch directory for intermediate CSVs (gitignored)
- `transcripts/` - Cached YouTube transcripts

## Key Patterns

- **Version-aware parsing**: NANOG version number drives HTML parsing strategy (different site layouts across eras). Always check which code path a change affects.
- **Fuzzy matching**: `thefuzz.process.extractOne()` is used throughout merge scripts. Threshold tuning matters for data quality.
- **CSV field order**: Agenda CSV schema is `NANOG,SPEAKER,AFFILIATION,TITLE,YOUTUBE,PRESO_FILES,ORIGIN`. Merge scripts add fields like `TAGS,TOPICS,ACADEMIC`.
- **Global state**: `nanog-agenda.py` uses module-level globals (`NANOG_NUM`, `URL_BASE`, `ORIGIN`) set at runtime from CLI args.
- **Malformed entry logging**: Scripts print `malformed spkr:` or `malformed attendee:` warnings to stderr for entries that don't parse cleanly.
- **Filter patterns**: Non-talk items (lunch, breaks, social events) are filtered via regex lists.

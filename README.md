# nanog-scrape

some quick and dirty beautiful soup (and friends) to extract the necessary
elements from historic NANOG agendas and attendee lists in order to build up
the speaker stats and database. covers NANOG 6 through 96.

## prerequisites

- [uv](https://docs.astral.sh/uv/) - scripts use PEP 723 inline metadata
  so `uv` resolves dependencies automatically. no venv or `pip install`
  needed.
- java runtime (openjdk) - only needed for PDF attendee list parsing via
  `tabula-py` (NANOG 61-78).

## scripts

- `nanog-agenda.py` - scrapes agendas from archive.nanog.org (NANOG 13-76)
- `nanog-attendees.py` - extracts attendee lists across four format eras:
  - legacy HTML from archive.nanog.org (NANOG 12-60)
  - PDF via tabula (NANOG 61-78, requires java)
  - nanog.org server-rendered HTML (NANOG 79-83)
  - nanog.org JSON API (NANOG 84-96)
- `nanog-get-youtube-transcript.py` - pulls close captioning transcripts
  from youtube for the various presentations
- `export-nanog.sh` - batch orchestration to run scrapers and consolidate
  per-meeting CSVs into master files
- `nanog-merge.py` - single use (ideally) tool to merge manually curated
  speaker data with scraped data using fuzzy matching
- `liz-merge.py` - merges golden master data with a tagged fork to add
  topic/tag metadata

## usage

```bash
# scrape a single agenda
uv run nanog-agenda.py --nanog 42 --url archive.nanog.org \
  --csv csv/nanog-42-agenda.csv agendas/nanog42-agenda.html

# scrape attendees (format picked by file extension and NANOG number)
uv run nanog-attendees.py --nanog 42 --csv csv/nanog-42-attendees.csv \
  attendees/nanog42-attendees.html
uv run nanog-attendees.py --nanog 70 --csv csv/nanog-70-attendees.csv \
  attendees/nanog70-attendees.pdf
uv run nanog-attendees.py --nanog 96 --csv csv/nanog-96-attendees.csv \
  attendees/nanog96-attendees.json

# batch export everything
./export-nanog.sh export-agendas
./export-nanog.sh export-attendees
```

## data

- `agendas/` - source HTML agenda files (nanog{N}-agenda.html)
- `attendees/` - source attendee files (HTML, PDF, or JSON depending on
  era)
- `data/nanog-dates-locs.csv` - NANOG meeting dates and locations lookup
- `csv/` - scratch directory for intermediate CSVs
- `transcripts/` - cached youtube transcripts

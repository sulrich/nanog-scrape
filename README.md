# overview

some quick and dirty beautiful soup to extract the necessary elements from the
historic NANOG agendas in order to build up the speader stats and database.

- `nanog-agendas.py` - scrapes the agendas available from archive.nanog.org
- `nanog-attendees.py` - scrapes the attendees lists available from
  archive.nanog.org
- `nanog-get-youtube-transcript.py` - pulls the close captioning transcripts
  from youtube for the various presentations
- `export-nanog.sh` - a quick shell script to consistently munge things together
  into the CSVs for export

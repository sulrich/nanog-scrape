#!/bin/bash
# -*- mode: sh; fill-column: 78; comment-column: 50; tab-width: 2 -*-

trap cleanup SIGINT SIGTERM ERR EXIT

usage() {
    cat << EOF
usage: ${0##*/} [-h]
    -h          display help and exit

EOF
}

# print an error and stop the script.
die() {
  echo "error: $*" >&2
  exit 1
}

# run one scraper and check what it produced. usage:
#   scrape <label> <output csv> <command...>
# a failed scraper, or one that writes an empty CSV, stops the export. both
# used to slip through into the consolidated file as a missing meeting
# (e.g. no java for the PDF years, or a saved "page not found" page).
scrape() {
  local label=$1
  local out=$2
  shift 2

  echo "scraping ${label}"
  "$@" || die "${label} failed (exit $?): $*"
  [[ -s "${out}" ]] || die "${label} produced no rows: ${out}"
}


# for the agendas in the range noted export the associated CSVs
## export-agendas: output the agenda formats we know of
export-agendas() {
  local AGENDA_HEADER="NANOG,SPEAKER,AFFILIATION,TITLE,YOUTUBE,PRESO_FILES,ORIGIN"
  local AGENDA_START=13
  local AGENDA_END=76

  # clear scratch files from earlier runs so they can't leak into the output
  rm -f csv/*-agenda.csv

  for (( i = AGENDA_START; i <= AGENDA_END; i++ ))
  do
    scrape "agenda: NANOG $i" "csv/nanog-$i-agenda.csv" \
      uv run nanog-agenda.py --nanog "$i" --url archive.nanog.org \
      --csv "csv/nanog-$i-agenda.csv" "agendas/nanog$i-agenda.html"
  done

  echo "consolidating NANOG agendas"
  echo "${AGENDA_HEADER}" >  agendas-$AGENDA_START-$AGENDA_END.csv
  cat csv/*-agenda.csv >> agendas-$AGENDA_START-$AGENDA_END.csv
  echo "removing scratch agenda CSVs"
  rm -f csv/*-agenda.csv
}

## export-attendees: output the attendee lists
export-attendees() {
  local ATT_START=12
  local ATT_END=98
  local ATT_HTML_END=60

  # tabula (NANOG 61-78 PDFs) shells out to java
  java -version > /dev/null 2>&1 \
    || die "no working java runtime; tabula needs one for the NANOG 61-78 PDFs"

  # clear scratch files from earlier runs so they can't leak into the output
  rm -f csv/*-attendees.csv

  # NANOG 12-60: legacy HTML (archive.nanog.org)
  for (( i = ATT_START; i <= ATT_HTML_END; i++ ))
  do
    # the saved NANOG 27 file is a "page not found" page (the URL it came
    # from was mistyped). re-fetch it and drop this skip to restore 27.
    if (( i == 27 )); then
      echo "warning: skipping NANOG 27, no attendee data in the saved file" >&2
      continue
    fi
    scrape "attendees: NANOG $i" "csv/nanog-$i-attendees.csv" \
      uv run nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.html"
  done

  # NANOG 61-78: PDF (archive.nanog.org / storage.googleapis.com)
  for (( i = 61; i <= 78; i++ ))
  do
    scrape "attendees: NANOG $i (pdf)" "csv/nanog-$i-attendees.csv" \
      uv run nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.pdf"
  done

  # NANOG 79-83: new-style HTML (nanog.org server-rendered)
  for (( i = 79; i <= 83; i++ ))
  do
    scrape "attendees: NANOG $i (html)" "csv/nanog-$i-attendees.csv" \
      uv run nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.html"
  done

  # NANOG 84-98: JSON API (nanog.org)
  for (( i = 84; i <= ATT_END; i++ ))
  do
    scrape "attendees: NANOG $i (json)" "csv/nanog-$i-attendees.csv" \
      uv run nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.json"
  done

  echo "consolidating NANOG attendees"
  cat csv/*-attendees.csv > "attendees-$ATT_START-$ATT_END.csv"
  echo "removing scratch attendee CSVs"
  rm -f csv/*-attendees.csv
}

# anything that has ## at the front of the line will be used as input.
## help: details the available functions in this script
help() {
  usage
  echo "available functions:"
  sed -n 's/^##//p' "$0" | column -t -s ':' | sed -e 's/^/ /'
}

cleanup() {
    trap - SIGINT SIGTERM ERR EXIT
    # script cleanup here, tmp files, etc.
}

if [[ $# -lt 1 ]]; then
  help
  cleanup
  exit
fi

# run the named function. only print help for a name we don't know; a
# function that fails exits non-zero with its own error message.
CMD=$1
shift 1
if ! declare -F "${CMD}" > /dev/null; then
  echo "error: unknown function: ${CMD}" >&2
  help
  exit 1
fi
"${CMD}" "$@"

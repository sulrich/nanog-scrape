#!/bin/bash
# -*- mode: sh; fill-column: 78; comment-column: 50; tab-width: 2 -*-

trap cleanup SIGINT SIGTERM ERR EXIT

usage() {
    cat << EOF
usage: ${0##*/} [-h]
    -h          display help and exit

EOF
}


# for the agendas in the range noted export the associated CSVs
## export-agendas: output the agenda formats we know of
export-agendas() {
  local AGENDA_HEADER="NANOG,SPEAKER,AFFILIATION,TITLE,YOUTUBE,PRESO_FILES,ORIGIN"
  local AGENDA_START=13
  local AGENDA_END=76
  for (( i = AGENDA_START; i <= AGENDA_END; i++ ))
  do
    echo "scraping agenda: NANOG $i"
    nanog-agenda.py --nanog "$i" --url archive.nanog.org \
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
  local ATT_END=63
  local ATT_HTML_END=60
  for (( i = ATT_START; i <= ATT_HTML_END; i++ ))
  do
    echo "scraping attendees: NANOG $i"
    nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.html"
  done

  for i in 61 62 63
  do
    echo "scraping attendees: NANOG $i (pdf)"
    nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.pdf"
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
  sed -n 's/^##//p' $0 | column -t -s ':' | sed -e 's/^/ /'
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

case $1 in
  *)
    # shift positional arguments so that arg 2 becomes arg 1, etc.
    CMD=$1
    shift 1
    ${CMD} ${@} || help
    cleanup
    ;;
esac

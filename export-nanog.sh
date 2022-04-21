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
  local AGENDA_START=13
  local AGENDA_END=70
  for (( i = AGENDA_START; i <= AGENDA_END; i++ ))
  do
    echo "exporting NANOG $i - agenda"
    nanog-agenda.py --nanog "$i" --url archive.nanog.org \
      --csv "csv/nanog-$i-agenda.csv" "agendas/nanog$i-agenda.html"
  done

  echo "consolidating nanog agendas"
  cat csv/*-agenda.csv > nanog-agendas-13-70.csv
}

## export-attendees: output the attendee lists
export-attendees() {
  local ATT_START=19
  local ATT_END=52
  for (( i = ATT_START; i <= ATT_END; i++ ))
  do
    echo "exporting NANOG $i - attendees"
    nanog-attendees.py --nanog "$i" \
      --csv "csv/nanog-$i-attendees.csv" "attendees/nanog$i-attendees.html"
  done

  echo "consolidating nanog attendees"
  cat csv/*-attendees.csv > "nanog-attendees-$ATT_START-$ATT_END.csv"
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

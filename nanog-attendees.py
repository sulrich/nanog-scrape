#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import re
import csv
import pprint


def process_attendee_table(attendee_table):
    attendees = []
    for tr in attendee_table.tbody.find_all("tr"):
        td = tr.find_all("td")
        if len(td) < 2:
            continue

        attendee = [
            td[0].text,
            td[1].text,
            td[2].text,
        ]
        attendees.append(attendee)

    return attendees


def get_attendees_table(attendees_file):
    """
    there should really only be 1 attendee table in the page.  it appears to be
    the only one with a border=1.  we'll see ...
    """
    with open(attendees_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    attendees_table = soup.find_all("table", {"border": "1"})

    attendees = []
    for table in attendees_table:
        attendees = process_attendee_table(table)

    return attendees


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attendees", help="html attendees file")
    parser.add_argument(
        "--nanog",
        help="nanog number",
        dest="NANOG_NUM",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--csv",
        help="csv file to output to",
        dest="csv_file",
        action="store",
        required=False,
    )
    args = parser.parse_args()

    global NANOG_NUM
    NANOG_NUM = args.NANOG_NUM

    attendees = get_attendees_table(args.attendees)

    if args.csv_file:
        with open(args.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(attendees)

    else:
        pprint.pprint(attendees, width=100)


if __name__ == "__main__":
    main()

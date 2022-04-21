#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import re
import csv
import tabula
import pprint


def process_attendee_table(attendee_table, parse_names):
    attendees = []
    for tr in attendee_table.find_all("tr"):
        # for tr in attendee_table.tbody.find_all("tr"):
        td = tr.find_all("td")
        if len(td) < 2:
            continue

        if parse_names:
            try:
                (lname, fname) = re.split(",", td[0].text.strip())
                attendee = [
                    NANOG_NUM,
                    lname.strip(),
                    fname.strip(),
                    td[1].text.strip(),
                ]
                attendees.append(attendee)
            except ValueError:
                attendee = [
                    NANOG_NUM,
                    "malformed attendee:" + td[0].text.strip(),
                    "",
                    td[1].text.strip(),
                ]
                attendees.append(attendee)

        else:
            try:
                attendee = [
                    NANOG_NUM,
                    td[0].text.strip(),  # last name
                    td[1].text.strip(),  # first name
                    td[2].text.strip(),  # organization
                ]
                attendees.append(attendee)
            except IndexError:
                attendee = [NANOG_NUM]
                cells = [x.text.strip() for x in td]
                attendee.extend(cells)
                attendees.append(attendee)

    return attendees


def get_attendees_table(attendees_file):
    """
    there should really only be 1 attendee table in the page.
    different iterations of the NANOG site over the years have moved this.
    """
    with open(attendees_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    if NANOG_NUM in [12]:
        attendees_table = soup.find_all("table", {"cellpadding": "3"})
        parse_names = True
    elif NANOG_NUM in [13]:
        attendees_table = soup.find_all(
            "table", {"class": "MsoNormalTable", "border": "0"}
        )
        parse_names = True
    elif NANOG_NUM in [14, 15, 16, 17, 18]:
        attendees_table = soup.find_all("table", {"border": "1"})
        parse_names = True
    elif NANOG_NUM in range(46, 53):
        attendees_table = soup.find_all("table", {"border": "0", "cellpadding": "4"})
        parse_names = False
    elif NANOG_NUM in range(53, 61):
        attendees_table = soup.find_all("table", {"class": "GJ"})
        parse_names = True
    else:
        attendees_table = soup.find_all("table", {"border": "1"})
        parse_names = False

    attendees = []
    for table in attendees_table:
        attendees = process_attendee_table(table, parse_names)

    return attendees


def pdf_text_clean(cell_text):
    text = cell_text.strip()

    text = re.sub("\s+", " ", text)
    return text


def fix_pdf_names(name):
    try:
        (lname, fname) = re.split(",", name.strip())
    except ValueError:
        fname = "malformed attendee:"
        lname = name.strip()

    lname = lname.strip()
    fname = fname.strip()
    return (fname, lname)


def parse_attendees_pdf(attendee_pdf):
    attendee_table = tabula.read_pdf(attendee_pdf, output_format="json", pages="all")
    # we might need to adjust this for each pdf table
    attendees = []
    for data_table in attendee_table:
        # data_table = attendee_table[1]["data"]
        for row in data_table["data"]:
            (fname, lname) = fix_pdf_names(pdf_text_clean(row[0]["text"]))
            org = pdf_text_clean(row[1]["text"])

            attendee = [NANOG_NUM, lname, fname, org]
            attendees.append(attendee)

    return attendees


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("attendees", help="html attendees file")
    parser.add_argument(
        "--nanog",
        help="nanog number",
        dest="NANOG_NUM",
        type=int,
        action="store",
        required=True,
    )
    parser.add_argument(
        "--csv",
        help="csv file for output",
        dest="csv_file",
        action="store",
        required=False,
    )
    args = parser.parse_args()

    global NANOG_NUM
    NANOG_NUM = args.NANOG_NUM

    if "pdf" in args.attendees:
        attendees = parse_attendees_pdf(args.attendees)
    else:
        attendees = get_attendees_table(args.attendees)

    if args.csv_file:
        with open(args.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(attendees)

    else:
        pprint.pprint(attendees, width=100)


if __name__ == "__main__":
    main()

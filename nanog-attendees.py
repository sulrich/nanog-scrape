#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "beautifulsoup4",
#     "tabula-py",
# ]
# ///

from bs4 import BeautifulSoup
import argparse
import json
import re
import csv
import sys
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
            lname = ""
            fname = ""
            try:
                name = re.split(",", td[0].text.strip())
                if len(name) == 2:
                    lname = name[0]
                    fname = name[1]
                elif len(name) > 2:
                    lname = name[0] + name[1]
                    fname = " ".join(name[2:])

                if lname.strip() == "" and fname.strip() == "":
                    continue

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


def process_new_html_attendees(attendees_file):
    """parse the nanog.org attendee pages used from NANOG 79-83.

    these have a table with columns: First Name, Last Name, Company, ASN, MEET, Type.
    NANOG 79 uses <th> for row numbers alongside <td> cells.
    NANOG 80-83 use the agenda-table-body class with all <td> cells.
    """
    with open(attendees_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    attendees = []
    for tr in soup.find_all("tr"):
        td = tr.find_all("td")
        if len(td) < 3:
            continue

        fname = td[0].text.strip()
        lname = td[1].text.strip()
        org = td[2].text.strip()

        if fname == "" and lname == "":
            continue
        # skip header-like rows
        if fname == "First Name":
            continue
        # normalize em-dash placeholder to empty
        if org == "\u2014":
            org = ""

        attendees.append([NANOG_NUM, lname, fname, org])

    return attendees


def parse_attendees_json(attendees_json):
    """parse the JSON attendee data used from NANOG 84-98.

    JSON is an array of objects with keys: first_name, last_name, company.
    """
    with open(attendees_json) as f:
        data = json.load(f)

    attendees = []
    for entry in data:
        fname = (entry.get("first_name") or "").strip()
        lname = (entry.get("last_name") or "").strip()
        org = (entry.get("company") or "").strip()

        if fname == "" and lname == "":
            continue

        attendees.append([NANOG_NUM, lname, fname, org])

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

    text = re.sub(r"\s+", " ", text)
    return text


def fix_pdf_names(name):
    """split "Last, First" into (fname, lname), or None if there's no comma."""
    try:
        (lname, fname) = re.split(",", name.strip())
    except ValueError:
        return None

    return (fname.strip(), lname.strip())


# tabula's default table detection (--guess) misses most of the pages in
# some of these PDFs (NANOG 68 yields nothing at all). those meetings use
# stream mode instead. where stream mode runs adjacent columns together,
# explicit column boundaries keep them apart. boundaries are x positions in
# points, just left of each column header on page 1. the header only
# appears on page 1 but the layout is the same on every page.
PDF_TABULA_OPTIONS = {
    66: {"stream": True, "guess": False},
    67: {"stream": True, "guess": False},
    68: {"stream": True, "guess": False},
    69: {"stream": True, "guess": False, "columns": [130, 245, 405]},
    70: {"stream": True, "guess": False, "columns": [80, 143, 400]},
    75: {"stream": True, "guess": False},
    78: {"stream": True, "guess": False, "columns": [112, 177, 240]},
}


def parse_attendees_pdf(attendee_pdf):
    """parse PDF attendee lists across several layout eras.

    NANOG 61-66: 3 columns - "Name" (Last, First), Company, ASN
        66-67 may have a leading empty column.
    NANOG 67:    3 columns - empty, "Name" (Last, First), Organization
    NANOG 68:    3 columns - "Full Name" (Last, First), Company, ASN
    NANOG 69:    4 columns - First Name, Last Name, Company, ASN
    NANOG 70-77: 4 columns - Last Name, First Name, Company, ASN
    NANOG 78:    4 columns - Last Name, First Name, ASN, Company (swapped)
    """
    attendee_table = tabula.read_pdf(
        attendee_pdf,
        output_format="json",
        pages="all",
        **PDF_TABULA_OPTIONS.get(NANOG_NUM, {}),
    )
    attendees = []

    # headers to skip
    skip_names = {
        "Name",
        "Full Name",
        "Last Name",
        "First Name",
        "Company",
        "Organization",
        "ASN",
        "",
    }

    for data_table in attendee_table:
        for row in data_table["data"]:
            cells = [pdf_text_clean(cell["text"]) for cell in row]

            # skip rows that are too short or are headers/titles
            if len(cells) < 2:
                continue
            if cells[0] in skip_names and cells[1] in skip_names:
                continue
            # skip title rows like "NANOG 61 Attendees"
            if re.search(r"NANOG\s+\d+", cells[0]):
                continue

            if NANOG_NUM in range(61, 69):
                # "Last, First" in a single column, possibly with a
                # leading empty column (NANOG 66-67)
                name_col = 0
                org_col = 1
                # detect leading empty column
                if cells[0] == "" and len(cells) >= 3:
                    name_col = 1
                    org_col = 2
                names = fix_pdf_names(cells[name_col])
                if names is None:
                    # a long name can wrap onto a second line, e.g.
                    # "Cuellar Gallegos, Hector" / "Ignacio  ITESM". the
                    # first line has no company, so fold this one into it.
                    prev = attendees[-1] if attendees else None
                    if cells[name_col] and prev and prev[3] == "":
                        prev[2] = f"{prev[2]} {cells[name_col]}".strip()
                        prev[3] = cells[org_col] if len(cells) > org_col else ""
                        continue
                    print(f"malformed attendee: {NANOG_NUM} {cells}", file=sys.stderr)
                    continue
                (fname, lname) = names
                org = cells[org_col] if len(cells) > org_col else ""
            elif NANOG_NUM == 69:
                # First, Last, Company, ASN
                fname = cells[0]
                lname = cells[1]
                org = cells[2] if len(cells) > 2 else ""
            elif NANOG_NUM == 78:
                # Last, First, ASN, Company (company is col 3)
                lname = cells[0]
                fname = cells[1] if len(cells) > 1 else ""
                org = cells[3] if len(cells) > 3 else ""
            else:
                # NANOG 70-77: Last, First, Company, ASN
                lname = cells[0]
                fname = cells[1] if len(cells) > 1 else ""
                org = cells[2] if len(cells) > 2 else ""

            if lname == "" and fname == "":
                continue

            attendees.append([NANOG_NUM, lname, fname, org])

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

    if args.attendees.endswith(".json"):
        attendees = parse_attendees_json(args.attendees)
    elif args.attendees.endswith(".pdf"):
        attendees = parse_attendees_pdf(args.attendees)
    elif NANOG_NUM in range(79, 84):
        attendees = process_new_html_attendees(args.attendees)
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

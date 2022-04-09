#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse


def getTable(agenda_file):
    with open(agenda_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    agenda_table = soup.find("table", attrs={"class": "table_agenda sticky-enabled"})

    # print(agenda_table.tbody)
    heading = []
    for th in agenda_table.thead.find_all("th"):
        heading.append(th.text.strip())

    print(heading)

    for tr in agenda_table.tbody.find_all("tr"):
        print("-" * 70)
        for td in tr.find_all("td"):
            print("- {{", td.text.strip(), "}}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agenda", help="html agenda file")
    args = parser.parse_args()

    getTable(args.agenda)


if __name__ == "__main__":
    main()

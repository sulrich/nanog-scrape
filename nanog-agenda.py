#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse


def scrub_speaker(speaker):
    """
    <td><em><strong>Speakers:</strong></em><br/>
    <ul class="agenda_speakers"><h3 class="txttoggle_action"><li>%%SPEAKER%% ,
    %%AFFILIATION%%</li></h3><div class="text_toggle">%%SPEAKER_BIO%%</div>
    <h3 class="txttoggle_action"></ul></td> }}
    """
    pass


def scrub_abstract(abstract):
    pass


def get_agenda_table(agenda_file):
    with open(agenda_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    agenda_table = soup.find("table", attrs={"class": "table_agenda sticky-enabled"})

    # print(agenda_table.tbody)
    heading = []
    for th in agenda_table.thead.find_all("th"):
        heading.append(th.text.strip())

    print(heading)
    # ['Time/Webcast:', 'Room:', 'Topic/Abstract:', 'Presenter/Sponsor:', 'Presentation Files:']

    for tr in agenda_table.tbody.find_all("tr"):
        td = tr.find_all("td")
        print("-" * 70)
        print("speaker(s): {{", td[3].text.strip(), "}}")
        print("topic/abstract: {{", td[2].text.strip(), "}}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agenda", help="html agenda file")
    args = parser.parse_args()

    get_agenda_table(args.agenda)


if __name__ == "__main__":
    main()

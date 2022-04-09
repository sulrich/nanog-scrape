#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import re


def extract_speaker(speaker_cell):
    """
    <td><em><strong>Speakers:</strong></em><br/>
    <ul class="agenda_speakers"><h3 class="txttoggle_action"><li>%%SPEAKER%% ,
    %%AFFILIATION%%</li></h3><div class="text_toggle">%%SPEAKER_BIO%%</div>
    <h3 class="txttoggle_action"></ul></td> }}
    """

    speakers = []
    speaker_list = speaker_cell.find_all("li")
    for s in speaker_list:
        (speaker, affiliation) = re.split(",", s.text)
        # note nested list
        speakers.append([speaker.strip(), affiliation.strip()])

    return speakers


def extract_title(abstract_cell):
    """meat"""
    title = abstract_cell.find("h3", attrs={"class": "txttoggle_action"})
    if title:
        return title.text


def extract_presentation(preso):
    """
    <td><img alt="youtube" height="12" src="/images/doc_icons/youtube_icon.gif"/><a
    href="https://youtu.be/jW-C82JMEQg">Increas ing IP Network Survivability: An
    Introduction to Protection Mechanisms</a><br/><img alt="ppt" height="12"
    src="/images/doc_icons/ppt_icon.gi f"/><a
    href="/meetings/nanog20/presentations/sadler.ppt">Jonathan Sadler
    Presentation(PPT)</a><br/></td>"""

    video_urls = []
    preso_urls = []

    links = preso.find_all("a")
    for l in links:
        url = l.get("href")
        # these seem to have some form of shortened url, but this substring
        # matches
        if re.search("youtu", url):
            video_urls.append(url)
        if re.search("\.(ppt|pdf)", url):
            preso_urls.append(url)

    return (video_urls, preso_urls)


def process_agenda_table(agenda_table):
    heading = []
    for th in agenda_table.thead.find_all("th"):
        heading.append(th.text.strip())

    print(heading)
    # ['Time/Webcast:', 'Room:', 'Topic/Abstract:', 'Presenter/Sponsor:', 'Presentation Files:']

    for tr in agenda_table.tbody.find_all("tr"):
        td = tr.find_all("td")
        if len(td) < 2:
            continue

        speakers = extract_speaker(td[3])
        title = extract_title(td[2])
        (videos, presos) = extract_presentation(td[4])
        print("-" * 70)
        print("timeslot:", td[0].text)
        print("speakers:", speakers)
        print("topic/abstract:", title)
        print("presentation:", presos)
        print("video:", videos)


def get_agenda_tables(agenda_file):
    with open(agenda_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    agenda_tables = soup.find_all(
        "table", attrs={"class": "table_agenda sticky-enabled"}
    )

    for agenda in agenda_tables:
        process_agenda_table(agenda)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agenda", help="html agenda file")
    args = parser.parse_args()

    get_agenda_tables(args.agenda)


if __name__ == "__main__":
    main()

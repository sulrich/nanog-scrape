#!/usr/bin/env python3

from bs4 import BeautifulSoup
import argparse
import re
import csv
import pprint

NANOG_NUM = 0
URL_BASE = ""
ORIGIN = "archive.nanog.org"


def extract_speaker(speaker_cell):
    """
    sample speaker cell
    <td><em><strong>Speakers:</strong></em><br/>
    <ul class="agenda_speakers"><h3 class="txttoggle_action"><li>%%SPEAKER%% ,
    %%AFFILIATION%%</li></h3><div class="text_toggle">%%SPEAKER_BIO%%</div>
    <h3 class="txttoggle_action"></ul></td>
    """

    speakers = []
    speaker_list = speaker_cell.find_all("li")
    for s in speaker_list:
        # remove trailing punctuation

        strip_elements = ". "

        if "," not in s.text:
            speakers.append([s.text.strip(strip_elements), ""])
        else:
            try:
                (speaker, affiliation) = re.split(",", s.text, maxsplit=1)
                # note nested list
                speakers.append(
                    [speaker.strip(strip_elements), affiliation.strip(strip_elements)]
                )
            except ValueError:
                speaker = "malformed spkr:" + s.text.strip(strip_elements)
                speakers.append([speaker, ""])

    return speakers


def extract_title(abstract_cell):
    """
    returns the extracted title from the legacy agendas
    TODO(sulrich): this needs to handle the cases where there's no H3 to grab
    but there's something in here that's representative of the title.
    """
    title = ""
    toggled_title = abstract_cell.find("h3", attrs={"class": "txttoggle_action"})
    if toggled_title:
        title = toggled_title.text.strip()
    else:
        title = abstract_cell.text.strip()

    whitespace_re = re.compile(r"[\n\r\t]")
    title = whitespace_re.sub(" ", title)

    escape_slash_re = re.compile(r"\\")  # these seem to have escaped
    title = escape_slash_re.sub("", title)

    return title


def extract_presentation(preso):
    """
    sample presentation cell
    <td><img alt="youtube" height="12" src="/images/doc_icons/youtube_icon.gif"/><a
    href="https://youtu.be/jW-C82JMEQg">Increas ing IP Network Survivability: An
    Introduction to Protection Mechanisms</a><br/><img alt="ppt" height="12"
    src="/images/doc_icons/ppt_icon.gi f"/><a
    href="/meetings/nanog20/presentations/sadler.ppt">Jonathan Sadler
    Presentation(PPT)</a><br/></td>

    pull the video links from the cell as well as the URL for the presentation.
    if the presentation url does not start with "http" create the URL from the
    URL_BASE.

    """

    video_urls = []
    preso_urls = []

    links = preso.find_all("a")
    for link in links:
        url = link.get("href")
        # these seem to have some form of shortened url, but this substring
        # matches
        if re.search("https://.*youtu|\.ram", url):
            video_urls.append(url)
        if re.search("\.(ppt|pdf)", url):
            if re.search("^http", url):
                preso_urls.append(url)
            else:
                preso_urls.append("https://" + URL_BASE + url)

    return (video_urls, preso_urls)


def gen_talk_rows(talk):
    """gen_talk_rows emits a list of strings that describe a talk. for panel
    discussions where there are multiple speakers, these are unrolled into a
    separate entries

    parameters:
        talk (dict):

    returns:
        array of strings containing the details associated with the talk
    """
    # ROW FORMAT
    # ----------------------
    # NANOG number
    # speaker name
    # speaker affiliation
    # title
    # video_urls
    # preso_urls

    talk_info = []
    if len(talk["video"]) > 0:
        video = talk["video"][0]
    else:
        video = ""

    if len(talk["presentation"]) > 1:
        presos = "|".join(talk["presentation"])
    elif len(talk["presentation"]) == 1:
        presos = talk["presentation"][0]
    else:
        presos = ""

    # filter out the breaks, etc. that are in the agendas. the check for the
    # non-empty status of the video and the preso fields are to ensure that we
    # do something reasonable here and aren't suppressing hackathon readouts,
    # etc.
    # TODO(sulrich): how do we best handle "women in tech lunches"?
    if re.search(
        "(break|breakfast|beer|social event|lunch|hackathon)",
        talk["title"],
        re.IGNORECASE,
    ) and (video == "" and presos == ""):
        talk_info = None
        return

    if len(talk["speakers"]) > 1:
        for s in talk["speakers"]:
            row = [
                NANOG_NUM,
                s[0],
                s[1],
                talk["title"],
                video,
                presos,
                talk["origin"],
            ]
            talk_info.append(row)
    elif len(talk["speakers"]) == 1:
        row = [
            NANOG_NUM,
            talk["speakers"][0][0],
            talk["speakers"][0][1],
            talk["title"],
            video,
            presos,
            talk["origin"],
        ]
        talk_info.append(row)
    else:
        talk_info = None  # it's a lunch / break / etc.

    return talk_info


def process_agenda_table(agenda_table):
    heading = []
    for th in agenda_table.thead.find_all("th"):
        heading.append(th.text.strip())

    # heading
    # ['Time/Webcast:', 'Room:', 'Topic/Abstract:', 'Presenter/Sponsor:', 'Presentation Files:']

    # importing this here for consistency
    global ORIGIN

    nanog_talks = []
    for tr in agenda_table.tbody.find_all("tr"):
        td = tr.find_all("td")
        if len(td) < 2:
            continue

        (videos, presos) = extract_presentation(td[4])
        talk = {
            "speakers": extract_speaker(td[3]),
            "title": extract_title(td[2]),
            "timeslot": td[0].text,
            "presentation": presos,
            "video": videos,
            "origin": ORIGIN,
        }
        talk_row = gen_talk_rows(talk)
        if talk_row is not None:
            for r in talk_row:
                nanog_talks.append(r)

    return nanog_talks


def get_agenda_tables(agenda_file):
    with open(agenda_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    agenda_tables = soup.find_all(
        "table", attrs={"class": "table_agenda sticky-enabled"}
    )

    export_talks = []
    for agenda in agenda_tables:
        talks = process_agenda_table(agenda)
        export_talks.extend(talks)

    return export_talks


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("agenda", help="html agenda file")
    parser.add_argument(
        "--nanog",
        help="nanog number",
        dest="NANOG_NUM",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--url",
        help="URL base location",
        dest="url_base",
        action="store",
        required=True,
    )

    parser.add_argument(
        "--origin",
        help="source of the agenda",
        dest="origin",
        action="store",
        required=False,
    )
    parser.add_argument(
        "--csv",
        help="csv file to output to",
        dest="csv_file",
        action="store",
        required=False,
    )
    args = parser.parse_args()

    global ORIGIN
    if args.origin:
        ORIGIN = args.origin

    global NANOG_NUM
    NANOG_NUM = args.NANOG_NUM

    global URL_BASE
    URL_BASE = args.url_base

    agenda = get_agenda_tables(args.agenda)

    if args.csv_file:
        with open(args.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(agenda)

    else:
        pprint.pprint(agenda, width=100)


if __name__ == "__main__":
    main()

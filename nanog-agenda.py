#!/usr/bin/env python3

import argparse
import csv
import pprint
import re

from bs4 import BeautifulSoup
from thefuzz import process

NANOG_NUM = 0
URL_BASE = ""
ORIGIN = "archive.nanog.org"


def extract_speaker(speaker_cell, nanog):
    """
    sample speaker cell: NANOG <= 70
    ------------------
    <td><em><strong>Speakers:</strong></em><br/>
    <ul class="agenda_speakers"><h3 class="txttoggle_action"><li>%%SPEAKER%% ,
    %%AFFILIATION%%</li></h3><div class="text_toggle">%%SPEAKER_BIO%%</div>
    <h3 class="txttoggle_action"></ul></td>
    ------------------

    sample speaker cell: NANOG >= 71
    ------------------
    <td>Conference Opening
    <a class="abstract" target="_blank" href="/static/published/meetings//NANOG71/daily/day_3.html#talk_1503">
    <br>[ view full abstract ]
    </a><br>
    <p></p>
    <dl class="speakers">
    <dt>Speaker</dt>
    <dd><strong>David Temkin</strong>, Netflix</dd>
    <dd><strong>Brian Lillie</strong>, Equinix</dd>
    <dd><strong>Jack Waters</strong>, Zayo</dd>
    <dd><strong>L Sean Kennedy</strong></dd>
    </dl>
    </td>

    """

    speakers = []
    if nanog <= 70:
        speaker_list = speaker_cell.find_all("li")
    else:
        speaker_list = speaker_cell.find_all("dd")

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


def extract_title(abstract_cell, nanog):
    """
    returns the extracted title from the legacy agendas
    """
    title = ""

    if nanog <= 70:
        # seems to cover all the bases
        toggled_title = abstract_cell.find("h3", attrs={"class": "txttoggle_action"})
        if toggled_title:
            title = toggled_title.text.strip()
        else:
            title = abstract_cell.text.strip()
    else:
        # the text up to the anchor holding the abstract is the title
        first_anchor = abstract_cell.find("a")
        title = first_anchor.previousSibling.strip()

    whitespace_re = re.compile(r"[\n\r\t]")
    title = whitespace_re.sub(" ", title)

    escape_slash_re = re.compile(r"\\")  # these seem to have escaped
    title = escape_slash_re.sub("", title)

    return title


def extract_presentation(preso, nanog):
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


def fuzzy_preso_url(speakers, presos):
    preso_map = {}
    # create a reasonable response string for filtering, in post-process
    preso_scrunch = "|".join(presos)

    for s in speakers:
        preso_score = 0
        preso_url = ""
        s_preso = process.extractOne(s[0], presos)  # speaker match
        if s[1] != "":
            a_preso = process.extractOne(s[1], presos)  # affilliation match
        else:
            a_preso = (0, 0)

        if s_preso[1] >= a_preso[1]:
            preso_score = s_preso[1]
            preso_url = s_preso[0]
        else:
            preso_score = a_preso[1]
            preso_url = a_preso[0]

        if preso_score >= 50:
            # reasonably high quality match
            preso_map[s[0]] = preso_url
        else:
            tmp_ = (
                f"lo-quality preso match: ({s_preso[1]}/{a_preso[1]}) - {preso_scrunch}"
            )
            preso_map[s[0]] = tmp_

    return preso_map


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

    unroll_presentations = False  # do we unroll presentation urls?
    presos = ""  # handling of presentation urls
    preso_map = {}

    if len(talk["speakers"]) > 1 and len(talk["presentation"]) > 1:
        unroll_presentations = True
        preso_map = fuzzy_preso_url(talk["speakers"], talk["presentation"])
    elif len(talk["speakers"]) > 1 and len(talk["presentation"]) == 1:
        presos = talk["presentation"][0]
    elif len(talk["speakers"]) == 1 and len(talk["presentation"]) == 1:
        presos = talk["presentation"][0]
    else:
        presos = ""

    # filter out the breaks, etc. that are in the agendas. the check for the
    # non-empty status of the video and the preso fields are to ensure that we
    # do something reasonable here and aren't suppressing hackathon readouts,
    # etc.
    #
    # so. many. lunch variations
    if re.search(
        "(break|breakfast|beer|social event|hackathon|espresso bar"
        "|refreshments|vendor collaboration room|pgp key"
        "|(newcomers|monday|tuesday|welcome|open) lunch|^lunch$|^social|cocktail)",
        talk["title"],
        re.IGNORECASE,
    ) and (video == "" and presos == ""):
        talk_info = None
        return

    # there are some sneaky speaker variations for some agenda items.
    for _s in talk["speakers"]:
        if re.search("(on your own|^sponsor)", _s[0],
                     re.IGNORECASE,) and (video == "" and presos == ""):
            talk_info = None
            return

    if len(talk["speakers"]) > 1 and unroll_presentations:
        for s in talk["speakers"]:
            row = [
                NANOG_NUM,
                s[0],
                s[1],
                talk["title"],
                video,
                preso_map[s[0]],
                talk["origin"],
            ]
            talk_info.append(row)
    elif len(talk["speakers"]) > 1 and not unroll_presentations:
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


def process_agenda_table(agenda_table, nanog):
    # heading = []
    # for th in agenda_table.find_all("th"):
    #     heading.append(th.text.strip())
    #
    # handy for figuring out what the table structures look like
    # print(heading)
    #
    # agenda fields: nanog 13-70
    # ['Time/Webcast:', 'Room:', 'Topic/Abstract:', 'Presenter/Sponsor:', 'Presentation Files:']
    #
    # agenda fields: nango 71+
    # ['Time', 'Location', 'Topic', 'Video Files', 'Presentation Files']

    # importing this here for consistency
    global ORIGIN

    nanog_talks = []

    rows = agenda_table.find_all("tr")
    for tr in rows:
        td = tr.find_all("td")
        if len(td) < 2:
            continue

        if nanog <= 70:
            # the following works up to NANOG 70
            (videos, presos) = extract_presentation(td[4], nanog)
            talk = {
                "speakers": extract_speaker(td[3], nanog),
                "title": extract_title(td[2], nanog),
                "timeslot": td[0].text.strip(),
                "presentation": presos,
                "video": videos,
                "origin": ORIGIN,
            }
        else:
            (videos, _) = extract_presentation(td[3], nanog)
            (_, presos) = extract_presentation(td[4], nanog)
            talk = {
                "speakers": extract_speaker(td[2], nanog),
                "title": extract_title(td[2], nanog),
                "timeslot": td[0].text.strip(),
                "presentation": presos,
                "video": videos,
                "origin": ORIGIN,
            }

        talk_row = gen_talk_rows(talk)
        if talk_row is not None:
            for r in talk_row:
                nanog_talks.append(r)

    return nanog_talks


def get_agenda_tables(agenda_file, nanog):
    with open(agenda_file) as a_file:
        soup = BeautifulSoup(a_file, "html.parser")

    # NANOG specific overrides
    table_attr = {}
    if nanog <= 70:
        table_attr = {"class": "table_agenda sticky-enabled"}

    agenda_tables = soup.find_all("table", attrs=table_attr)

    export_talks = []
    for agenda in agenda_tables:
        talks = process_agenda_table(agenda, nanog)
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
        type=int,
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

    agenda = get_agenda_tables(args.agenda, NANOG_NUM)

    if args.csv_file:
        with open(args.csv_file, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerows(agenda)

    else:
        pprint.pprint(agenda, width=100)


if __name__ == "__main__":
    main()

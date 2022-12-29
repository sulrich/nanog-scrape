#!/usr/bin/env python3

import argparse
import csv
import operator
import re

# liz-merge.py
#
# this is a single use tool (ideally) that is to be used to merge the
# golden master speaker date with liz culley's fork that has the tags added.
# this will also be used to scrub down the youtube URLs to something that can be
# consistently referenced.
#

# overview
#
# load both csv's, note the index and generate a composite key of the fllowing
# fields.
# - NANOG
# - SPEAKER
# - TITLE
# if these are identical across records grab the tags and the keywords from
# liz's copy and merge into an output that is indexed uniquely based on the
# record number


# this assumes that the gsd and the ssd structures have some common fields
BLANK_ENTRY = {  # template blank speaker entry
    "INDEX": 0,
    "NANOG": "",
    "DATE": "",
    "LOCATION": "",
    "TALK_ORDER": "",
    "SPEAKER": "",
    "AFFILIATION": "",
    "TITLE": "",
    "TALK_TYPE": "",
    "YOUTUBE": "",
    "PRESO_FILES": "",
    "DURATION_MIN": "",
    "TAGS": "",
    "TOPICS": "",
    "ACADEMIC": "",
    "ORIGIN": "",
}

# dict to store per-NANOG breakdown of speakers
PER_NANOG_SPEAKERS = {}

# dict to store dict of NANOG dates and locations, keyed by NANOG
NANOG_INFO = {}

CSV_FIELDS = [  # csv export fields in order
    "INDEX",
    "NANOG",
    "DATE",
    "LOCATION",
    "TALK_ORDER",
    "SPEAKER",
    "AFFILIATION",
    "TITLE",
    "TALK_TYPE",
    "YOUTUBE",
    "PRESO_FILES",
    "DURATION_MIN",
    "TAGS",
    "TOPICS",
    "ACADEMIC",
    "ORIGIN",
]


def strip_html(data):
    """quick and dirty HTML tag stripping for titles."""
    tag_re = re.compile("<.*?>")
    return re.sub(tag_re, "", data)


def load_csv(csv_in: str) -> list:
    """load_csv"""
    csv_list = list()
    with open(csv_in, "rt", newline="") as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            row["NANOG"] = int(row["NANOG"])  # make this a real int
            csv_list.append(row)

    return csv_list


def write_csv(csvfile_out, fields, dataset):
    """write_csv - pretty self-evident

    :csvfile_out: path to the csv file to export
    :fields: list of the fieldnames to export
    :data: LoD with the rows to be written
    :returns: nothing

    """
    with open(csvfile_out, "w", newline="") as csvout:
        writer = csv.DictWriter(csvout, fieldnames=fields)
        writer.writeheader()
        export_index = 0
        for row in dataset:
            export_index += 1
            row["INDEX"] = export_index
            writer.writerow(row)

    return


def normalize_youtube(url):
    url_re = re.compile(r"(?:v=|be/)(.*?)(?:\&|\?|$)")
    m = url_re.search(url)

    if m:
        return "http://youtube.com/watch?v=" + m.group(1)


def main():
    """main - where the action is"""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--gsd",
        help="golden speaker data csv",
        dest="gsd_csv",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--liz",
        help="liz speaker data csv",
        dest="liz_csv",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--out",
        help="merged export csv",
        dest="merged_csv",
        action="store",
        required=True,
    )
    args = parser.parse_args()

    gsd = load_csv(args.gsd_csv)
    lsd = load_csv(args.liz_csv)

    merged_speakers = []  # merged entries

    for gsd_spkr in gsd:
        tmp_spkr = BLANK_ENTRY.copy()
        tmp_spkr.update(gsd_spkr)
        tmp_spkr.pop("KEYWORDS")

        # inefficient, but effective in our case
        tag_speaker = [
            liz_spkr
            for liz_spkr in lsd
            if liz_spkr["NANOG"] == gsd_spkr["NANOG"]
            and liz_spkr["SPEAKER"] == gsd_spkr["SPEAKER"]
            and liz_spkr["TITLE"] == gsd_spkr["TITLE"]
        ][0]
        tmp_spkr["TITLE"] = strip_html(gsd_spkr["TITLE"])
        tmp_spkr["TAGS"] = tag_speaker["TAGS"]
        tmp_spkr["TOPICS"] = tag_speaker["TOPICS"]
        tmp_spkr["ACADEMIC"] = tag_speaker["ACADEMIC"]
        tmp_spkr["TALK_TYPE"] = tag_speaker["TALK_TYPE"]
        if tmp_spkr["YOUTUBE"] != "":
            tmp_spkr["YOUTUBE"] = normalize_youtube(tmp_spkr["YOUTUBE"])

        merged_speakers.append(tmp_spkr)

    # sort based on NANOG, then speaker for export
    merged_speakers.sort(key=operator.itemgetter("NANOG", "TALK_ORDER", "SPEAKER"))

    write_csv(args.merged_csv, CSV_FIELDS, merged_speakers)


if __name__ == "__main__":
    main()

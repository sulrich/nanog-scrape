#!/usr/bin/env python3

import argparse
import csv
import operator
import re

from thefuzz import process

# nanog-merge.python3
#
# this is a single use tool (ideally) that is to be used to merge the
# 'raw_speaker_data' which has been manually assembled in the NANOG google
# drive with the 'scraped_speaker_data' that has been generated from the
# agendas that have were gleaned from archive.nanog.org
#
# the "best" data from each is to be used in order to populate a third
# merged_speaker_data CSV file that will be exported with the superset of
# information.
#
# the merge algorithm works something along these lines.
#
# - for each row in the scraped_speaker_data (ssd) file, find the corresponding
# data within the raw_speaker_data (gsd) structure that has a matching title,
# NANOG and speaker_name.
#
# if there's a match in both, then merge the data from the non-duplicative
# fields and export this to the merged_speaker_data structure.
#
#

# this assumes that the gsd and the ssd structures have some common fields
BLANK_ENTRY = {  # template blank speaker entry
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
    "KEYWORDS": "",
    "ORIGIN": "",
}

# dict to store per-NANOG breakdown of speakers
PER_NANOG_SPEAKERS = {}

# dict to store dict of NANOG dates and locations, keyed by NANOG
NANOG_INFO = {}

CSV_FIELDS = [  # csv export fields in order
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
    "KEYWORDS",
    "ORIGIN",
]


def load_csv(csv_in: str) -> list:
    """load_csv"""
    csv_list = list()
    with open(csv_in, "r", newline="") as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            row["NANOG"] = int(row["NANOG"])  # make this a real int
            csv_list.append(row)

    return csv_list


def create_merged_entry(search_entry, target_entry):
    """create_merged_entry(search_entry: dict, target_entry: dict)

    :target_entry: entry that we found in the searched data set
    :search_entry: entry that was used to search in the target data set
    :returns: dict with the merged speaker entry across fields

    since we're here, we can likely assume that the following fields are
    identical across the entries

    - SPEAKER
    - NANOG
    - TITLE
    """

    merged_entry = BLANK_ENTRY.copy()
    merged_entry.update(target_entry)
    merged_entry.update(search_entry)

    # override data/location with blessed info
    merged_entry["DATE"] = NANOG_INFO[search_entry["NANOG"]]["DATE"]
    merged_entry["LOCATION"] = NANOG_INFO[search_entry["NANOG"]]["LOCATION"]

    return merged_entry


def search_entry(entry: dict, target_sd: list):
    """search_entry - performs a logic-addled fuzzy search for a given entry in
    the target speaker data list

    :speaker_entry: dict containing the scraped entry
    :target_sd: list of dicts containing the speaker data to sort through
    :returns:
        - matched_speaker_entry - a dict with the relevant merged fields or None
        - unmatched_speaker_entry - a dict with the relevant unmerged speaker
          data fields or None

    """
    speaker = []
    matched_speaker_entry = {}  # dict with the matched speaker entry
    unmatched_speaker_entry = {}  # dict with the matched speaker entry

    speaker_exact = list(
        filter(
            lambda target_entry: (
                re.search(
                    re.escape(entry["SPEAKER"]), target_entry["SPEAKER"], re.IGNORECASE
                )
                and re.search(
                    re.escape(entry["TITLE"]), target_entry["TITLE"], re.IGNORECASE
                )
            ),
            target_sd,
        )
    )

    if len(speaker_exact) == 1:
        print(f'exact match: {entry["NANOG"]}: {entry["SPEAKER"]} - {entry["TITLE"]}')
        speaker = speaker_exact

    else:
        print(
            f'attempting fuzzy match: {entry["NANOG"]}: '
            f'{entry["SPEAKER"]} - {entry["TITLE"]}'
        )

        # this is expensive, but should yield something to search on
        titles = set(e["TITLE"] for e in target_sd)
        speakers = set(e["SPEAKER"] for e in target_sd)
        fuzzy_title = process.extractOne(entry["TITLE"], titles)
        fuzzy_speaker = process.extractOne(entry["SPEAKER"], speakers)

        speaker_fuzzy = list(
            filter(
                lambda target_entry: (
                    re.search(
                        re.escape(fuzzy_title[0]), target_entry["TITLE"], re.IGNORECASE
                    )
                    and re.search(
                        re.escape(fuzzy_speaker[0]),
                        target_entry["SPEAKER"],
                        re.IGNORECASE,
                    )
                ),
                target_sd,
            )
        )
        if len(speaker_fuzzy) > 0:
            print(
                f'fuzzy match: {speaker_fuzzy[0]["NANOG"]}: '
                f'{speaker_fuzzy[0]["SPEAKER"]} - {speaker_fuzzy[0]["TITLE"]}'
            )
            speaker = speaker_fuzzy
        else:
            print(
                f'fuzzy fail: {entry["NANOG"]}: {entry["SPEAKER"]} - {entry["TITLE"]}'
            )

    if len(speaker) == 1:
        # we have a match! fuzzy or exact.
        matched_speaker_entry = create_merged_entry(entry, speaker[0])
        unmatched_speaker_entry = None
    else:
        print(
            f'unmatched entry: {entry["NANOG"]}: {entry["SPEAKER"]} - {entry["TITLE"]}'
        )
        matched_speaker_entry = None
        unmatched_speaker_entry = create_merged_entry(entry, BLANK_ENTRY.copy())

    return matched_speaker_entry, unmatched_speaker_entry


def filter_nanogs(nog_set, dataset):
    """filter_nanogs - given a set, return a LoD that has the relevant entries.

    :nog_set: set - NANOG meetings to filter for speakers
    :dataset: dataset to filter
    :returns: list of NANOG speakers for associated NANOG meetings

    """

    nanogs = list(filter(lambda entry: entry["NANOG"] in nog_set, dataset))
    return nanogs


def get_nanogs(speaker_data):
    """get_nanogs(speaker_data: list)

    :speaker_data: list of dicts that have the associated speaker data
    :returns: a set of NANOGs found within the speaker_data

    """
    nanogs = set(int(entry["NANOG"]) for entry in speaker_data)
    return set(sorted(nanogs))


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
        for row in dataset:
            writer.writerow(row)

    return


def load_nanog_info(nanog_info_csv):
    """load_nanog_info(nanog_info_csv)

    :nanog_info_csv: path to CSV with NANOG info data
    :returns: DoD containing the nanog dates and locations keyed by NANOG #

    """
    _nanog_info = {}
    ninfo = load_csv(nanog_info_csv)
    for n in ninfo:
        _nanog_info[n["NANOG"]] = {
            "DATE": n["DATE"],
            "LOCATION": n["LOCATION"],
        }

    return _nanog_info


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--raw-speaker-data",
        help="raw speaker data",
        dest="raw_speaker_data",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--scraped-speaker-data",
        help="scraped speaker data",
        dest="scraped_speaker_data",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--nanog-dates-locs",
        help="NANOG dates and locations CSV",
        dest="nanog_dates_locs",
        action="store",
        required=True,
    )
    parser.add_argument(
        "--merged-csv-out",
        help="csv file to output merged entries",
        dest="merged_csv_out",
        action="store",
        required=False,
    )
    parser.add_argument(
        "--unmatched-csv-out",
        help="csv file to output unmatched",
        dest="unmatched_csv_out",
        action="store",
        required=False,
    )
    parser.add_argument(
        "--fullmerge",
        help="fully merge elements into merge-csv-out",
        dest="fullmerge",
        action="store_true",
        required=False,
    )
    args = parser.parse_args()

    rsd = load_csv(args.raw_speaker_data)
    ssd = load_csv(args.scraped_speaker_data)

    global NANOG_INFO
    NANOG_INFO = load_nanog_info(args.nanog_dates_locs)

    # the data sets are not entirely aligned.  some NANOGs are tracked only in
    # one of the datasets.  get a list of the respective raw and scraped NANOGs
    rsd_nanogs = get_nanogs(rsd)
    ssd_nanogs = get_nanogs(ssd)

    # extract the respective sets
    rsd_only = rsd_nanogs.difference(ssd_nanogs)
    ssd_only = ssd_nanogs.difference(rsd_nanogs)
    intersecting_sd = rsd_nanogs.intersection(ssd_nanogs)

    # filter the datasets to relevant NANOGs
    rsd_nanog_speakers = filter_nanogs(rsd_only, rsd)
    ssd_nanog_speakers = filter_nanogs(ssd_only, ssd)
    # grabs all of the entries from the scraped speaker data to be used to
    # search against the raw speaker data
    shared_nanog_speakers = filter_nanogs(intersecting_sd, ssd)

    # generate a dict of LoDs containing the raw speaker data keyed by nanog
    # this speeds up the fuzzy searching
    for n in intersecting_sd:
        m = list(filter(lambda e: e["NANOG"] == n, rsd))
        PER_NANOG_SPEAKERS[n] = m

    merged_speakers = []  # merged entries
    unmatched_scraped_entries = []  # scraped entries which don't match in the rsd

    # first pass - add the NANOGs that are rsd_only into the mix
    for raw_speaker in rsd_nanog_speakers:
        tmp_spkr = BLANK_ENTRY.copy()
        tmp_spkr.update(raw_speaker)
        # override data/location with blessed info
        tmp_spkr["DATE"] = NANOG_INFO[raw_speaker["NANOG"]]["DATE"]
        tmp_spkr["LOCATION"] = NANOG_INFO[raw_speaker["NANOG"]]["LOCATION"]
        merged_speakers.append(tmp_spkr)

    # second pass - add the NANOGs that are ssd_only into the mix
    for scraped_speaker in ssd_nanog_speakers:
        tmp_spkr = BLANK_ENTRY.copy()
        tmp_spkr.update(scraped_speaker)
        # override data/location with blessed info
        tmp_spkr["DATE"] = NANOG_INFO[scraped_speaker["NANOG"]]["DATE"]
        tmp_spkr["LOCATION"] = NANOG_INFO[scraped_speaker["NANOG"]]["LOCATION"]
        merged_speakers.append(tmp_spkr)

    # see what we have with the intersection of the ssd content with the rsd
    # content.
    for entry in shared_nanog_speakers:
        merged_speaker, unmatched_entry = search_entry(
            entry, PER_NANOG_SPEAKERS[entry["NANOG"]]
        )
        if merged_speaker is not None:
            merged_speakers.append(merged_speaker)

        if unmatched_entry is not None:
            if args.fullmerge:
                merged_speakers.append(unmatched_entry)
            else:
                unmatched_scraped_entries.append(unmatched_entry)

    # sort based on NANOG, then speaker for export
    merged_speakers.sort(key=operator.itemgetter("NANOG", "TALK_ORDER", "SPEAKER"))
    unmatched_scraped_entries.sort(key=operator.itemgetter("NANOG", "SPEAKER"))

    if args.merged_csv_out:
        write_csv(args.merged_csv_out, CSV_FIELDS, merged_speakers)

    if args.unmatched_csv_out:
        write_csv(args.unmatched_csv_out, CSV_FIELDS, unmatched_scraped_entries)


if __name__ == "__main__":
    main()

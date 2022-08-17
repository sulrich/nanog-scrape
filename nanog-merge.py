#!/usr/bin/env python3

import argparse
import csv
import pprint
import operator


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

BLANK_ENTRY = {
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


def load_csv(csv_in: str) -> list:
    """load_csv"""
    csv_list = list()
    with open(csv_in, "r", newline="") as csvfile:
        csv_reader = csv.DictReader(csvfile)
        for row in csv_reader:
            row["NANOG"] = int(row["NANOG"])
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

    # merged_entry = {
    #     "NANOG": search_entry["NANOG"],
    #     "SPEAKER": search_entry["SPEAKER"],
    #     "TITLE": search_entry["TITLE"],
    #     "AFFILIATION": search_entry["AFFILIATION"],
    # }

    merged_entry = BLANK_ENTRY
    merged_entry.update(target_entry)
    merged_entry.update(search_entry)

    #     merged_entry["YOUTUBE"] = search_entry["YOUTUBE"]
    # elif target_entry["YOUTUBE"] != "":
    #     merged_entry["YOUTUBE"] = target_entry["YOUTUBE"]
    # else:
    #     merged_entry["YOUTUBE"] = ""

    # if search_entry["PRESO_FILES"] != "":
    #     merged_entry["PRESO_FILES"] = search_entry["PRESO_FILES"]
    # else:
    #     merged_entry["PRESO_FILES"] = ""

    # if search_entry["ORIGIN"] != "":
    #     merged_entry["ORIGIN"] = search_entry["ORIGIN"]
    # elif target_entry["ORIGIN"] != "":
    #     merged_entry["ORIGIN"] = target_entry["ORIGIN"]
    # else:
    #     merged_entry["ORIGIN"] = ""

    # if target_entry["LOCATION"] != "":
    #     merged_entry["LOCATION"] = target_entry["LOCATION"]
    # else:
    #     merged_entry["LOCATION"] = ""

    # if target_entry["DATE"] != "":
    #     merged_entry["DATE"] = target_entry["DATE"]
    # else:
    #     merged_entry["DATE"] = ""

    # if target_entry["DURATION_MIN"] != "":
    #     merged_entry["DURATION_MIN"] = target_entry["DURATION_MIN"]
    # else:
    #     merged_entry["DURATION_MIN"] = ""

    # if target_entry["TAGS"] != "":
    #     merged_entry["TAGS"] = target_entry["TAGS"]
    # else:
    #     merged_entry["TAGS"] = ""

    # if target_entry["KEYWORDS"] != "":
    #     merged_entry["KEYWORDS"] = target_entry["KEYWORDS"]
    # else:
    #     merged_entry["KEYWORDS"] = ""

    return merged_entry


def search_entry(entry: dict, target_sd: list):
    """TODO: Docstring for search_entry.

    :speaker_entry: dict containing the scraped entry
    :target_sd: list of dicts containing the speaker data to sort through
    :returns: dict with the merged speaker entry

    """
    speaker_entry = list(
        filter(
            lambda target_entry: (
                target_entry["NANOG"] == entry["NANOG"]
                and target_entry["SPEAKER"] == entry["SPEAKER"]
                and target_entry["TITLE"] == entry["TITLE"]
            ),
            target_sd,
        )
    )

    if 2 > len(speaker_entry) > 0:
        # this represents a match on the key fields
        print(f'matched entry: {entry["NANOG"]} - {entry["TITLE"]}, {entry["SPEAKER"]}')
        speaker_entry = create_merged_entry(entry, speaker_entry[0])
    else:
        # no match, but the NANOG in the target data set exisets
        print(
            f'unmatched entry: {entry["NANOG"]} - {entry["TITLE"]}, {entry["SPEAKER"]}',
        )
        # speaker_entry = []
        speaker_entry = None

    return speaker_entry


def filter_nanogs(nog_set, dataset):
    """TODO: Docstring for filter_nanogs.

    :nog_set: set - NANOG meetings to filter for speakers
    :dataset: dataset to filter
    :returns: list of NANOG speakers for associated NANOG meetings

    """

    nanogs = list(filter(lambda entry: entry["NANOG"] in nog_set, dataset))
    return nanogs


def get_nanogs(speaker_data):
    """get_nanogs(speaker_data: list)

    :speaker_data: list of dicts that have the speaker data
    :returns: a set of NANOGs found within the speaker_data

    """
    nanogs = set(int(entry["NANOG"]) for entry in speaker_data)
    return set(sorted(nanogs))


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
        "--csv-out",
        help="csv file to output",
        dest="csv_out",
        action="store",
        required=False,
    )
    args = parser.parse_args()

    rsd = load_csv(args.raw_speaker_data)
    ssd = load_csv(args.scraped_speaker_data)

    # the data sets are not entirely aligned.  some NANOGs are tracked only in
    # one of the datasets.  get a list of the respective raw and scraped NANOGs
    rsd_nanogs = get_nanogs(rsd)
    ssd_nanogs = get_nanogs(ssd)

    # extract the respective sets
    rsd_only = rsd_nanogs.difference(ssd_nanogs)
    ssd_only = ssd_nanogs.difference(rsd_nanogs)
    intersecting_sd = rsd_nanogs.intersection(ssd_nanogs)

    # filter the datasets to relevant NANOGs only and generate merged entries
    rsd_nanog_speakers = filter_nanogs(rsd_only, rsd)
    ssd_nanog_speakers = filter_nanogs(ssd_only, ssd)
    shared_nanog_speakers = filter_nanogs(intersecting_sd, ssd)

    merged_speakers = []

    # first pass - add the NANOGs that are rsd_only into the mix
    for raw_speaker in rsd_nanog_speakers:
        tmp_spkr = BLANK_ENTRY.copy()
        tmp_spkr.update(raw_speaker)
        merged_speakers.append(tmp_spkr)

    # second pass - add the NANOGs that are ssd_only into the mix
    for scraped_speaker in ssd_nanog_speakers:
        tmp_spkr = BLANK_ENTRY.copy()
        tmp_spkr.update(scraped_speaker)
        merged_speakers.append(tmp_spkr)

    # see what we have with the intersection of the ssd content with the rsd
    # content.
    for entry in shared_nanog_speakers:
        merged_entry = search_entry(entry, rsd)
        if merged_entry:
            merged_speakers.append(merged_entry)

    merged_speakers.sort(key=operator.itemgetter("NANOG", "SPEAKER"))

    if args.csv_out:
        with open(args.csv_out, "w", newline="") as csvout:
            field_names = [
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
            writer = csv.DictWriter(csvout, fieldnames=field_names)
            writer.writeheader()
            for row in merged_speakers:
                writer.writerow(row)


if __name__ == "__main__":
    main()

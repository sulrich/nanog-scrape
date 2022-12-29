#!/usr/bin/env python3


import argparse
import csv
import logging
import os.path
import traceback
from urllib.parse import parse_qs, urlparse

from youtube_transcript_api import YouTubeTranscriptApi, _errors
from youtube_transcript_api.formatters import TextFormatter


def getYoutubeTranscript(outdir, nanog_num, url):
    """
    given a video url download the transcript and save the raw content to a text
    file in the output_dir.  filename format will be
    $output_dir/nanog-#-youtube-id.txt.

    if the file already exists, don't bother downloading the transcript.
    """

    # create the filename
    if "?" in url:
        u = urlparse(url)
        if "watch" in u.path:
            qs = parse_qs(u.query)  # returns a dict of lists
            video_id = qs["v"][0]
        # sometimes URLs are of the form: https://youtu.be/NZbrpdyJlfg?list=PLO8
        # when this is the case use the path as the video_id
        else:
            video_id = u.path.replace("/", "")

    else:
        url_elems = url.split("/")
        video_id = url_elems[-1]

    transcript_file = "nanog-" + str(nanog_num) + "-" + video_id + ".txt"
    transcript_path = os.path.join(outdir, transcript_file)
    error_file = "errors-" + str(nanog_num) + "-" + video_id + ".txt"
    error_path = os.path.join(outdir, error_file)

    # check to see if the transcript has been downloaded
    if os.path.exists(transcript_path):
        error = f"transcript previously captured: {video_id} {transcript_path} - {url}"
        return error
    if os.path.exists(error_path):
        error = (
            f"error transcript previously unavailable: {video_id} {error_path} - {url}"
        )
        return error

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id)

        # turns the transcript into a text string.
        formatter = TextFormatter()
        formatted = formatter.format_transcript(transcript)

        # write it out to a file.
        with open(transcript_path, "w", encoding="utf-8") as text_file:
            text_file.write(formatted)

        return "captured transcript: " + transcript_path
    # there are videos for which there are no captions generated. log these
    except (_errors.TranscriptsDisabled, _errors.NoTranscriptFound):
        with open(error_path, "w", encoding="utf-8") as error_log:
            traceback.print_exc(file=error_log)

        error = (
            f"unable to capture transcript: {video_id} exception: {error_path} - {url}"
        )
        return error


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csv_file", help="CSV file of all talks")
    parser.add_argument(
        "--outdir",
        help="directory for transcript output",
        dest="output_dir",
        action="store",
        required=False,
    )
    args = parser.parse_args()

    logging.basicConfig(
        filename="transcript-capture.log",
        format="%(asctime)s: %(message)s",
        datefmt="%Y%m%d %H:%M:%S",
        level=logging.INFO,
    )

    with open(args.csv_file, "r", newline="") as f:
        talk_reader = csv.reader(f)

        for row in talk_reader:
            transcript = ""
            if row[4] != "":
                transcript = getYoutubeTranscript(args.output_dir, row[0], row[4])
                logging.info(transcript)


if __name__ == "__main__":
    main()

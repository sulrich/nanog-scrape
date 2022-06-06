#!/usr/bin/env python3


import os.path
import argparse
import csv
import traceback
import logging

from youtube_transcript_api import YouTubeTranscriptApi
from youtube_transcript_api import _errors
from youtube_transcript_api.formatters import TextFormatter


def getYoutubeTranscript(outdir, nanog_num, url):
    """
    given a video url download the transcript and save the raw content to a text
    file in the output_dir.  filename format will be
    $output_dir/nanog-#-youtube-id.txt.

    if the file already exists, don't bother downloading the transcript.
    """

    # create the filename
    url_elems = url.split("/")
    video_id = url_elems[-1]

    transcript_file = "nanog-" + str(nanog_num) + "-" + video_id + ".txt"
    transcript_path = os.path.join(outdir, transcript_file)
    error_file = "errors-" + str(nanog_num) + "-" + video_id + ".txt"
    error_path = os.path.join(outdir, error_file)

    # check to see if the transcript has been downloaded
    if not (os.path.exists(transcript_path) or os.path.exists(error_path)):
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

            error = f"unable to capture transcript: {video_id} exception: {error_path}"
            return error
    else:
        return None


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
                if transcript:
                    logging.info(transcript)
                else:
                    logging.info("transcript for talk exists: " + row[4])


if __name__ == "__main__":
    main()

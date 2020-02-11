#!/usr/bin/env python
"""
FFMPEG wrapper for compressing directories of videos
"""
import argparse
import logging
import os
import shutil
import subprocess




def run_from_cli():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--log-level", default=logging.INFO)
    parser.add_argument("path", help="Path to video or directory containing videos")
    args = parser.parse_args()

    logger = logging.getLogger(__file__)
    logger.setLevel(args.log_level)
    logger.addHandler(logging.StreamHandler())
    logger.handlers[0].setLevel(args.log_level)

    compress(args.path, logger)


def compress(path, logger):
    absolute_path = os.path.abspath(os.path.expanduser(os.path.expandvars(path)))

    if os.path.isdir(absolute_path):
        logger.info(f"Compressing the contents of {absolute_path}")
        compressed_filenames = get_compressed_filenames(absolute_path, logger)
        for filename in os.listdir(absolute_path):
            absolute_filepath = os.path.join(absolute_path, filename)
            if filename in compressed_filenames:
                logger.info(f"SKIPPING[ALREADY COMPRESSED]: {absolute_filepath}")
            elif not os.path.isfile(absolute_filepath):
                logger.info(f"SKIPPING[NOT A FILE]: {absolute_filepath}")
            else:
                logger.info(f"PROCESSING: {absolute_filepath}")
                compress_file(os.path.join(absolute_path, filename), logger)

    else:
        logger.info(f"Compressing {absolute_path}")
        compress_file(absolute_path)

def get_compressed_filenames(absolute_dirpath, logger):
    compressed_filenames = set()
    if os.path.exists(os.path.join(absolute_dirpath, ".compressed")):
        with open(os.path.join(absolute_dirpath, ".compressed"), "r") as compressed_file:
            for filename in compressed_file:
                compressed_filenames.add(filename.strip())

    logger.info(f"Found {len(compressed_filenames)} files already compressed")
    return compressed_filenames


def compress_file(absolute_filepath, logger):
    absolute_dirpath = os.path.dirname(absolute_filepath)
    filename = os.path.basename(absolute_filepath)
    temporary_filepath = os.path.join(absolute_dirpath, f".temp.{filename}")
    command = f'/usr/bin/ffmpeg -stats -y -i "{absolute_filepath}" -vcodec libx265 -crf 24 "{temporary_filepath}"'

    logger.info(command)
    p = subprocess.Popen(command, shell=True, stderr=subprocess.STDOUT)

    if p.wait() == 0:
        parent_dir = os.path.dirname(absolute_filepath)
        filename = os.path.basename(absolute_filepath)
        with open(os.path.join(parent_dir, ".compressed"), "a") as compressed_filenames:
            compressed_filenames.write(f"{filename}\n")
        logger.info(f"Overwriting {absolute_filepath}")
        shutil.move(temporary_filepath, absolute_filepath)
    else:
        p.kill()
        raise RuntimeError


if __name__ == "__main__":
    run_from_cli()

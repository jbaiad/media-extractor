#!/usr/bin/env python
"""
Scraper for twist.moe
"""
import argparse
import base64
import hashlib
import json
import logging
import math
import os
import urllib

from Crypto.Cipher import AES
import requests
from tqdm import tqdm


LOGGER = logging.getLogger(__file__)


BASE_URL = "https://twist.moe"
API_URL = f"{BASE_URL}/api/anime"
CDN_BASE_URL = "https://twistcdn.bunny.sh"

BUFFER_SIZE = 1024
KEY_LENGTH = 32
IV_LENGTH = 16
AES_128_DECRYPTION_KEY = b"LXgIVP&PorO68Rq7dTx8N^lP!Fa5sGJ^*XK"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:69.0) Gecko/20100101 Firefox/69.0",
    "Referer": "https://twist.moe/",
    "x-access-token": "1rj2vRtegS8Y60B3w3qNZm5T2Q0TN2NR"
}


def download_series(twist_series_name: str, output_directory: str, starting_episode: int):
    LOGGER.info(f"Writing {twist_series_name} to {output_directory} beginning at episode {starting_episode}")
    series_data = get_series_data(twist_series_name, starting_episode)
    output_directory = os.path.abspath(output_directory)
    max_digits_necessary = int(math.log(len(series_data), 10)) + 1

    # Make directory if we need to
    if not os.path.exists(output_directory):
        LOGGER.info(f"Making directory: {output_directory}")
        os.makedirs(output_directory)

    for num, source in series_data.items():
        filename = str(num).zfill(max_digits_necessary) + ".mp4"
        with open(os.path.join(output_directory, filename), "wb") as f:
            response = requests.get(source, headers=HEADERS, stream=True)
            total_size = int(response.headers["content-length"])
            for data in tqdm(response.iter_content(chunk_size=BUFFER_SIZE), total=total_size//BUFFER_SIZE, unit="KB",
                             dynamic_ncols=True, desc=f"{os.path.join(output_directory, filename)}"):
                f.write(data)


def get_series_data(twist_series_name: str, starting_episode: int):
    response = requests.get(f"{API_URL}/{twist_series_name}/sources", headers=HEADERS)
    body = json.loads(response.content)

    results = {}
    for episode_dict in body:
        episode_number = episode_dict["number"]
        source = urllib.parse.urljoin(CDN_BASE_URL, aes_decrypt(base64.b64decode(episode_dict["source"])))
        if episode_number >= starting_episode:
            results[episode_number] = source

    return results


def aes_decrypt(message):
    assert message[0:8] == b"Salted__"
    salt, message = message[8:16], message[16:]
    key_iv = get_md5_hash(AES_128_DECRYPTION_KEY + salt, KEY_LENGTH + IV_LENGTH)
    key, iv = key_iv[:KEY_LENGTH], key_iv[-IV_LENGTH:]
    aes = AES.new(key, AES.MODE_CBC, iv)

    decrypted_message = aes.decrypt(message).decode("utf-8")
    message_padding = decrypted_message[-1] if type(decrypted_message[-1]) == int else ord(decrypted_message[-1])
    return decrypted_message[:-message_padding]


def get_md5_hash(data, output_length):
    hashed_data = hashlib.md5(data).digest()
    output = hashed_data

    # MD5 outputs data in 16-byte blocks
    while len(output) < output_length:
        hashed_data = hashlib.md5(hashed_data + data).digest()
        output += hashed_data

    return output[:output_length]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("-l", "--log-level", default=logging.INFO)
    parser.add_argument("--parent-dir", help="Output directory; defaults to $PLEX_HOME/anime",
                        default=os.path.join(os.getenv("PLEX_HOME"), "anime"))
    parser.add_argument("--season", help="Season number; defaults to 1", default=1, type=int)
    parser.add_argument("--starting-episode", help="Episode to start at; defaults to 1", default=1, type=int)
    parser.add_argument("series", help="Twist.moe name for series")
    parser.add_argument("dirname", help="Name of the directory to write episodes into")
    args = parser.parse_args()

    LOGGER.setLevel(args.log_level)
    LOGGER.addHandler(logging.StreamHandler())
    LOGGER.handlers[0].setLevel(args.log_level)

    path_to_dir = os.path.join(args.parent_dir, args.dirname, f"Season {args.season}")
    download_series(args.series, path_to_dir, args.starting_episode)

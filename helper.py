import base64
import re
from datetime import UTC, datetime, timedelta
from urllib.parse import parse_qs, parse_qsl, urlencode, urlparse, urlunparse

import validators
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad
from hashids import Hashids
from pytubefix import YouTube

from config import CRYPTO_KEY, HASH_SALT, NEW_DL_BASE_URL, OLD_DL_BASE_URL

hashids = Hashids(salt=HASH_SALT)


async def hide_name(name):
    words = name.split()
    hidden_words = []
    for word in words:
        if len(word) > 4:
            hidden_word = word[:2] + "***" + word[-2:]
        else:
            hidden_word = word
        hidden_words.append(hidden_word)
    return " ".join(hidden_words)


async def gen_dl_hash():
    expire_time = datetime.now(UTC) + timedelta(hours=6)
    expire_timestamp = int(expire_time.timestamp())
    hashid = hashids.encode(expire_timestamp)
    return hashid


async def decode_string(encoded):
    decoded = "".join([chr(i) for i in hashids.decode(encoded)])
    return decoded


async def decrypt_string(encrypted):
    data = base64.b64decode(encrypted)
    iv_dec = data[:16]
    ciphertext_dec = data[16:]
    cipher_dec = AES.new(CRYPTO_KEY, AES.MODE_CBC, iv_dec)
    decrypted = unpad(cipher_dec.decrypt(ciphertext_dec), AES.block_size)
    return decrypted.decode()


async def is_valid_url(url):
    return validators.url(url)


async def extract_gdrive_id(gdrive_link):
    match = re.match(
        r"^https://drive\.google\.com/file/d/([a-zA-Z0-9_-]+)/?.*$", gdrive_link
    )
    if match:
        return match.group(1)
    query_params = parse_qs(urlparse(gdrive_link).query)
    if "id" in query_params:
        return query_params["id"][0]
    return None


async def gen_video_link(video_url):
    parsed_url = urlparse(video_url)
    if parsed_url.netloc in ["youtube.com", "youtu.be"]:
        yt = YouTube(video_url, "WEB")
        video_streams = yt.streams.filter(progressive=True)
        return video_streams.get_highest_resolution().url
    elif parsed_url.netloc in ["drive.google.com"]:
        gid = await extract_gdrive_id(video_url)
        return f"https://gdl.anshumanpm.eu.org/direct.aspx?id={gid}"
    # For Stream Bot
    elif parsed_url.netloc in OLD_DL_BASE_URL:
        query_params = dict(parse_qsl(parsed_url.query))
        hash_val = await gen_dl_hash()
        query_params["hash"] = hash_val
        new_query = urlencode(query_params)
        return urlunparse(
            (
                parsed_url.scheme,
                NEW_DL_BASE_URL,
                parsed_url.path,
                parsed_url.params,
                new_query,
                parsed_url.fragment,
            )
        )
    else:
        return video_url

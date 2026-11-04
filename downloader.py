import os
import requests
import tempfile

from urllib.parse import urljoin


def download_ts(playlist_url):
    response = requests.get(playlist_url, timeout=30)
    response.raise_for_status()

    content = response.text

    if "#EXT-X-KEY" in content:
        raise Exception("Encrypted playlists are not supported yet.")

    if "#EXT-X-MAP" in content:
        raise Exception("fMP4 playlists are not supported yet.")

    if "#EXT-X-BYTERANGE" in content:
        raise Exception("Byte-range playlists are not supported yet.")

    segments = []

    for line in content.splitlines():
        line = line.strip()

        if not line or line.startswith("#"):
            continue

        segments.append(urljoin(playlist_url, line))

    if not segments:
        raise Exception("No video segments found.")

    temp = tempfile.NamedTemporaryFile(
        suffix=".ts",
        delete=False
    )

    try:
        with temp:
            for index, segment_url in enumerate(segments):
                response = requests.get(
                    segment_url,
                    stream=True,
                    timeout=60
                )
                response.raise_for_status()

                for chunk in response.iter_content(1024 * 1024):
                    if chunk:
                        temp.write(chunk)

                response.close()

        return temp.name

    except Exception:
        if os.path.exists(temp.name):
            os.remove(temp.name)
        raise

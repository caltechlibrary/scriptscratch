# file: croppola.py

# create “smart” thumbnails of images in a directory using the [Croppola
# API](https://croppola.com/documentation/examples/python/)

from pathlib import Path

import requests


def main(
    directory: "path to image directory",  # type: ignore
):
    count = 1
    for p in Path(directory).iterdir():
        if count > 100:
            count += 1
            print("⛔️", p)
            continue
        if p.suffix == ".gif" or p.suffix == ".jpg" or p.suffix == ".png":
            print(p)
            with open(p, "rb") as fp:
                data = fp.read()
        else:
            count += 1
            print("⛔️", p)
            continue

        # smart square thumbnail "showing the most interesting part of the image"
        url = "https://croppola.com/croppola/image.jpg"
        params = {
            "aspectRatio": "1.0",
            "minimumHeight": "80%",
            "scaledMaximumWidth": "400",
            "algorithm": "croppola",
        }
        response = requests.post(url, params=params, data=data)

        # save the thumbnail
        if response.status_code == 200:
            with open(f"{directory}/{p.stem}--thumbnail{p.suffix}", "wb") as f:
                f.write(response.content)
        else:
            print("❌ error " + str(response.status_code))

        count += 1


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

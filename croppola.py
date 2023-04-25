# file: croppola.py

# create “smart” thumbnails of images in a directory using the [Croppola
# API](https://croppola.com/documentation/examples/python/)

from pathlib import Path

import requests


def main(
    directory: "path to image directory",  # type: ignore
    upscale: ("upscale images with smaller dimensions", "flag", "u"),  # type: ignore
):
    count = 1
    for p in Path(directory).iterdir():
        if count > 100:
            count += 1
            print("⛔️", p)
            continue
        if p.suffix == ".jpg" or p.suffix == ".png":
            print(p)
            with open(p, "rb") as fp:
                binary_image_content = fp.read()
        else:
            count += 1
            print("⛔️", p)
            continue

        # smart square thumbnail "showing the most interesting part of the image"
        info_url = "https://croppola.com/croppola/image.json"
        crop_url = "https://croppola.com/croppola/image.jpg"
        thumbnail_filename = f"{p.stem}--thumbnail{p.suffix}"
        if upscale:
            arguments = {
                "aspectRatio": "1.0",
                "scaledHeight": "400",
                "scaledWidth": "400",
                "algorithm": "croppola",
            }
            info_response = requests.post(info_url, params=arguments, data=binary_image_content).json()
            if info_response["imageHeight"] < 400 or info_response["imageWidth"] < 400:
                thumbnail_filename = f"{p.stem}--thumbnail-upscaled{p.suffix}"
            crop_url = f'https://croppola.com/croppola/{info_response["token"]}/image.jpg'
            crop_response = requests.post(crop_url, params=arguments, data=binary_image_content)
        else:
            arguments = {
                "aspectRatio": "1.0",
                "minimumHeight": "80%",
                "scaledMaximumWidth": "400",
                "algorithm": "croppola",
            }
            crop_response = requests.post(crop_url, params=arguments, data=binary_image_content)

        # save the thumbnail
        if crop_response.status_code == 200:
            with open(f"{directory}/{thumbnail_filename}", "wb") as f:
                f.write(crop_response.content)
        else:
            print(f"❌ error {str(crop_response.status_code)}\n{crop_response.text}")

        count += 1


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

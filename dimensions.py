# file: dimensions.py

# save dimensions of images in a directory to a csv file

import csv
import subprocess

from pathlib import Path


def main(
    directory: "path to image directory",  # type: ignore
):
    with open("_outputs/exhibits+thumbnails/_dimensions.csv", "w") as csv_fp:
        csv_writer = csv.DictWriter(
            csv_fp,
            fieldnames=["filename", "width", "height"],
        )
        csv_writer.writeheader()
        for p in Path(directory).iterdir():
            if p.suffix == ".gif" or p.suffix == ".jpg" or p.suffix == ".png":
                print(p)
                result = subprocess.run(
                    [
                        "identify",
                        "-format",
                        "%w,%h",
                        p,
                    ],
                    capture_output=True,
                    text=True,
                )
                width, height = result.stdout.split(",")
                csv_writer.writerow(
                    {
                        "filename": p.name,
                        "width": width,
                        "height": height,
                    }
                )


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

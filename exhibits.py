# file: exhibits.py

# save images from exhibits pages via csv file with URLs

import csv
import os

import requests
from bs4 import BeautifulSoup

def main(
    csv_file: "path to csv file",  # type: ignore
):
    with open(csv_file) as csv_fp:
        csv_reader = csv.DictReader(csv_fp)
        for row in csv_reader:
            print("🌐", row["url"])
            URL = row["url"]
            os.mkdir('_outputs/exhibits/' + URL.split("=")[-1])
            getURL = requests.get(URL, headers={"User-Agent":"Mozilla/5.0"})
            soup = BeautifulSoup(getURL.text, 'html.parser')

            imgs = soup.find_all('img')
            imageURLs = []

            for img in imgs:
                src = img.get('src')
                imageURLs.append(requests.compat.urljoin(URL, src))

            for imageURL in imageURLs:
                image = requests.get(imageURL)
                open('_outputs/exhibits/' + URL.split("=")[-1] + "/" + imageURL.split('/')[-1], 'wb').write(image.content)

if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

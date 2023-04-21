import csv
import json

import requests

from decouple import config

payload = {
    "site_id": config("LIBGUIDES_API_SITE_ID"),
    "key": config("LIBGUIDES_API_KEY"),
    "expand": "owner",
}
response = requests.get("https://lgapi-us.libapps.com/1.1/guides", params=payload)
data = json.loads(response.text)


def search_nested_dicts(nested_dicts, search_strings):
    results = []
    for d in nested_dicts:
        for k, v in d.items():
            if any(s in str(v) for s in search_strings):
                results.append(d)
            if isinstance(v, dict):
                results.extend(search_nested_dicts([v], search_strings))
    return results


# results = search_nested_dicts(data, assets)

with open("in.csv") as csv_in:
    # NOTE `in.csv` is created from copying the Outer HTML from the
    # Search Results table in LibGuides > Tools > Search & Replace

    reader = csv.DictReader(csv_in)

    with open("out.csv", "a", newline="") as csv_out:
        writer = csv.writer(csv_out)
        writer.writerow(["url", "name", "owner_name", "owner_email"])

        for row in reader:
            print(row["GuideID"])
            guide_data = search_nested_dicts(data, [row["GuideID"]])
            writer.writerow(
                [
                    row["URL"],
                    row["Guide Mappings"],
                    f'{guide_data[0]["owner"]["first_name"]} {guide_data[0]["owner"]["last_name"]}',
                    guide_data[0]["owner"]["email"],
                ]
            )

print("🙃 join complete!")

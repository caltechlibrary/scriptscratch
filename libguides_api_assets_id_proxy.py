# file: libguides_api_assets_id_proxy.py

# USAGE: python libguides_api_assets_id_proxy.py

# This script will update the save the IDs and proxy status of assets in a CSV
# file named `_outputs/assets_id_proxy.csv`. The file will have the columns:
# `id`, and `enable_proxy`.

import csv
import json
import requests

from decouple import config  # pypi python-decouple

# response
response = requests.get(
    "https://lgapi-us.libapps.com/1.1/assets",
    params={
        "site_id": config("LIBGUIDES_API_SITE_ID"),
        "key": config("LIBGUIDES_API_KEY"),
    },
)

# print(json.dumps(response, indent=4, sort_keys=True))

# Parse response
data = json.loads(response.text)

# Extract necessary data
rows = []
for item in data:
    id = item["id"]
    if "meta" in item and item["meta"]:
        enable_proxy = item["meta"].get("enable_proxy", "")
    else:
        enable_proxy = ""
    rows.append({"id": id, "enable_proxy": enable_proxy})

# Save data to CSV file
with open("_outputs/assets_id_proxy.csv", "w", newline="") as csvfile:
    fieldnames = ["id", "enable_proxy"]
    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow(row)

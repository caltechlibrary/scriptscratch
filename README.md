# Table of Contents

## `links.py`

Prerequisites:

Values must exist for the LibApps items in `settings.ini`. Required packages for the script can be installed with `pipenv install`.

Usage: `python links.py _inputs/links.csv`

This script will update the URLs of link assets in LibGuides that are provided in a CSV file. The CSV file should have the columns: "URL" and "NewURL".

Caveats:

- It will only update the URL if the two provided URLs are different.
- If there are multiple links found with the old URL, it will not update any of them.

### `links.side`

This file demonstrates using the Selenium IDE browser extension to set up example link assets for the script and also to delete them.

The base `url` key should be updated when using it in Selenium. It also assumes a user is already logged in to LibApps in the browser.

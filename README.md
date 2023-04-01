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

## `url_proxy_decode.py`

Usage: `python url_proxy_decode.py _inputs/file.csv`

This script will update the URLs and the Use Proxy? toggle of assets in LibGuides that are provided in a CSV file. The CSV file should have the columns: "ID", "Type", "Name", "URL", and "proxy_toggle".

Entries in `settings.ini` are required for:

- `CURRENT_PREFIX`
- `FORMER_PREFIX`
- `EXCEPTION_DOMAINS`

### `create_example_assets_for_url_proxy_decode.py`

Selenium IDE file for creating example Link and Book assets that can be used with the `url_proxy_decode.py` script.

Values in `settings.ini` to work with the example assets should be set to:

- `CURRENT_PREFIX=https://go.example.net/redirector/example.edu?url=`
- `FORMER_PREFIX=https://example.idm.example.org/login?url=`
- `EXCEPTION_DOMAINS=exception1.example.com,exception2.example.com,exception3.example.com,exception4.example.com`

### `libguides_api_assets_id_proxy.py`

This script will update the save the IDs and proxy status of assets in a CSV file named `_outputs/assets_id_proxy.csv`. The file will have the columns: `id`, and `enable_proxy`.

Usage: python libguides_api_assets_id_proxy.py

The contents of the CSV file can be used to lookup the proxy status of assets in a sheet exported from the LibGuides Assets web interface.

Entries in `settings.ini` are required for:

- `LIBGUIDES_API_SITE_ID`
- `LIBGUIDES_API_KEY`

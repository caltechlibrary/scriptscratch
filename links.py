# file: links.py

# USAGE: python links.py _inputs/file.csv

# This script will update the URLs of link assets in LibGuides that are provided
# in a CSV file. The CSV file should have the columns: "URL" and "NewURL".
#
# Caveats:
# - It will only update the URL if the two provided URLs are different.
# - If there are multiple links found with the old URL, it will not update any
#   of them.

import csv

from decouple import config  # pypi python-decouple

from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError


def main(
    csv_file: "path to csv file",  # type: ignore
):
    with sync_playwright() as playwright:
        try:
            b = playwright.firefox.launch()
            p = b.new_page(
                base_url=config("LIBAPPS_BASE_URL"), record_video_dir="_outputs"
            )
            p.goto("/libapps/login.php")
            p.fill("#s-libapps-email", config("LIBAPPS_USERNAME"))
            p.fill("#s-libapps-password", config("LIBAPPS_PASSWORD"))
            p.click("#s-libapps-login-button")
            p.wait_for_load_state("networkidle")
            p.goto("/libguides/assets.php")
            with open(csv_file) as csv_fp:
                csv_reader = csv.DictReader(csv_fp)
                for row in csv_reader:
                    print("📍", row["Name"])
                    if row["URL"] == row["NewURL"]:
                        continue
                    if row["NewURL"] == "":
                        continue
                    print("🔎", row["URL"])
                    p.locator("#type").select_option("Link")
                    p.locator("#assets__filter__url").fill(row["URL"])
                    p.locator(
                        "#lg-admin-asset-filter .datatable-filter__button--submit"
                    ).click()
                    p.wait_for_load_state("networkidle")
                    p.wait_for_selector(
                        "#s-lg-admin-datatable-content_processing", state="hidden"
                    )
                    if (
                        p.locator("#s-lg-admin-datatable-content_info")
                        .text_content()
                        .startswith("Showing 0 to 0 of 0 entries")
                    ):
                        print("❌ NO LINKS FOUND")
                        continue
                    elif (
                        not p.locator("#s-lg-admin-datatable-content_info")
                        .text_content()
                        .startswith("Showing 1 to 1 of 1 entries")
                    ):
                        print("❌ MULTIPLE LINKS FOUND")
                        continue
                    else:
                        p.locator(".fa-edit").click()
                        p.locator("#url").fill(row["NewURL"])
                        # clicking the label rather than the input works
                        p.locator("#label-enable_proxy_0").click()
                        p.wait_for_load_state("networkidle")
                        p.locator("#s-lib-alert-btn-first").click()
                        p.wait_for_load_state("networkidle")
                        print("✅", row["NewURL"])
            b.close()
        except PlaywrightTimeoutError as e:
            print(e)
            b.close()


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

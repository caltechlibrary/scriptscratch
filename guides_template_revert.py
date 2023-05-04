import requests
import json

from decouple import config  # pypi python-decouple
from playwright.sync_api import (
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


def main(
    groups: ("comma-delimited list of group IDs"),  # type: ignore
):

    # Make GET request to API endpoint and parse JSON response.
    payload = {
        "site_id": config("LIBGUIDES_API_SITE_ID"),
        "key": config("LIBGUIDES_API_KEY"),
        "group_ids": groups,
    }
    response = requests.get("https://lgapi-us.libapps.com/1.1/guides", params=payload)
    # print(response.text)
    data = json.loads(response.text)
    # print(data)
    # Get the keys from the first item in the JSON data.
    keys = list(data[0].keys())

    with sync_playwright() as playwright:
        try:
            browser = playwright.firefox.launch()
            page = browser.new_page(
                base_url=config("LIBAPPS_BASE_URL"),
                record_video_dir="_outputs",
            )
            page.goto("/libapps/login.php")
            page.fill("#s-libapps-email", config("LIBAPPS_USERNAME"))
            page.fill("#s-libapps-password", config("LIBAPPS_PASSWORD"))
            page.click("#s-libapps-login-button")
            page.wait_for_load_state("networkidle")
            for item in data:
                print(item["name"])
                page.goto(f"/libguides/admin_c.php?g={item['id']}")
                print(f"/libguides/admin_c.php?g={item['id']}")
                page.get_by_title("Guide Layout").click()
                page.get_by_role("link", name="Guide Navigation Layout").click()
                print(page.locator("#select2-chosen-1").text_content(), end=" ")
                if (
                    page.locator("#select2-chosen-1").text_content()
                    == "Caltech Library - Guides - Tab Layout"
                ):
                    page.locator("#select2-chosen-1").click()
                    page.get_by_role(
                        "option", name="Inherit Layout From System / Group Settings"
                    ).click()
                    print("➡️ Inherit Layout From System / Group Settings", end=" ")
                    page.get_by_role("button", name="Save").click()
                    print("✨")
                elif (
                    page.locator("#select2-chosen-1").text_content()
                    == "Caltech Library - Guides - Side-Nav Layout"
                ):
                    page.locator("#select2-chosen-1").click()
                    page.get_by_role(
                        "option", name="System Default - Side-Nav Layout"
                    ).click()
                    print("➡️ System Default - Side-Nav Layout", end=" ")
                    page.get_by_role("button", name="Save").click()
                    print("✨")
                else:
                    print("❓")
                page.wait_for_load_state("networkidle")
        except PlaywrightTimeoutError as e:
            print(e)
            browser.close()


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

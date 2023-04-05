# file: asset_proxy_cleanup.py

# This script will report on assets in LibGuides with URLs that are proxied
# inappropriately. Link and Book assets will be checked for a proxy prefix on
# the URL or for a URL with a domain in the exception list that should not be
# proxied. The `--update` flag will update the assets with the appropriate
# changes.

# Required values in `settings.ini` include:
#
# - LIBGUIDES_API_SITE_ID
# - LIBGUIDES_API_KEY
# - PROXY_PREFIXES
# - EXCEPTION_DOMAINS
# - LIBAPPS_BASE_URL [with `--update` only]
# - LIBAPPS_USERNAME [with `--update` only]
# - LIBAPPS_PASSWORD [with `--update` only]

# USAGE: python asset_proxy_cleanup.py [--update]

import json
import requests
import urllib.parse

from decouple import config  # pypi python-decouple

from playwright.sync_api import (
    expect,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)

types = {
    1: "Rich Text / HTML",
    2: "Link",
    3: "RSS Feed",
    4: "Document / File",
    5: "Book from the Catalog",
    6: "Poll",
    7: "Google Search",
    9: "Media / Widget",
    10: "Database",
    11: "Guide List",
    12: "LibAnswers Widget",
    13: "LibWizard Item",
    14: "Remote Script",
}


def main(
    update: ("update records", "flag", "u"),  # type: ignore
    dry_run: ("mock update without saving", "flag", "d"),  # type: ignore
):

    # LibGuides API Response
    response = requests.get(
        "https://lgapi-us.libapps.com/1.1/assets",
        params={
            "site_id": config("LIBGUIDES_API_SITE_ID"),
            "key": config("LIBGUIDES_API_KEY"),
        },
    )

    # Parse Response
    data = json.loads(response.text)

    with sync_playwright() as playwright:
        try:
            if update:
                if dry_run:
                    print("\n🐞 DRY RUN: no changes will be saved")
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
            for asset in data:
                if (
                    types[asset["type_id"]] != "Link"
                    and types[asset["type_id"]] != "Book from the Catalog"
                    and types[asset["type_id"]] != "Database"
                ):
                    continue
                # NOTE reset loop variables
                toggled = ""
                use_proxy = "No"
                if "meta" in asset and asset["meta"]:
                    if asset["meta"].get("enable_proxy", ""):
                        use_proxy = "Yes"
                proxy_prefix = contains_proxy_prefix(asset["url"])
                exception_domain = contains_exception_domain(asset["url"])
                if proxy_prefix:
                    print_asset(asset, use_proxy)
                    working_url = urllib.parse.unquote(
                        asset["url"].replace(proxy_prefix, "")
                    )
                    if not update:
                        print("➡️  Replace URL", working_url)
                        if not exception_domain and use_proxy == "No":
                            print("➡️  Toggle “Use Proxy?” to Yes")
                        elif exception_domain and use_proxy == "Yes":
                            print(f"[Exception: {exception_domain}]")
                            print("➡️  Toggle “Use Proxy?” to No")
                    elif update:
                        if types[asset["type_id"]] == "Database":
                            page.goto("/libguides/az.php")
                        else:
                            page.goto("/libguides/assets.php")
                        # NOTE reset search
                        page.get_by_role("textbox", name="ID").fill("")
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 25"
                        )
                        page.get_by_role("textbox", name="ID").fill(str(asset["id"]))
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 1 of 1 entries"
                        )
                        page.screenshot(
                            path=f'_outputs/{asset["id"]}-filtered.png'
                        )
                        page.get_by_title("Edit Item").click()
                        page.locator("#form-group-enable_proxy").wait_for()
                        page.screenshot(
                            path=f'_outputs/{asset["id"]}-pre-edit.png'
                        )
                        if "Link" in types[asset["type_id"]]:
                            page.get_by_label("Link URL").fill(working_url)
                        elif "Book" in types[asset["type_id"]]:
                            page.get_by_role("textbox", name="URL", exact=True).fill(
                                working_url
                            )
                        if not exception_domain and use_proxy == "No":
                            # NOTE clicking the label rather than the input works
                            page.locator("#label-enable_proxy_1").click()
                            toggled = "☑️  Toggled “Use Proxy?” to Yes"
                        elif exception_domain and use_proxy == "Yes":
                            # NOTE clicking the label rather than the input works
                            page.locator("#label-enable_proxy_0").click()
                            toggled = f"☑️  Toggled “Use Proxy?” to No [Exception: {exception_domain}]"
                        page.screenshot(
                            path=f'_outputs/{asset["id"]}-pre-save.png'
                        )
                        if dry_run:
                            page.get_by_role("button", name="Cancel").click()
                        else:
                            page.get_by_role("button", name="Save").click()
                        print("☑️  Replaced URL", working_url)
                        if toggled:
                            print(toggled)
                elif exception_domain and use_proxy == "Yes":
                    print_asset(asset, use_proxy)
                    if not update:
                        print(
                            f"➡️  Toggle “Use Proxy?” to No [Exception: {exception_domain}]"
                        )
                    if update:
                        if types[asset["type_id"]] == "Database":
                            page.goto("/libguides/az.php")
                        else:
                            page.goto("/libguides/assets.php")
                        # NOTE reset search
                        page.get_by_role("textbox", name="ID").fill("")
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 25"
                        )
                        page.get_by_role("textbox", name="ID").fill(str(asset["id"]))
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 1 of 1 entries"
                        )
                        page.screenshot(
                            path=f'_outputs/{asset["id"]}-filtered.png'
                        )
                        page.get_by_title("Edit Item").click()
                        page.locator("#form-group-enable_proxy").wait_for()
                        page.screenshot(
                            path=f'_outputs/{asset["id"]}-pre-edit.png'
                        )
                        # NOTE clicking the label rather than the input works
                        page.locator("#label-enable_proxy_0").click()
                        page.screenshot(
                            path=f'_outputs/{asset["id"]}-pre-save.png'
                        )
                        if dry_run:
                            page.get_by_role("button", name="Cancel").click()
                        else:
                            page.get_by_role("button", name="Save").click()
                        print(
                            f"☑️  Toggled “Use Proxy?” to No [Exception: {exception_domain}]"
                        )
            if update:
                browser.close()
                if dry_run:
                    print("\n🐞 DRY RUN: no changes were saved")
            print("")
        except PlaywrightTimeoutError as e:
            print(e)
            if update:
                browser.close()


def print_asset(asset, use_proxy):
    print("")
    print(
        asset["id"],
        types[asset["type_id"]],
        f"[Use Proxy? {use_proxy}]",
        asset["name"],
    )
    print(asset["url"])


def contains_proxy_prefix(url):
    for prefix in config("PROXY_PREFIXES").split(","):
        if prefix in url:
            return prefix
    return False


def contains_exception_domain(url):
    for domain in config("EXCEPTION_DOMAINS").split(","):
        if domain in url:
            return domain
    return False


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

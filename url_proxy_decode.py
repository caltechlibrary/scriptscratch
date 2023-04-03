# file: url_proxy_decode.py

# USAGE: python url_proxy_decode.py _inputs/file.csv

# This script will update the URLs and the Use Proxy? toggle of assets in
# LibGuides that are provided in a CSV file. The CSV file should have the
# columns: "ID", "Type", "Name", "URL", and "proxy_toggle".

import csv
import urllib.parse

from decouple import config  # pypi python-decouple

from playwright.sync_api import (
    expect,
    sync_playwright,
    TimeoutError as PlaywrightTimeoutError,
)


def main(
    dry_run: ("dry run", "flag", "d"),  # type: ignore
    csv_file: "path to csv file",  # type: ignore
):
    with sync_playwright() as playwright:
        try:
            browser = playwright.firefox.launch()
            page = browser.new_page(
                base_url=config("LIBAPPS_BASE_URL"),
                record_video_dir="_outputs/url_prxy_dcd",
            )
            page.goto("/libapps/login.php")
            page.fill("#s-libapps-email", config("LIBAPPS_USERNAME"))
            page.fill("#s-libapps-password", config("LIBAPPS_PASSWORD"))
            page.click("#s-libapps-login-button")
            page.wait_for_load_state("networkidle")
            page.goto("/libguides/assets.php")
            # NOTE asset_list.csv export contains byte-order mark (BOM)
            with open(csv_file, encoding="utf-8-sig") as csv_fp:
                csv_reader = csv.DictReader(csv_fp)
                for row in csv_reader:
                    page.get_by_role("textbox", name="ID").fill("")
                    page.keyboard.up("ArrowRight")
                    expect(page.get_by_role("status")).to_contain_text(
                        "Showing 1 to 25"
                    )
                    # page.screenshot(path=f'_outputs/url_prxy_dcd/{row["ID"]}-reset.png')
                    print("\n")
                    if row["proxy_toggle"] == "1":
                        use_proxy = "Yes"
                    else:
                        use_proxy = "No"
                    print(row["ID"], f"[Use Proxy? {use_proxy}]", row["Name"])
                    print(row["URL"])
                    if row["URL"].startswith(config("CURRENT_PREFIX")):
                        replacement_url = urllib.parse.unquote(
                            row["URL"].replace(config("CURRENT_PREFIX"), "")
                        )
                        print("Replace URL ➡️ ", replacement_url)
                        page.get_by_role("textbox", name="ID").fill(row["ID"])
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 1 of 1 entries"
                        )
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-filtered.png'
                        )
                        page.get_by_title("Edit Item").click()
                        page.locator("#form-group-enable_proxy").wait_for()
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-edit.png'
                        )
                        if "Link" in row["Type"]:
                            page.get_by_label("Link URL").fill(replacement_url)
                        elif "Book" in row["Type"]:
                            page.get_by_role("textbox", name="URL", exact=True).fill(
                                replacement_url
                            )
                        exception_domain = contains_exception_domain(replacement_url)
                        if exception_domain:
                            print(
                                f"Toggle “Use Proxy?” to ❌ No [Exception: {exception_domain}]"
                            )
                            # NOTE clicking the label rather than the input works
                            page.locator("#label-enable_proxy_0").click()
                            page.screenshot(
                                path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-save.png'
                            )
                            if dry_run:
                                page.get_by_role("button", name="Cancel").click()
                                continue
                            page.get_by_role("button", name="Save").click()
                            continue
                        if row["proxy_toggle"] != "1":
                            print("Toggle “Use Proxy?” to ✅ Yes")
                            # NOTE clicking the label rather than the input works
                            page.locator("#label-enable_proxy_1").click()
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-save.png'
                        )
                        if dry_run:
                            page.get_by_role("button", name="Cancel").click()
                            continue
                        page.get_by_role("button", name="Save").click()
                    elif row["URL"].startswith(config("FORMER_PREFIX")):
                        replacement_url = urllib.parse.unquote(
                            row["URL"].replace(config("FORMER_PREFIX"), "")
                        )
                        print("Replace URL ➡️ ", replacement_url)
                        page.get_by_role("textbox", name="ID").fill(row["ID"])
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 1 of 1 entries"
                        )
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-filtered.png'
                        )
                        page.get_by_title("Edit Item").click()
                        page.locator("#form-group-enable_proxy").wait_for()
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-edit.png'
                        )
                        if "Link" in row["Type"]:
                            page.get_by_label("Link URL").fill(replacement_url)
                        elif "Book" in row["Type"]:
                            page.get_by_role("textbox", name="URL", exact=True).fill(
                                replacement_url
                            )
                        exception_domain = contains_exception_domain(replacement_url)
                        if exception_domain:
                            print(
                                f"Toggle “Use Proxy?” to ❌ No [Exception: {exception_domain}]"
                            )
                            # NOTE clicking the label rather than the input works
                            page.locator("#label-enable_proxy_0").click()
                            page.screenshot(
                                path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-save.png'
                            )
                            if dry_run:
                                page.get_by_role("button", name="Cancel").click()
                                continue
                            page.get_by_role("button", name="Save").click()
                            continue
                        if row["proxy_toggle"] != "1":
                            print("Toggle “Use Proxy?” to ✅ Yes")
                            # NOTE clicking the label rather than the input works
                            page.locator("#label-enable_proxy_1").click()
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-save.png'
                        )
                        if dry_run:
                            page.get_by_role("button", name="Cancel").click()
                            continue
                        page.get_by_role("button", name="Save").click()
                    elif row["proxy_toggle"] == "1":
                        print(f"Toggle “Use Proxy?” to ❌ No")
                        page.get_by_role("textbox", name="ID").fill(row["ID"])
                        page.keyboard.up("ArrowRight")
                        expect(page.get_by_role("status")).to_contain_text(
                            "Showing 1 to 1 of 1 entries"
                        )
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-filtered.png'
                        )
                        page.get_by_title("Edit Item").click()
                        page.locator("#form-group-enable_proxy").wait_for()
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-edit.png'
                        )
                        # NOTE clicking the label rather than the input works
                        page.locator("#label-enable_proxy_0").click()
                        page.screenshot(
                            path=f'_outputs/url_prxy_dcd/{row["ID"]}-pre-save.png'
                        )
                        if dry_run:
                            page.get_by_role("button", name="Cancel").click()
                            continue
                        page.get_by_role("button", name="Save").click()
                    else:
                        print("No changes needed ⛔️")
            print("\n")
            browser.close()
        except PlaywrightTimeoutError as e:
            print(e)
            browser.close()


def contains_exception_domain(url):
    for domain in config("EXCEPTION_DOMAINS").split(","):
        if domain in url:
            return domain
    return False


if __name__ == "__main__":
    # fmt: off
    import plac; plac.call(main)

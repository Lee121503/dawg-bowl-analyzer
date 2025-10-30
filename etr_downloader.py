from playwright.sync_api import sync_playwright
import os
import time

def download_etr_csv(download_path="data/etr_fd_main.csv"):
    with sync_playwright() as p:
        print("🚀 Launching persistent browser...")
        user_data_dir = os.path.join(os.getcwd(), "etr_profile")
        browser = p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False,
            accept_downloads=True
        )

        page = browser.pages[0] if browser.pages else browser.new_page()

        print("🌐 Navigating to ETR projections page...")
        page.goto("https://establishtherun.com/fantasy-point-projections/")
        time.sleep(2)

        print("🟢 Clicking FD Main Slate tab...")
        page.get_by_role("link", name="FD Main Slate").click()
        time.sleep(1)

        print("📥 Clicking Download CSV...")
        with page.expect_download() as download_info:
            page.get_by_text("Download CSV").click()
        download = download_info.value

        print(f"💾 Saving to {download_path}...")
        download.save_as(download_path)

        print("✅ Download complete.")
        browser.close()

download_etr_csv()

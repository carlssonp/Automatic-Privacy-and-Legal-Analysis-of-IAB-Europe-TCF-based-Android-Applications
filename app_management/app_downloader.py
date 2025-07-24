from appium import webdriver
from appium.options.android import (
    UiAutomator2Options,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import subprocess
import time
import signal
import sys
from os import path

file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)
sys.path.append(f"{dir_path}\\auxiliary")
sys.path.append(f"{dir_path}\\dynamic_analysis")
from dynamic_util import check_appium_status, download_app, extract_install_amt
import global_util

apps, status, countries, tcf_version, dates = [], [], [], [], []
app_indices = set()
emu = "emulator-5554"
csv = "app_status.csv"


emulators = {"1": "emulator-5554", "2": "emulator-5556", "3": "emulator-5558"}
header_args = [
    "App package",
    "Status",
    "Publishing country",
    "TCF version",
    "Date downloaded",
]
appium_server_url = "http://localhost:4723/wd/hub"


def on_interrupt(signal, frame):
    if apps and status and countries and tcf_version and dates:
        global_util.overwrite_csv(header_args, [apps, status, countries, tcf_version, dates], csv)


def boot_playstore():
    capabilities = dict(
        platformName="Android",
        platformVersion="15",
        deviceName="emulator-5554",
        automationName="UIAutomator2",
        appPackage="com.android.vending",
        appActivity="com.google.android.finsky.activities.MainActivity",
        avd="android_device",
        autoGrantPermissions="true",
    )
    try:
        driver = webdriver.Remote(
            appium_server_url,
            options=UiAutomator2Options().load_capabilities(capabilities),
        )
        time.sleep(4)
        return driver
    except Exception:
        print("Could not reboot Playstore, quitting..")
        global_util.overwrite_csv(header_args, [apps, status, countries, tcf_version, dates], csv)


def playstore_authentication(driver) -> bool:
    print("running auth")
    try:
        WebDriverWait(driver, 5).until(
            expected_conditions.presence_of_element_located(
                (By.XPATH, f"//android.widget.Button[contains(@text, 'Try again')] | //android.widget.TextView[contains(@text, 'Try again')]")
            )
        )
        return True
    except:
        pass
    print("found no button")
    return False


def main(app_amt: int, emu: str = "emulator-5554", csv: str = "app_status.csv", stop_code_execution: bool = True):
    signal.signal(signal.SIGINT, on_interrupt)

    global_util.fetch_scraped_apps(header_args, csv)

    global_util.read_csv(header_args, csv, [apps, status, countries, tcf_version, dates], "Scraped", app_indices)

    pre_amt = extract_install_amt()
    print(f"initial app amt: {str(pre_amt)}")

    if not check_appium_status():
        print("Appium could not boot correctly, quitting")
        quit()

    ctr = 0
    driver = boot_playstore()
    reset_playstore = 0
    for index, app_package in enumerate(apps):
        if ctr >= app_amt:
            break
        if index not in app_indices:
            continue
        if reset_playstore <= -3:
            print("Playstore needed authentication, restarting phone")
            subprocess.run('adb shell su -c "pm clear com.android.vending"', stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run('adb shell su -c "pm disable com.android.vending"', stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            subprocess.run('adb shell su -c "pm enable com.android.vending"', stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
            global_util.kill_emu()
            reset_playstore = 0
        if not global_util.boot_emu():
            global_util.overwrite_csv(header_args, [apps, status, countries, tcf_version, dates], csv)
        app_package = app_package.strip()  # Removes "\n" at end
        pkg_output = subprocess.run(
            f'adb -s {emu} shell su -c "pm list packages {app_package}"',
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.strip()
        if len(pkg_output) > 0:
            print(f"{app_package} was already downloaded.")
            status[index] = "Downloaded"
            continue
        if (ctr + 1) % 11 == 0:
            print(f"App-num: {str(ctr)}")
            driver = boot_playstore()  # PlayStore "crashes" sometimes, requiring a manual click, reset after every app to negate this
        if download_app(pre_amt, app_package, driver):
            pre_amt = extract_install_amt()
            status[index] = "Downloaded"
            reset_playstore = 0
        else:
            if playstore_authentication(driver):
                reset_playstore -= 1
            status[index] = "Cannot download"
        ctr += 1

    global_util.overwrite_csv(header_args, [apps, status, countries, tcf_version, dates], csv, stop_code_execution)


if __name__ == "__main__":
    app_amt = int(input("Select app amount to be downloaded: "))  # Set amount of apps to download
    multi_emu = input("Are you running multiple emulators (N/y)? ")
    if multi_emu.lower() == "y":
        print("This functionality is under construction, quitting..")
        quit()
        emu_int = input("Which emulator is running? ")
        if emu_int in emulators:
            emu = emulators[emu_int]
            csv = f"app_status_{emu_int}.csv"
        else:
            print("Requested emulator does not exist (expect format like: 1/2/3), quitting ")
            quit()
    main(app_amt, emu, csv)

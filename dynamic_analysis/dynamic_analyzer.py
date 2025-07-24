from appium import webdriver
from appium.options.android import (
    UiAutomator2Options,
)
from selenium.webdriver.support.ui import (
    WebDriverWait,
)
from selenium.webdriver.support import (
    expected_conditions,
)
from selenium.webdriver.common.by import (
    By,
)
from selenium.common.exceptions import WebDriverException
import time
import subprocess
import signal
import os
import easyocr
import sys
from os import path
import json

file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)
sys.path.append(f"{dir_path}\\auxiliary")
import global_util

app_packages = []
cmp_ids = []
m_activities = []
purpose_amount = []
purpose_res = []
dynamic_csv = ""

header_args = [
    "App package",
    "SdkId",
    "MainActivity",
    "Purpose Amount",
    "Found Purposes",
]
appium_server_url = "http://localhost:4723/wd/hub"


def update_traffic_json(analysis_type: str, app_package: str):
    json_data = {"analysis_type": f"{analysis_type}", "app_package": f"{app_package}"}
    print("updating json file")
    print(json_data)
    with open(f"{dir_path}\\traffic_analysis\\mitm_inputs.json", "w") as file:
        json.dump(json_data, file)


def check_for_cookie_paywall(driver, reader, package: str, app_activity: str):
    if os.path.exists(f"{dir_path}/screenshots/{package}.png"):
        os.remove(f"{dir_path}/screenshots/{package}.png")
    if os.path.exists(f"{dir_path}/screenshots_to_remove/{package}.png"):
        os.remove(f"{dir_path}/screenshots_to_remove/{package}.png")
    dynamic_util.remove_top_activity(
        driver,
        package,
        app_activity,
    )
    paywall_sources = [
        "subscribe per month",
        "sek/month",
        "usd/month",
        "eur/month",
        "sek per month",
        "usd per month",
        "eur per month",
        "use with tracking",
        "use without tracking",
        "use with personalised advertising",
        "use without personalised advertising",
        "pay to remove ads",
        "ad-free subscription",
        "subscribe to remove ads",
    ]
    subprocess.run(f'adb shell su -c "screencap -p sdcard/screenshots/{package}.png"')
    subprocess.run(f"adb pull sdcard/screenshots/{package}.png {dir_path}/screenshots/{package}.png")
    subprocess.run(f'adb shell su -c "rm sdcard/screenshots/{package}.png"')

    image_text = reader.readtext(f"{dir_path}/screenshots/{package}.png")
    contenders = [
        contender.strip().lower()
        for (
            _,
            contender,
            _,
        ) in image_text
    ]
    if not contenders:
        return
    best_contender_index = dynamic_util.sentence_similarity(paywall_sources, contenders)
    if best_contender_index == -1:
        os.rename(
            f"{dir_path}/screenshots/{package}.png",
            f"{dir_path}/screenshots_to_remove/{package}.png",
        )
    return


# When interrupting the code, this runs
def on_interrupt(signal, frame):
    if app_packages and cmp_ids and m_activities and purpose_amount and purpose_res:
        global_util.overwrite_csv(
            header_args,
            [
                app_packages,
                cmp_ids,
                m_activities,
                purpose_amount,
                purpose_res,
            ],
            dynamic_csv,
        )


def analysis(driver, analysis_type, package, cmp_id, app_activity, traffic_analysis: bool = False) -> bool:
    time.sleep(3)
    dynamic_util.remove_top_activity(driver, package, app_activity)
    match analysis_type:
        case "LI":
            res = analysis_LI(driver, package, cmp_id, app_activity, analysis_type, traffic_analysis)
        case "Nothing":
            res = analysis_nothing(driver, package, cmp_id, app_activity, analysis_type, traffic_analysis)
        case "All":
            res = analysis_all(driver, package, cmp_id, app_activity, analysis_type, traffic_analysis)
    return res


def analysis_all(driver, package, cmp_id, app_activity, analysis_type, traffic_analysis) -> bool:
    match cmp_id:
        case "28":
            try:
                if not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.Button",
                    "text",
                    [
                        "accept",
                        "allow",
                        "godkänner",
                    ],
                    package,
                    analysis_type,
                    traffic_analysis,
                ):
                    return False
            except Exception as e:
                if dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                ):
                    try:
                        if not dynamic_util.find_elem_click(
                            driver,
                            "//android.widget.Button",
                            "text",
                            [
                                "accept",
                                "allow",
                                "godkänner",
                            ],
                            package,
                            analysis_type,
                            traffic_analysis,
                        ):
                            return False
                    except Exception as e:
                        return False
                else:
                    return False
            return True
        case "350":  # Never seen pop-ups on 350, therefore no handling of it necessary.
            # No need for sentence similarity, always identical dialogs.
            try:
                accept_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            "//android.widget.Button[contains(@text, 'Accept')]",
                        )
                    )
                )
                accept_button.click()
                accept_button = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            "//android.widget.Button[contains(@text, 'Accept')]",
                        )
                    )
                )
                if traffic_analysis:
                    update_traffic_json(analysis_type, package)
                accept_button.click()
                return True
            except Exception as e:
                return False
        case "7":
            try:
                if not dynamic_util.find_elem_click(
                    driver, "//android.widget.Button", "text", ["agree & close"], package, analysis_type, traffic_analysis
                ):
                    return False
            except Exception as e:
                if dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                ):
                    try:
                        if not dynamic_util.find_elem_click(
                            driver, "//android.widget.Button", "text", ["agree & close"], package, analysis_type, traffic_analysis
                        ):
                            return False
                    except Exception as e:
                        return False
                else:
                    return False
            return True
        case "300":
            try:
                if not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.Button",
                    "text",
                    [
                        "consent",
                        "i agree",
                        "allow",
                        "ok",
                        "got it",
                        "i understand",
                        "agree",
                        "continue",
                        "accept",
                    ],
                    package,
                    analysis_type,
                    traffic_analysis,
                ):
                    return False
            except Exception as e:
                if dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                ):
                    try:
                        if not dynamic_util.find_elem_click(
                            driver,
                            "//android.widget.Button",
                            "text",
                            [
                                "consent",
                                "i agree",
                                "allow",
                                "ok",
                                "got it",
                                "i understand",
                                "agree",
                                "continue",
                                "accept",
                            ],
                                package,
                                analysis_type,
                                traffic_analysis,
                        ):
                            return False
                    except Exception as e:
                        return False
                else:
                    return False
            return True
        case "348":  # No need for sentence similarity, consent dialogs are always identical
            try:
                ok_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "OK")]',
                        )
                    )
                )
                if driver.orientation == "LANDSCAPE":
                    driver.tap([(2635, 650)], 0)
                    driver.tap([(2635, 650)], 0)
                    driver.tap([(2635, 650)], 0)
                else:
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                ok_button.click()
                accept_button = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "ACCEPT")]',
                        )
                    )
                )
                if traffic_analysis:
                    update_traffic_json(analysis_type, package)
                accept_button.click()
                return True
            except Exception as e:
                return False
        case "5":
            try:
                if not dynamic_util.find_elem_click(driver, "//android.widget.TextView", "text", ["accept all"], package, analysis_type, traffic_analysis):
                    return False
            except Exception as e:
                if dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                ):
                    try:
                        if not dynamic_util.find_elem_click(
                            driver, "//android.widget.TextView", "text", ["accept all"], package, analysis_type, traffic_analysis
                        ):
                            return False
                    except Exception as e:
                        return False
                else:
                    return False
            return True
        case _:
            print(f"CMP: {cmp_id} not handled.")
            return False


def analysis_nothing(driver, package, cmp_id, app_activity, analysis_type, traffic_analysis) -> bool:
    match cmp_id:
        case "28":
            try:
                if not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.Button",
                    "text",
                    [
                        "reject",
                        "decline",
                        "avvisa",
                    ],
                    package,
                    analysis_type,
                    traffic_analysis,
                ):
                    return False
                return True
            except Exception as e:
                # Found no reject-button, cannot handle consent dialog
                return False
        case "350":  # No need for sentence similarity, all apps are identical from Easybrain
            windowSize = driver.get_window_size()
            legitimateInterests = set()
            partner_view_found = False

            try:
                accept_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            "//android.widget.Button[contains(@text, 'Accept')]",
                        )
                    )
                )
                accept_button.click()
                LI_view = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "legitimate interest")]',
                        )
                    )
                )
            except Exception as e:
                return False

            view_pos = LI_view.get_attribute("bounds")
            posX = int(view_pos[view_pos.rfind("[") + 1 : view_pos.rfind(",")])
            posY = int(view_pos[view_pos.rfind(",") + 1 : view_pos.rfind("]")]) - 100
            LI_pressed = False
            for j in range(10):
                driver.tap(
                    [
                        (
                            posX / 2,
                            posY - 50 * j,
                        )
                    ],
                    0,
                )
                try:
                    WebDriverWait(driver, 0.1).until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                '//android.widget.TextView[contains(@text, "Consent to All")]',
                            )
                        )
                    )
                    LI_pressed = True
                    break
                except Exception as e:
                    pass
            if not LI_pressed:
                return False

            try:
                crossButtons = WebDriverWait(driver, 3).until(
                    expected_conditions.presence_of_all_elements_located(
                        (
                            By.XPATH,
                            "//android.widget.ImageButton",
                        )
                    )
                )
                acceptButtonPos = (
                    WebDriverWait(driver, 3)
                    .until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                '//android.widget.Button[contains(@text, "Accept")]',
                            )
                        )
                    )
                    .get_attribute("bounds")
                )
            except Exception as e:
                return False

            crossButtonPos = "[0,250]"
            for button in crossButtons:
                if button.id == "00000000-0000-01e3-ffff-ffff0000002d":
                    crossButtonPos = button.get_attribute("bounds")
                    break

            xStart = xEnd = windowSize["width"] // 2

            yEnd = yStartRange = int(crossButtonPos[crossButtonPos.rfind(",") + 1 : crossButtonPos.rfind("]")]) + 25
            yStart = yEndRange = int(acceptButtonPos[acceptButtonPos.find(",") + 1 : acceptButtonPos.find("]")]) - 60
            yEnd += 75
            yStart -= 75

            noButtonsFound = 0
            while True:
                if noButtonsFound >= 3:  # Scrolling without finding buttons, quitting
                    return False

                if partner_view_found:  # If we scrolled to bottom, store results and quit
                    try:
                        confirm_button = WebDriverWait(driver, 1).until(
                            expected_conditions.presence_of_element_located(
                                (
                                    By.XPATH,
                                    "//android.widget.Button[(@text='Confirm Choices')]",
                                )
                            )
                        )
                        if traffic_analysis:
                            update_traffic_json(analysis_type, package)
                        confirm_button.click()
                        return True
                    except Exception as e:
                        return False

                try:  # Finding LI-views and pressing their related widget-buttons.
                    LI_buttons = WebDriverWait(driver, 1).until(
                        expected_conditions.presence_of_all_elements_located(
                            (
                                By.XPATH,
                                "//android.widget.TextView[contains(@text, 'Legitimate interest')]",
                            )
                        )
                    )
                    for button in LI_buttons:
                        pos = button.get_attribute("bounds")
                        tPos = int(pos[pos.find(",") + 1 : pos.find("]")])
                        bPos = int(pos[pos.rfind(",") + 1 : pos.rfind("]")])
                        mPos = (tPos + bPos) / 2
                        if mPos <= yEndRange:
                            noButtonsFound = 0
                            elementId = button.id
                            if elementId not in legitimateInterests:
                                legitimateInterests.add(elementId)
                                driver.tap(
                                    [
                                        (
                                            1100,
                                            mPos,
                                        )
                                    ],
                                    0,
                                )
                except Exception as e:
                    noButtonsFound += 1

                try:  # If partner_view is found, then we're at bottom of app.
                    partner_view = WebDriverWait(driver, 0.3).until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                "//android.widget.TextView[(@text='View Partners')]",
                            )
                        )
                    )
                    partner_view_found = True
                    print("Found partner-button")
                except Exception as e:
                    pass
                try:
                    driver.swipe(
                        xStart,
                        yStart,
                        xEnd,
                        yEnd,
                        1000,
                    )
                except Exception as e:
                    print("Got error while scrolling? Breaking.")
                    return False

        case "7":
            try:
                if (
                    not dynamic_util.find_elem_click(
                        driver,
                        "//android.widget.Button",
                        "text",
                        ["learn more"],
                    )
                    or not dynamic_util.find_elem_click(
                        driver,
                        "//android.widget.Switch",
                        "content-desc",
                        ["agree to all"],
                    )
                    or not dynamic_util.find_elem_click(
                        driver,
                        "//android.widget.Switch",
                        "content-desc",
                        ["agree to all"],
                    )
                    or not dynamic_util.find_elem_click(driver, "//android.widget.Button", "text", ["save"], package, analysis_type, traffic_analysis)
                ):

                    return False
                return True
            except Exception as e:
                return False
        case "300":
            windowSize = driver.get_window_size()
            # Find manage options button of consent dialog
            try:
                if not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.Button",
                    "text",
                    ["manage", "details", "options", "see more", "more", "管理选项", "manage options", "manage settings"],
                ):
                    return False
            except Exception as e:
                return False
            try:
                arrowButtonPos = (
                    WebDriverWait(driver, 20)
                    .until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                '//android.widget.Button[@text="Back"]',
                            )
                        )
                    )
                    .get_attribute("bounds")
                )
                confirmButtonPos = dynamic_util.find_elem(
                    driver,
                    "//android.widget.Button",
                    "text",
                    ["confirm choices", "confirm", "consent", "accept"],
                ).get_attribute("bounds")
                if not confirmButtonPos:
                    return False
            except Exception as e:
                return False

            if driver.orientation == "LANDSCAPE":
                xStart = xEnd = windowSize["width"] // 2
                yStart = (windowSize["height"] // 2) + 100
                yEnd = yStartRange = int(arrowButtonPos[arrowButtonPos.rfind(",") + 1 : arrowButtonPos.rfind("]")])
                yStart = yEndRange = int(confirmButtonPos[confirmButtonPos.find(",") + 1 : confirmButtonPos.find("]")]) - 90
                yEnd += 65
                yStart -= 10
            else:
                xStart = xEnd = windowSize["width"] // 2
                yEnd = yStartRange = int(arrowButtonPos[arrowButtonPos.rfind(",") + 1 : arrowButtonPos.rfind("]")])
                yStart = yEndRange = int(confirmButtonPos[confirmButtonPos.find(",") + 1 : confirmButtonPos.find("]")]) - 90
                yEnd += 100  # For scrolling safety
                yStart -= 100

            # Scroll through consent dialog and decline all legitimate interests
            pref_button_found = False
            legitimateInterests = set()  # To never press same button twice, the text of button is stored in a set.
            noButtonsFound = 0
            noButton = False
            while True:
                try:
                    toggle_buttons = WebDriverWait(driver, 1).until(
                        expected_conditions.presence_of_all_elements_located(
                            (
                                By.XPATH,
                                '//android.widget.ToggleButton | //android.widget.Button[@text="Vendor preferences"]',
                            )
                        )
                    )
                    noButtonsFound = 0
                except Exception as e:
                    noButtonsFound -= 1
                    if dynamic_util.remove_top_activity(
                        driver,
                        package,
                        app_activity,
                        False,
                    ):
                        continue
                    driver.swipe(
                        xStart,
                        yStart,
                        xEnd,
                        yEnd,
                        1000,
                    )
                    if noButtonsFound <= -15:
                        return False
                    continue

                # At bottom there will be a "vendor preferences"-button, quit once this is seen
                try:
                    pref_button = WebDriverWait(driver, 0.3).until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                '//android.widget.Button[@text="Vendor preferences"]',
                            )
                        )
                    )
                    pref_button_found = True
                    print("Vendor preferences button found, will quit")
                except Exception as e:
                    pass

                for toggle_button in toggle_buttons:
                    try:
                        buttonPos = toggle_button.get_attribute("bounds")
                        bPos = int(buttonPos[buttonPos.rfind(",") + 1 : buttonPos.rfind("]")])
                        if bPos >= yStartRange and bPos <= yEndRange:
                            buttonText = toggle_button.get_attribute("text")
                            if "Legitimate interest" in buttonText and buttonText not in legitimateInterests:
                                toggle_button.click()
                                legitimateInterests.add(buttonText)
                                continue
                            else:
                                continue
                    except Exception as e:  # Consent dialog has most likely pre-emptively closed.
                        print("Tried accessing non-existent button.")
                        break

                if pref_button_found:
                    if not dynamic_util.find_elem_click(
                        driver,
                        "//android.widget.Button",
                        "text",
                        ["confirm choices", "confirm", "consent", "accept"],
                        package,
                        analysis_type,
                        traffic_analysis,
                    ):
                        return False
                    break

                try:
                    driver.swipe(
                        xStart,
                        yStart,
                        xEnd,
                        yEnd,
                        1000,
                    )
                except Exception as e:
                    break
            if noButton:
                return False
            if len(legitimateInterests) == 0:
                return False
            if len(legitimateInterests) > 0:
                return True
        case "348":  # Outfit7 are always identical, no need for sentence similarity
            windowSize = driver.get_window_size()
            try:
                ok_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "OK")]',
                        )
                    )
                )
                if driver.orientation == "LANDSCAPE":
                    driver.tap([(2635, 650)], 0)
                    driver.tap([(2635, 650)], 0)
                    driver.tap([(2635, 650)], 0)
                else:
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
            except Exception as e:
                print("Could not find OK-button, breaking")
                return False
            ok_button = WebDriverWait(driver, 20).until(
                expected_conditions.presence_of_element_located(
                    (
                        By.XPATH,
                        '//android.widget.TextView[contains(@text, "OK")]',
                    )
                )
            )
            ok_button.click()
            LI_button = WebDriverWait(driver, 20).until(
                expected_conditions.presence_of_element_located(
                    (
                        By.XPATH,
                        '//android.widget.TextView[contains(@text, "Legitimate Interest")]',
                    )
                )
            )
            LI_button.click()
            reject_button = WebDriverWait(driver, 20).until(
                expected_conditions.presence_of_element_located(
                    (
                        By.XPATH,
                        '//android.widget.TextView[contains(@text, "REJECT ALL")]',
                    )
                )
            )
            if traffic_analysis:
                update_traffic_json(analysis_type, package)
            reject_button.click()
            return True
        case "5":
            res = False
            windowSize = driver.get_window_size()
            try:
                if not dynamic_util.find_elem_click(driver, "//android.widget.TextView", "text", ["manage", "manage options", "manage settings"]):
                    if dynamic_util.find_elem_click(
                        driver, "//android.widget.TextView", "text", ["deny all", "deny"], package, analysis_type, traffic_analysis
                    ):
                        return True
                    return False
            except Exception as e:
                dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                )
                print("Could not find Manage Settings, trying other case...")
                try:
                    if not dynamic_util.find_elem_click(
                        driver,
                        "//android.widget.TextView",
                        "text",
                        ["manage", "manage options", "manage settings"],
                    ):
                        return False
                    time.sleep(2)
                except Exception as e:
                    return False
            tos_found = False
            noButtonsFound = 0
            legitimateInterests = 0
            try:
                if dynamic_util.find_elem_click(driver, "//android.widget.TextView", "text", ["deny all"], package, analysis_type, traffic_analysis):
                    return True
                else:
                    confirmButtonPos = dynamic_util.find_elem(
                        driver,
                        "//android.widget.TextView",
                        "text",
                        ["confirm", "accept"],
                    ).get_attribute("bounds")
            except Exception:
                return False
            if driver.orientation == "LANDSCAPE":
                xStart = xEnd = windowSize["width"] // 2
                yStart = yEndRange = int(confirmButtonPos[confirmButtonPos.find(",") + 1 : confirmButtonPos.find("]")]) - 75
                yEnd = yStartRange = 300
                yEnd += 50
                yStart -= 75
            else:
                xStart = xEnd = windowSize["width"] // 2
                yStart = yEndRange = int(confirmButtonPos[confirmButtonPos.find(",") + 1 : confirmButtonPos.find("]")]) - 50
                yEnd = yStartRange = 700
                yEnd += 100
                yStart -= 100
            while True:
                try:
                    toggle_buttons = WebDriverWait(driver, 1).until(
                        expected_conditions.presence_of_all_elements_located(
                            (
                                By.CLASS_NAME,
                                "android.widget.Switch",
                            )
                        )
                    )
                    noButtonsFound = 0
                except Exception as e:
                    if dynamic_util.remove_top_activity(driver, package, app_activity, False):
                        continue
                    noButtonsFound -= 1
                    driver.swipe(
                        xStart,
                        yStart,
                        xEnd,
                        yEnd,
                        1000,
                    )
                    if noButtonsFound <= -5:
                        break
                    continue

                try:
                    WebDriverWait(driver, 0.1).until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                '//android.widget.TextView[@text="Non-IAB Purposes"]',
                            )
                        )
                    )
                    tos_found = True
                except Exception as e:
                    pass

                for toggle_button in toggle_buttons:
                    try:
                        buttonPos = toggle_button.get_attribute("bounds")
                        buttonStartPos = int(buttonPos[buttonPos.find(",") + 1 : buttonPos.find("]")])
                        buttonEndPos = int(buttonPos[buttonPos.rfind(",") + 1 : buttonPos.rfind("]")])
                    except Exception as e:  # Consent dialog has most likely pre-emptively closed.
                        break

                    if (buttonStartPos >= yStartRange and buttonStartPos <= yEndRange) or (buttonEndPos >= yStartRange and buttonEndPos <= yEndRange):
                        buttonText = toggle_button.get_attribute("content-desc")
                        buttonStatus = toggle_button.get_attribute("checked")
                        if "Legitimate Interest" in buttonText and buttonStatus == "true":
                            toggle_button.click()
                            legitimateInterests += 1
                            continue
                    else:
                        continue
                if tos_found:
                    if not dynamic_util.find_elem_click(
                        driver,
                        "//android.widget.TextView",
                        "text",
                        [
                            "save options",
                            "save settings",
                        ],
                        package,
                        analysis_type,
                        traffic_analysis,
                    ):
                        return False
                    res = True
                    break

                try:
                    driver.swipe(
                        xStart,
                        yStart,
                        xEnd,
                        yEnd,
                        1000,
                    )
                except Exception as e:
                    break
            return res
        case _:
            print(f"CMP: {cmp_id} not handled.")
            return False


def analysis_LI(driver, package, cmp_id, app_activity, analysis_type, traffic_analysis) -> bool:
    match cmp_id:
        case "28":
            if not dynamic_util.find_elem(
                driver,
                "//android.widget.Button",
                "text",
                [
                    "accept",
                    "allow",
                    "godkänner",
                    "reject",
                    "decline",
                    "avvisa",
                ],
            ):
                return False
            return True

        case "350":  # Press accept and then confirm choices
            # No need for sentence similarity, always identical dialogs.
            try:
                accept_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            "//android.widget.Button[contains(@text, 'Accept')]",
                        )
                    )
                )
                accept_button.click()
                LI_view = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "legitimate interest")]',
                        )
                    )
                )
            except Exception as e:
                return False

            view_pos = LI_view.get_attribute("bounds")
            posX = int(view_pos[view_pos.rfind("[") + 1 : view_pos.rfind(",")])
            posY = int(view_pos[view_pos.rfind(",") + 1 : view_pos.rfind("]")]) - 100
            LI_pressed = False
            for j in range(10):
                driver.tap(
                    [
                        (
                            posX / 2,
                            posY - 50 * j,
                        )
                    ],
                    0,
                )
                try:
                    WebDriverWait(driver, 1).until(
                        expected_conditions.presence_of_element_located(
                            (
                                By.XPATH,
                                '//android.widget.TextView[contains(@text, "Consent to All")]',
                            )
                        )
                    )
                    LI_pressed = True
                    break
                except Exception as e:
                    pass
            if not LI_pressed:
                return False
            try:
                confirm_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            "//android.widget.Button[contains(@text, 'Confirm Choices')]",
                        )
                    )
                )
                if traffic_analysis:
                    update_traffic_json(analysis_type, package)
                confirm_button.click()
                return True
            except Exception as e:
                return False
        case "7":  # CMP 7 stores LI without needing an interaction
            if not dynamic_util.find_elem(
                driver,
                "//android.widget.Button",
                "text",
                ["learn more"],
            ):
                return False
            return True

        case "300":  # Manage options and then confirm choices
            try:
                if not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.Button",
                    "text",
                    ["manage", "details", "options", "see more", "more", "管理选项", "manage options", "manage settings"],
                ) or not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.Button",
                    "text",
                    [
                        "confirm",
                        "confirm choices",
                    ],
                    package,
                    analysis_type,
                    traffic_analysis,
                ):
                    return False
                else:
                    return True
            except Exception as e:
                if dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                ):
                    try:
                        if not dynamic_util.find_elem_click(
                            driver,
                            "//android.widget.Button",
                            "text",
                            ["manage", "details", "options", "see more", "more", "管理选项", "manage options", "manage settings"],
                        ) or not dynamic_util.find_elem_click(
                            driver,
                            "//android.widget.Button",
                            "text",
                            [
                                "confirm",
                                "confirm choices",
                            ],
                            package,
                            analysis_type,
                            traffic_analysis,
                        ):
                            return False
                    except Exception as e:
                        return False
                else:
                    return False
                return True

        case "348":  # "Manage", then press any square once and then save settings
            try:
                ok_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "OK")]',
                        )
                    )
                )
                if driver.orientation == "LANDSCAPE":
                    driver.tap([(2635, 650)], 0)
                    driver.tap([(2635, 650)], 0)
                    driver.tap([(2635, 650)], 0)
                else:
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                    driver.tap(
                        [(1150, 1500)],
                        0,
                    )
                ok_button = WebDriverWait(driver, 20).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "OK")]',
                        )
                    )
                )
                ok_button.click()
                more_button = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "MORE")]',
                        )
                    )
                )
                more_button.click()
                if driver.orientation == "LANDSCAPE":
                    driver.swipe(
                        1300,
                        1100,
                        1300,
                        100,
                        1000,
                    )
                purpose_box_1 = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "cb_1")]',
                        )
                    )
                )
                purpose_box_1.click()  # Toggle on and off
                purpose_box_1.click()
                save_button = WebDriverWait(driver, 10).until(
                    expected_conditions.presence_of_element_located(
                        (
                            By.XPATH,
                            '//android.widget.TextView[contains(@text, "SAVE")]',
                        )
                    )
                )
                if traffic_analysis:
                    update_traffic_json(analysis_type, package)
                save_button.click()
                return True
            except Exception as e:
                print("Could not find OK-button, breaking")
                return False

        case "5":
            try:
                if not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.TextView",
                    "text",
                    [
                        "manage options",
                        "manage settings",
                    ],
                ) or not dynamic_util.find_elem_click(
                    driver,
                    "//android.widget.TextView",
                    "text",
                    [
                        "save settings",
                        "save options",
                    ],
                    package,
                    analysis_type,
                    traffic_analysis,
                ):
                    return False
            except Exception as e:
                if dynamic_util.remove_top_activity(
                    driver,
                    package,
                    app_activity,
                ):
                    try:
                        if not dynamic_util.find_elem_click(
                            driver,
                            "//android.widget.TextView",
                            "text",
                            [
                                "manage options",
                                "manage settings",
                            ],
                        ) or not dynamic_util.find_elem_click(
                            driver,
                            "//android.widget.TextView",
                            "text",
                            [
                                "save settings",
                                "save options",
                            ],
                            package,
                            analysis_type,
                            traffic_analysis,
                        ):

                            return False
                    except Exception as e:
                        return False
                else:
                    return False
            return True
        case _:
            print(f"CMP: {cmp_id} not handled.")
            return False


def main(app_amt, reset_amt, analysis_type, csv, analyse_paywalls, reader, stop_code_execution: bool = True):
    global dynamic_csv
    global_util.read_csv(header_args, csv, [app_packages, cmp_ids, m_activities, purpose_amount, purpose_res])
    dynamic_csv = csv
    signal.signal(signal.SIGINT, on_interrupt)

    ctr = 0
    analysis_failed = False
    if not global_util.boot_emu():  # Trying to boot emulator
        print("Emulator could not boot correctly, quitting")
        quit()

    if not dynamic_util.check_appium_status():
        print("Appium could not boot correctly, quitting")
        quit()
    app_index = 0
    while app_index < len(app_packages):
        package = app_packages[app_index]
        if ctr >= app_amt:
            break
        if purpose_amount[app_index] != 0 and purpose_amount[app_index] != -1:
            app_index += 1
            continue
        print("Current app: " + str(package) + ", at index: " + str(app_index))

        if not global_util.emu_status():
            global_util.overwrite_csv(
                header_args,
                [
                    app_packages,
                    cmp_ids,
                    m_activities,
                    purpose_amount,
                    purpose_res,
                ],
                csv,
            )

        if ((ctr + 1) % (reset_amt + 1)) == 0:
            print("Rebooting emulator")
            if not global_util.kill_emu() or not global_util.boot_emu() or not dynamic_util.check_appium_status():
                global_util.overwrite_csv(
                    header_args,
                    [
                        app_packages,
                        cmp_ids,
                        m_activities,
                        purpose_amount,
                        purpose_res,
                    ],
                    csv,
                )

        app_activities = m_activities[app_index].split(";")
        for activity_index in range(len(app_activities) - 1, -1, -1):
            capabilities = dict(
                platformName="Android",
                platformVersion="15",
                deviceName="emulator-5554",
                automationName="UIAutomator2",
                appPackage=package,
                appActivity=app_activities[activity_index],
                avd="android_device",
                autoGrantPermissions="true",
            )

            try:
                driver = webdriver.Remote(
                    appium_server_url,
                    options=UiAutomator2Options().load_capabilities(capabilities),
                )
                if purpose_amount[app_index] == -1:
                    print(f"Looking for updates in: {package}")
                    if not dynamic_util.update_app(package, driver):
                        analysis_failed = True
                        break
                global_util.give_perms(package)
                if analysis(
                    driver,
                    analysis_type,
                    package,
                    str(cmp_ids[app_index]),
                    app_activities[activity_index],
                ):
                    purpose_amount[app_index] = 99
                    m_activities[app_index] = app_activities[activity_index]
                    time.sleep(3)  # Give app some time after interaction
                    analysis_failed = False
                    print(f"Successfully interacted with dialog in app: {package}")
                    break
                else:
                    analysis_failed = True
                if analyse_paywalls:
                    time.sleep(2)
                    check_for_cookie_paywall(driver, reader, package, app_activities[activity_index])

            except WebDriverException:
                if activity_index == 0:
                    print(f"No functioning activities for: {package}.")
                    analysis_failed = True
                else:
                    print(f"Could not boot application: {package} with activity: {app_activities[activity_index]}, trying next activity.")
            except Exception:
                print(f"Could not interact with consent dialog of app: {package}, moving on..")
                analysis_failed = True

        if analysis_failed:
            print(f"Failed to interact with consent dialog of: {package}")
            purpose_amount[app_index] -= 1
            analysis_failed = False

        purpose_res[app_index] = "unhandled"
        ctr += 1
        subprocess.run((f"adb shell su -c 'am force-stop {package}'"))

    try:
        driver.quit()
    except Exception as e:
        global_util.overwrite_csv(
            header_args,
            [
                app_packages,
                cmp_ids,
                m_activities,
                purpose_amount,
                purpose_res,
            ],
            csv,
        )

    dynamic_util.terminate_appium()

    global_util.overwrite_csv(
        header_args,
        [
            app_packages,
            cmp_ids,
            m_activities,
            purpose_amount,
            purpose_res,
        ],
        csv,
        stop_code_execution,
    )


if __name__ == "__main__":
    import dynamic_util

    app_amt = int(input("Select amount of apps you want to interact with: "))
    reset_amt = int(input("How many apps do you want to analyze before rebooting the phone: "))
    analysis_input = input("Which type of analysis do you want to run (n/l/a): ")
    analysis_type, csv = "", ""
    match analysis_input:
        case "l":
            analysis_type = "LI"
            csv = "dynamic_LI.csv"
        case "n":
            analysis_type = "Nothing"
            csv = "dynamic_nothing.csv"
        case "a":
            analysis_type = "All"
            csv = "dynamic_all.csv"
        case _:
            print(f"{analysis_input} does not exist, you can only select n/l/a")
            quit()
    analyse_paywalls = False
    reader = ""
    if analysis_type == "LI" or analysis_type == "Nothing":
        paywall_input = input("Do you want to analyse cookie paywalls? (Y/n) ")
        if paywall_input.lower() != "n":
            analyse_paywalls = True
            reader = easyocr.Reader(
                ["en", "de", "sv", "fr", "es"],
                gpu=True,
            )
    main(app_amt, reset_amt, analysis_type, csv, analyse_paywalls, reader)
else:
    import dynamic_analysis.dynamic_util as dynamic_util

from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions
from selenium.webdriver.common.by import By
import time
from sentence_transformers import SentenceTransformer, util
import torch
import subprocess
import requests
import json
from os import path

# Find most similar sentence
device = "cuda" if torch.cuda.is_available() else "cpu"
embedder = SentenceTransformer("paraphrase-multilingual-MiniLM-L12-v2", device=device)
appium_server_url = "http://localhost:4723/wd/hub"


def sentence_similarity(sources: list[str], contenders: list[str]) -> int:
    contender_embeddings = embedder.encode(contenders, convert_to_tensor=True)
    source_embeddings = embedder.encode(sources, convert_to_tensor=True)
    cos_sim = util.cos_sim(contender_embeddings, source_embeddings)
    max_scores = torch.max(cos_sim, dim=1).values
    best_contender_index = torch.argmax(max_scores)
    max_score = max_scores[best_contender_index].item()
    if max_score < 0.7:
        print(f'Best contender with low max_score was: "{contenders[best_contender_index]}" with score: {max_score}')
        return -1
    print(f'Best contender with acceptable max_score was: "{contenders[best_contender_index]}" with score: {max_score}')
    return best_contender_index


# Wait until element of 'elem_attribute' appears, then return all those elements and the attributes
def extract_element_attributes(driver, elem_xpath: str, elem_attribute: str):
    ctr = 0
    elems_seen = 0
    while True:
        elements = WebDriverWait(driver, 20).until(expected_conditions.presence_of_all_elements_located((By.XPATH, elem_xpath)))
        if elems_seen == len(elements) or ctr == 3:
            break
        elems_seen = len(elements)
        time.sleep(7)
        ctr += 1
    element_attributes = []
    elements_to_remove = set()
    for i in range(len(elements)):
        if elements[i].get_attribute(elem_attribute).strip():
            element_attributes.append(elements[i].get_attribute(elem_attribute).lower().strip())
        else:
            elements_to_remove.add(elements[i])
            elements[i].get_attribute(elem_attribute.strip())
    for e in elements_to_remove:
        elements.remove(e)
    return elements, element_attributes


# Find the element with the attribute most related to 'sources' of all elements currently on the phone screen
def find_elem(driver, elem_xpath: str, elem_attribute: str, sources: list[str]):
    elems, elem_attributes = extract_element_attributes(driver, elem_xpath, elem_attribute)
    correct_elem_index = -1
    if elem_attributes:
        correct_elem_index = sentence_similarity(sources, elem_attributes)
    else:
        print("No elements found on screen")
    if correct_elem_index == -1:
        return None
    correct_elem_attribute = elems[correct_elem_index].get_attribute(elem_attribute)
    res_elem = WebDriverWait(driver, 20).until(
        expected_conditions.presence_of_element_located((By.XPATH, f'{elem_xpath}[@{elem_attribute}="{correct_elem_attribute}"]'))
    )
    return res_elem


file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)


def find_elem_click(
    driver, elem_xpath: str, elem_attribute: str, sources: list[str], app_package: str = "", analysis_type: str = "", traffic_analysis: bool = False
):
    clickable_elem = find_elem(driver, elem_xpath, elem_attribute, sources)
    if clickable_elem == None:
        print("Not sure of clickable element")
        return False
    if traffic_analysis:
        json_data = {"analysis_type": f"{analysis_type}", "app_package": f"{app_package}"}
        with open(f"{dir_path}\\traffic_analysis\\mitm_inputs.json", "w") as file:
            json.dump(json_data, file)
        time.sleep(2)
    clickable_elem.click()
    return True


def terminate_appium():
    subprocess.run(["taskkill", "/F", "/IM", "node.exe"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


def boot_appium() -> bool:
    terminate_appium()
    print("Booting Appium server")
    ctr = 0
    subprocess.Popen(
        ["appium", "server", "--address", "localhost", "--port", "4723", "--allow-cors", "--use-drivers", "uiautomator2", "--base-path", "/wd/hub"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        shell=True,
    )
    time.sleep(5)
    while requests.get((f"{appium_server_url}/status")).status_code != 200:
        time.sleep(5)
        if ctr >= 10:
            print("Appium server did not work, quitting")
            terminate_appium()
            return False
        ctr += 1
    return True


def check_appium_status() -> bool:
    try:
        response = requests.get((f"{appium_server_url}/status"))  # Check if server is running
        if response.status_code == 200:
            return True
    except Exception as e:  # Server is not running
        return boot_appium()


def tap_button(button_pos):
    pos_x = int(button_pos[button_pos.rfind("[") + 1 : button_pos.rfind(",")])
    pos_y = int(button_pos[button_pos.rfind(",") + 1 : button_pos.rfind("]")])
    subprocess.run(
        f"adb shell input tap {pos_x} {pos_y}",
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


def appium_playstore(driver, app_package: str, button_text: str) -> bool:

    rebooting_playstore = False
    running_activities = subprocess.run(
        'adb shell "dumpsys activity activities | grep -i mactivitycomponent', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout

    if "com.android.vending" not in running_activities:
        rebooting_playstore = True

    subprocess.run(
        f'adb shell am start -a android.intent.action.VIEW -d "https://play.google.com/store/apps/details?id={app_package}"',
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if rebooting_playstore:
        time.sleep(10)

    try:
        WebDriverWait(driver, 20).until(
            expected_conditions.presence_of_element_located(
                (
                    By.XPATH,
                    f"//android.widget.TextView[contains(@text, 'Update') or contains(@text, 'Install') or contains(@text, 'Uninstall') or contains(@text, 'Play')] | //android.widget.Button[contains(@text, 'Try again')]",
                )
            )
        )
        button = WebDriverWait(driver, 2).until(
            expected_conditions.presence_of_element_located(
                (
                    By.XPATH,
                    f"//android.widget.TextView[contains(@text, '{button_text}')]",
                )
            )
        )
        button.click()
        # tap_button(button.get_attribute("bounds"))
        time.sleep(4)
        if str(driver.current_activity) == "com.google.android.finsky.billing.acquire.SheetUiBuilderHostActivity":
            print("Playstore pop-up")
            time.sleep(3)
            driver.tap([(345, 2700)], 0)  # Non-determinism
            driver.tap([(345, 2700)], 0)
            driver.tap([(345, 2700)], 0)
            print("Playstore pop-up: pressed first button")
            time.sleep(3)
            driver.tap([(345, 2700)], 0)  # Non-determinism
            driver.tap([(345, 2700)], 0)
            driver.tap([(345, 2700)], 0)
            print("Playstore pop-up: pressed second button")
        return True
    except Exception as e:
        print(f"Could not find {button_text}-button for: {app_package}")
        return False


def extract_version_name(app_package: str) -> str:
    return subprocess.run(
        f'adb shell su -c "dumpsys package {app_package} | grep -i versionname', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout.strip()


def extract_install_amt() -> int:  # For app directories, which increase and decrease when downloading/updating apps
    return int(subprocess.run('adb shell su -c "ls data/app | wc -l"', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True).stdout.strip())


def update_app(app_package: str, driver) -> bool:
    pre_install_amt = extract_install_amt()
    pre_version = extract_version_name(app_package)
    if not appium_playstore(driver, app_package, "Update"):
        return False
    post_version = extract_version_name(app_package)
    update_timer = 0
    if extract_install_amt() == pre_install_amt:
        return False
    while post_version == pre_version and update_timer < 20:
        post_version = extract_version_name(app_package)
        update_timer += 1
        time.sleep(2)
    return True


def download_app(pre_amt: int, app_package: str, driver, emu: str = "emulator-5554") -> bool:
    print(f"Downloading: {app_package}")
    if not appium_playstore(driver, app_package, "Install"):
        return False
    time.sleep(4)
    post_amt = extract_install_amt()  # Check if amount of apps have increased on phone
    if post_amt > pre_amt:
        for i in range(70):  # Waiting for app to finish downloading
            pkg_output = subprocess.run(
                f'adb -s {emu} shell su -c "pm list packages {app_package}"',
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ).stdout.strip()
            if len(pkg_output) > 0:
                return True
            time.sleep(2)
            if i == 39:
                return True
    return False


def activity_changed(past_activity: str) -> bool:
    time.sleep(1)
    if (
        past_activity
        != subprocess.run(
            "adb shell su -c \"dumpsys activity activities | grep -i mactivitycomponent | head -n 1 | cut -d '/' -f2\"",
            stderr=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            text=True,
        ).stdout.strip()
    ):
        return True
    return False


def remove_top_activity(
    driver, package: str, mActivity: str, reset_activity: bool = True
) -> bool:  # Removes activities popping up in front of consent dialog, returns true if an activity was interacted with (removed).
    app_and_current_activity = subprocess.run(
        'adb shell "dumpsys activity activities | grep -i mactivitycomponent | head -n 1', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout
    past_package = app_and_current_activity[app_and_current_activity.find("=") + 1 : app_and_current_activity.find("/")]
    past_activity = app_and_current_activity[app_and_current_activity.find("/") + 1 :].strip()
    if past_activity == mActivity:
        reset_activity = False

    if "PhoneNumberHintActivity" in past_activity:
        driver.tap([(650, 1400)], 0)
    elif "AdActivity" in past_activity:
        driver.tap([(1050, 70)], 0)
        if activity_changed(past_activity):
            return True
        driver.tap([(1110, 220)], 0)
        if activity_changed(past_activity):
            return True
        driver.tap([(1210, 300)], 0)
        if activity_changed(past_activity):
            return True
        driver.tap([(300, 2500)], 0)
        if activity_changed(past_activity):
            return True
    elif ".GoogleGameActivity" in past_activity:
        driver.tap([(1110, 220)], 0)
    if reset_activity:
        subprocess.run(
            (f"adb shell am start -n {package}/{mActivity}"),
            shell=True,
            text=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    app_and_current_activity = subprocess.run(
        'adb shell "dumpsys activity activities | grep -i mactivitycomponent | head -n 1', stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout
    current_package = app_and_current_activity[app_and_current_activity.find("=") + 1 : app_and_current_activity.find("/")]
    current_activity = app_and_current_activity[app_and_current_activity.find("/") + 1 :].strip()

    if current_package == past_package and current_activity == past_activity:
        return False

    return True

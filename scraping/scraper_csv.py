from selenium import webdriver
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from time import sleep
from json import load
from pandas import read_csv, DataFrame
from datetime import date
from os import path
import signal

file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)

app_categories = set()
old_apps_set = set()
new_apps_set = set()  # Apps that have been recently added to Play Store
base_driver = "https://play.google.com/store/apps/category/"

app_category_list = []
new_apps_list = []
new_app_names = []
current_date = str(date.today())


def on_interrupt(signal, frame):
    if app_category_list and new_apps_list and new_app_names:
        append_csv()
        quit()


def append_csv():
    res_dict = {
        "App package": new_apps_list,
        "App name": new_app_names,
        "App category": app_category_list,
        "Date scraped": [current_date] * len(new_app_names),
    }

    res_df = DataFrame(res_dict)
    res_df.to_csv(f"{dir_path}/csv-files/scraped_apps.csv", mode="a", header=False, index=False)
    print(f"Scrape finished with {str(len(new_apps_set))} new apps found.")


def main():
    signal.signal(signal.SIGINT, on_interrupt)
    with open(f"{dir_path}/scraping/app_categories.json", "r") as categoryfile:  # Create set of all categories that exist in Play Store.
        data = load(categoryfile)
        for category in data["categories"]:
            cat_name = category["cat_key"]
            app_categories.add(cat_name)

    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument("--headless=new")
    driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)

    dataframe = read_csv(f"{dir_path}/csv-files/scraped_apps.csv", usecols=["App package"], index_col=False)
    for index, row in dataframe.iterrows():
        old_package = row["App package"]
        old_apps_set.add(old_package)

    for category in app_categories:
        category_count = 0
        driver.get(base_driver + category)

        old_height = 0
        new_height = driver.execute_script("return document.body.scrollHeight")

        while True:  # Scroll if possible and press Show More button if exists
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight);")
            sleep(1)
            old_height = new_height
            new_height = driver.execute_script("return document.body.scrollHeight")
            if old_height == new_height:
                try:
                    span_elem = driver.find_element(By.XPATH, "//span[text()='Show More']")
                    span_elem.click()
                except Exception as e:
                    break

        links = driver.find_elements(By.TAG_NAME, "a")

        for link in links:
            href = link.get_attribute("href")
            id_pos = href.find("/store/apps/details?id=")
            if id_pos > -1:
                app_id = href[id_pos + len("/store/apps/details?id=") :]
                if app_id not in old_apps_set and app_id not in new_apps_set:  # If app has not been added in previous sessions, add it now
                    new_apps_set.add(app_id)
                    # Have to find name in different ways depending on the format of the application in the Play Store
                    try:
                        app_name_var = link.find_element(
                            By.XPATH, ".//span[contains(@class, 'sT93pb') or contains(@class, 'fkdIre')]"
                        )  # Class name depends on where the app is found.
                        new_apps_list.append(app_id)
                        new_app_names.append(app_name_var.text)
                        category_count += 1
                    except Exception as e:
                        try:
                            app_name_var = link.find_element(By.XPATH, ".//div[@title]/div")
                            new_apps_list.append(app_id)
                            new_app_names.append(app_name_var.text)
                            category_count += 1
                        except Exception as e:
                            print("Got exception: " + href)

        print(f"At category: {category}, found: {str(len(new_apps_set))} new apps so far")
        app_category_list.extend([category] * category_count)
    driver.quit()

    append_csv()


if __name__ == "__main__":
    main()

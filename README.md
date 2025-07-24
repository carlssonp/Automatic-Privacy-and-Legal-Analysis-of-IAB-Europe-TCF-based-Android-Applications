# Automatic Privacy and Legal Analysis of IAB Europe TCF based Android Applications

This project contains all files neccessary to run the analysis we performed to achieve the results we present in our paper, which can be found at:

## Prerequisites

- Windows OS (Developed and ran on Windows)
- Rooted Android device (We used a Pixel 9 Pro with Android 15.0/API 35, and used Magisk to root the device) which has to be named **android_device** to run the code
- Postgresql
  - User and password of the database connection should be "postgres" to match the settings in the code (can be changed locally) and the database should be called "android_tcf_traffic_analysis"
  - One table called "idle_stage" and one called "active_stage", created with the command: create table table_name (app_package text, request text, url text, pd text, analysis text, date date, status_code numeric, PRIMARY KEY (app_package, request, url, analysis, status_code));
- For pip packages, run: ```pip install -r pip-pre-reqs.txt```
- Environment Variables
  - ANDROID_HOME, linked to where the emulated device's SDK is stored
  - Users\user\AppData\Local\Android\sdk
  - Path variables (Users\user\AppData\Local\Android\sdk\emulator, Users\user\AppData\Local\Android\sdk\platform-tools, Users\user\AppData\Roaming\npm, Program Files\PostgreSQL\16\bin, Program Files\mitmproxy\bin)
- Mitmproxy
  - CA on the device
- Appium & UIAutomator2
- Frida server (version 16.7.19)
- Magisk (on the emulated device)
## Files

*scraper_csv.py* scrapes the playstore for the top applications that are not currently in the *scraped_apps.csv* file

*app_downloader.py* downloads a specified amount of apps from *scraped_apps.csv* and adds them to *app_status.csv*

*app_opener.py* opens a specified amount of apps which have the status "downloaded" in *app_status.csv* to check if they implement the TCF

*dynamic_analyzer.py* runs the chosen version of analysis (Nothing [n], LI Only [l] or Consent and LI [a]) on a specified number of apps from the related dynamic csv

The *main.py* file connects all of the different analyses and lets users run all different components at once. To run *main.py* it is **required** that a snapshot called *clean_snapshot* exists. The included steps are:
 - Scraping
 - Downloading
 - Checking for TCF usage
 - Dynamic analysis (with chosen method)
 - Traffic analysis (uses our active method as it is more exhaustive in finding if **any** data is being transmitted at any point)



### Traffic Analysis files

For the traffic analysis, we had 2 different stages of analyzation. The first stage, which we used most throughout our project for testing, only analyses data which is transmitted while the app is idling after the consent dialog interaction has been interacted with (through *dynamic_analyzer.py*) and the app has relaunched, hence the name *traffic_analysis_stage_idle.py*. The second stage is used to check if any apps transmit data on their first launch or while interacting with their consent dialog. It is therefore named *traffic_analysis_stage_active.py*, as the phone is running the dynamic and traffic analysis simultaneously.




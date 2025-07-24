from auxiliary.global_util import boot_emu, kill_running_apps
import subprocess
import time

snapshot_name = "clean_snapshot"


def main():
    app_status_csv = "app_status.csv"
    emu = "emulator-5554"
    run_scraper = input("Do you want to run the scraper (y/N): ")
    try:
        app_download_amt = int(input("Select app amount to be downloaded (if any): "))  # Set amount of apps to download
        amt_to_check_for_tcf = int(input("Select app amount to be analyzed for TCF-usage (if any): "))
        amt_to_analyze = int(input("Select amount to analyze: "))
        if amt_to_check_for_tcf > 0 or amt_to_analyze > 0:
            amt_before_reboot = int(input("Select amount of apps to be ran continuously before rebooting device (~25): "))
        if amt_to_analyze > 0:
            analysis_type = input("Which type of analysis do you want to run (n/l/a): ").lower()
    except:
        print("Amount has to be a number.")
        quit()
    if run_scraper.lower() == "y" or app_download_amt > 0 or amt_to_check_for_tcf > 0 or amt_to_analyze > 0:
        print("Booting emulator")
        if not boot_emu(emu):
            print("Could not boot emulator, quitting..")
            quit()
        try:
            subprocess.run(
                f"adb emu avd snapshot load {snapshot_name}", stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=80
            )
        except Exception as e:
            print("Failed to load snapshot, quitting \n Exception message follows.. \n")
            print(e)
            quit()
    if run_scraper.lower() == "y":
        from scraping import scraper_csv

        scraper_csv.main()
    if app_download_amt > 0:
        from app_management import app_downloader

        app_downloader.main(app_download_amt, emu, app_status_csv, False)
        time.sleep(5)
        subprocess.run(f'adb shell "am force-stop com.android.vending"', stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
        time.sleep(2)
    if amt_to_check_for_tcf > 0:
        from app_management import app_opener

        time.sleep(5)
        app_opener.main(amt_to_check_for_tcf, amt_before_reboot, app_status_csv, emu, False)
    if amt_to_check_for_tcf > 0 or app_download_amt > 0:
        kill_running_apps()
        time.sleep(8)
        try:
            subprocess.run(
                f"adb emu avd snapshot save {snapshot_name}", stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, timeout=80
            )
        except Exception as e:
            print("Failed to save snapshot... \n MAKE SURE TO SAVE SNAPSHOT MANUALLY BEFORE RUNNING TRAFFIC \n Exception message follows.. \n")
            print(e)
    if amt_to_analyze > 0:
        from traffic_analysis import traffic_analysis_stage_active

        traffic_analysis_stage_active.main(amt_to_analyze, analysis_type, amt_before_reboot)


if __name__ == "__main__":
    main()

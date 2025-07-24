import subprocess
import time
import signal
import sys
from os import path

file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)
sys.path.append(f"{dir_path}\\auxiliary")
import global_util


def on_interrupt(signal, frame):
    if apps and status and countries and tcf_version and dates:
        update_csvs()


def update_csvs(stop_code_execution: bool = True):
    if apps and status and countries and tcf_version and dates:
        global_util.append_csv(
            dynamic_header_args,
            [tcf_apps, cmp_sdk_id_list, m_activity_list, [0] * len(tcf_apps), ["unhandled"] * len(tcf_apps)],
            ["dynamic_nothing.csv", "dynamic_LI.csv", "dynamic_all.csv"],
        )
        global_util.overwrite_csv(status_header_args, [apps, status, countries, tcf_version, dates], csv, stop_code_execution)


emulators = {"1": "emulator-5554", "2": "emulator-5556", "3": "emulator-5558"}
csv = "app_status.csv"
tcf_apps, m_activity_list, cmp_sdk_id_list = [], [], []
apps, status, countries, tcf_version, dates = [], [], [], [], []
app_indices = set()
status_header_args = [
    "App package",
    "Status",
    "Publishing country",
    "TCF version",
    "Date downloaded",
]
dynamic_header_args = ["App package", "SdkId", "MainActivity", "Purpose Amount", "Found Purposes"]


def main(app_amt: int, reboot_amt: int, csv: str = "app_status.csv", emu: str = "emulator-5554", stop_code_execution: bool = True):
    signal.signal(signal.SIGINT, on_interrupt)

    global_util.read_csv(status_header_args, csv, [apps, status, countries, tcf_version, dates], "Downloaded", app_indices)
    app_ctr = 0
    manual_cmp_ids = {"com.easybrain": 350, "com.outfit7": 348, "com.onetrust": 28}

    global_util.kill_running_apps()

    for index, app in enumerate(apps):
        if index not in app_indices:
            continue
        if app_ctr >= app_amt:
            break
        if (app_ctr + 1) % (reboot_amt + 1) == 0 or not global_util.emu_status(emu):
            print("Rebooting")
            if not global_util.kill_emu() or not global_util.boot_emu(emu):
                update_csvs()
        print(f"Running: {app}")
        pkg_exists = subprocess.run(
            f'adb -s {emu} shell su -c "pm list packages {app}"',
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        ).stdout.strip()
        if not (pkg_exists and len(pkg_exists) > 0):  # Check if package exists, if not it has already been removed and we can move on.
            status[index] = "Deleted"
            continue
        subprocess.run(
            f'adb -s {emu} shell "monkey -p {app} 1"',
            stderr=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
        )
        global_util.give_perms(app, emu)
        ctr = 0
        tcf = False
        m_activity = ""
        activity_set = set()
        while True:
            if ctr >= 20 or (ctr >= 10 and not tcf):
                break
            # Collect all activities of app during launch, necessary for dynamic analysis
            m_activity_output = subprocess.run(
                f'adb -s {emu} shell "dumpsys activity activities | grep -i mactivitycomponent"',
                text=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            ).stdout.strip()
            res = m_activity_output.split("\n")
            if not tcf:
                output = subprocess.run(
                    f'adb -s {emu} shell su -c "grep -l IABTCF data/data/{app}/shared_prefs/*.xml | wc -l "',
                    stderr=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    text=True,
                ).stdout
                if output and int(output) == 0:
                    output = subprocess.run(
                        f'adb -s {emu} shell su -c "grep -l -i onetrust data/data/{app}/shared_prefs/*.xml | wc -l "',
                        stderr=subprocess.DEVNULL,
                        stdout=subprocess.PIPE,
                        text=True,
                    ).stdout
                if output and int(output) > 0:
                    status[index] = "Has TCF"
                    tcf = True
            for r in range(len(res)):
                res[r] = res[r].strip()
                if "com.google" in res[r]:
                    continue
                res[r] = res[r][res[r].rfind("/") + 1 :]
                if res[r] not in activity_set and res[r] != ".NexusLauncherActivity":
                    activity_set.add(res[r])
                    if m_activity:
                        m_activity += ";" + res[r]
                    else:
                        m_activity += res[r]
            time.sleep(1)
            ctr += 1
        if not tcf:
            print(f"Tried to delete app: {app}")
            status[index] = "Deleted"
            # If TCF-usage wasn't found, we uninstall the app.
            subprocess.run(
                f"adb -s {emu} uninstall {app}",
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            tcf_apps.append(app)
            # Find which CMP the app uses, necessary for automatic interactions with consent dialogs in dynamic analysis
            cmp = subprocess.run(
                f'adb -s {emu} shell su -c "grep -i cmpsdkid data/data/{app}/shared_prefs/{app}_preferences.xml | cut -d= -f3"',
                stderr=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                text=True,
            ).stdout
            cmp = cmp[cmp.find('"') + 1 : cmp.rfind('"')]
            if not cmp:  # Some apps don't store their CMP-id in shared_prefs instantly and require manual intervention.
                for manualSdk in manual_cmp_ids:
                    if manualSdk in app:
                        cmp = str(manual_cmp_ids[manualSdk])
                        break
                    cmp_output = subprocess.run(
                        f'adb -s {emu} shell su -c "ls data/data/{app}/shared_prefs/ | grep {manualSdk} | wc -l"',
                        stdout=subprocess.PIPE,
                        stderr=subprocess.DEVNULL,
                        text=True,
                    ).stdout
                    if int(cmp_output) > 0:
                        cmp = str(manual_cmp_ids[manualSdk])
                        break
            cmp_sdk_id_list.append(cmp)
            if not m_activity:
                m_activity = "No activity found"
            m_activity_list.append(m_activity)
        global_util.kill_running_apps()
        time.sleep(2)
        app_ctr += 1

    update_csvs(stop_code_execution)


if __name__ == "__main__":
    app_amt = int(input("Select app amount to be checked for the TCF: "))  # Set amount of apps to download
    reboot_amt = int(input("How many apps before reboot? "))
    multi_emu = input("Are you running multiple emulators (N/y)? ")
    csv = "app_status.csv"
    if multi_emu.lower() == "y":
        print("This functionality is under construction, quitting..")
        quit()
        emu_num = input("Which emulator is running? ")
        if emu_num in emulators:
            emu = emulators[emu_num]
            csv = f"app_status_{emu_num}.csv"
        else:
            print("Requested emulator does not exist (expect format like: 1/2/3), quitting..")
            quit()
    main(app_amt, reboot_amt)

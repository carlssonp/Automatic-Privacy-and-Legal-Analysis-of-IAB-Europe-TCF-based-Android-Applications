appium_server_url = "http://localhost:4723/wd/hub"


# Check if Frida-server (f-server) is running and if not, potential to boot.
def on_interrupt(signal, frame):
    subprocess.run(
        'adb shell su -c "settings put global http_proxy :0"',
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    if apps and nothing and li and all:
        overwrite_csvs()


def check_boot_frida() -> bool:
    frida_check_res = subprocess.run(
        'adb shell "ps -A | grep f-server"', stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True
    ).stdout
    if not frida_check_res:
        print("Booting Frida")
        subprocess.Popen(
            "adb shell \"su -c '/data/local/tmp/./f-server'\"", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True
        )
        time.sleep(5)
        return False
    return True


def boot_emu_snapshot(snapshot_name: str, ip_and_port: str) -> bool:
    global_util.kill_emu()
    print("Starting phone")
    sleep_ctr = 0
    proc = subprocess.Popen(
        f"emulator -avd android_device",
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    while True:
        if sleep_ctr == 70:
            print("Could not start emulator, trying coldstart")
            global_util.kill_emu()
            proc.wait()
            proc = subprocess.Popen(
                f"emulator -avd android_device -no-snapshot-load",
                shell=True,
                stdin=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        if sleep_ctr >= 200:
            print("Coldstart failed, quitting")
            return False
        time.sleep(2)
        if global_util.emu_status():
            snapshot_load(snapshot_name, ip_and_port)
            return True
        if (sleep_ctr + 1) % 21 == 0:
            print(f"Have waited {str(sleep_ctr * 2)} seconds trying to reboot emulator")
        sleep_ctr += 1


def continue_or_reboot(snapshot_name: str, ip_and_port: str):
    restart_timer = 0
    while True:
        if (restart_timer + 1) % 6 == 0:
            print(f"Waited {str(2 * restart_timer)} while checking status.")
        if restart_timer >= 35:
            print("Hard crash, rebooting phone")
            if not boot_emu_snapshot(snapshot_name, ip_and_port):
                print("Objection- and mitm-instances have NOT been terminated.")
                overwrite_csvs()
            break
        if global_util.emu_status():
            break
        time.sleep(2)
        restart_timer += 1
    return


def csv_status_update(analyzation: str, index: int, val: int):
    match analyzation:
        case "LI":
            li[index] = val
        case "All":
            all[index] = val
        case _:
            nothing[index] = val


def overwrite_csvs():
    mitm_pid_num = global_util.find_pid("mitm")
    global_util.kill_proc(mitm_pid_num)
    subprocess.run(
        'adb shell su -c "settings put global http_proxy :0"',
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )
    global_util.overwrite_csv(traffic_headers, [apps, nothing, li, all], "traffic.csv", False)
    global_util.overwrite_csv(
        dynamic_headers, [dynamic_apps, dynamic_cmps, dynamic_activities, dynamic_purpose_amounts, dynamic_found_purposes], dynamic_csv
    )


def update_emulator_location():
    if not dynamic_util.check_appium_status():
        print("Appium could not boot, quitting")
        overwrite_csvs()
    location_data = subprocess.run('adb shell su -c "dumpsys location | grep Location"', stdout=subprocess.PIPE, text=True).stdout
    if "57.68" in location_data and "11.97" in location_data:
        return

    capabilities = dict(
        platformName="Android",
        platformVersion="15",
        deviceName="emulator-5554",
        automationName="UIAutomator2",
        appPackage="com.google.android.apps.maps",
        appActivity="com.google.android.maps.MapsActivity",
        avd="android_device",
        autoGrantPermissions="true",
    )

    try:
        driver = webdriver.Remote(
            appium_server_url,
            options=UiAutomator2Options().load_capabilities(capabilities),
        )
        print("Setting location to Chalmers Johanneberg")
        driver.set_location(57.68996954396111, 11.974183155527186, 28)
        location_ctr = 0
        while True:
            running_activities = subprocess.run(
                'adb shell su -c "dumpsys activity activities | grep -i mactivitycomponent"', stdout=subprocess.PIPE, text=True
            ).stdout
            if "com.google.android.apps.maps" not in running_activities:
                print("Google maps crashed, resetting location")
                update_emulator_location()
            location_data = subprocess.run('adb shell su -c "dumpsys location | grep Location"', stdout=subprocess.PIPE, text=True).stdout
            if "57.68" in location_data and "11.97" in location_data:
                print(f"Location was updated to Chalmers Johanneberg after: {str(2*location_ctr)} seconds")
                break
            time.sleep(2)
            location_ctr += 1
    except Exception as e:
        print(e)
        update_emulator_location()
    subprocess.run('adb shell su -c "am force-stop com.google.android.apps.maps"', stdout=subprocess.DEVNULL)


def snapshot_load(snapshot_name, ip_and_port):
    try:
        snp_load = subprocess.run(
            f"adb emu avd snapshot load {snapshot_name}",
            timeout=30,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.PIPE,
            text=True,
        ).stderr
        time.sleep(5)
        subprocess.run(
            f'adb shell su -c "settings put global http_proxy {ip_and_port}"',
            timeout=5,
            shell=True,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        if "error" not in snp_load:
            update_emulator_location()
            return
    except Exception as e:
        pass
    if not boot_emu_snapshot(snapshot_name, ip_and_port):
        print("Failed to boot phone")
        overwrite_csvs()
        # overwrite_csv(apps,nothing,li,all)


def count_ones(purpose: str) -> int:  # Counts amount of 1's in string from grep on either purposelegitimateinterests or purposeconsents
    pAmt = -99  # For the case that no string exists
    if purpose:  # If there is a result from the grep-command
        pAmt = 0  # For the case that the string is empty
        if int(purpose) == 0:
            return 0
        else:
            for c in purpose:
                if c == "1":
                    pAmt += 1
    return pAmt


def all_analyzation(li_purposes: str, consent_purposes: str) -> str:
    li_res = ""
    if li_purposes:
        li_res = disallowed_li(li_purposes)
        if li_res:
            return li_res
    if consent_purposes and int(consent_purposes) > 0:  # or (li_purposes and int(li_purposes) > 0)
        return "Purposes stored correctly"
    return "no active purposes"


def nothing_analyzation(li_purposes: str, consent_purposes: str) -> str:
    li_amt = count_ones(li_purposes)
    consent_amt = count_ones(consent_purposes)
    if li_amt == -99:
        li_amt = 0
    if consent_amt == -99:
        consent_amt = 0
    return f"{str(li_amt)} LI & {str(consent_amt)} consent."


def LI_analyzation(li_purposes: str, consent_purposes: str) -> str:
    if li_purposes:
        li_res = disallowed_li(li_purposes)
        if li_res:
            return li_res
    li_amt = count_ones(li_purposes)
    consent_amt = count_ones(consent_purposes)
    if li_amt == -99 and consent_amt == -99:
        return "no active purposes"
    elif consent_amt == -99:
        consent_amt = 0
    return f"{str(li_amt)} LI & {str(consent_amt)} consent."


def disallowed_li(purposes: str) -> str:
    res = ""
    res_suffix = ""
    if purposes:
        if int(purposes[0]):
            res_suffix += "1,"
        if int(purposes[2]):
            res_suffix += "3,"
        if int(purposes[3]):
            res_suffix += "4,"
        if int(purposes[4]):
            res_suffix += "5,"
        if int(purposes[5]):
            res_suffix += "6,"
        if res_suffix:
            res = f"Disallowed purposes {res_suffix[:-1]} in use"
    return res


def extract_purposes(analyzation: str, app_package: str) -> str:
    li_purposes = subprocess.run(
        f'adb shell su -c "grep -i iabtcf_purposelegitimateinterests data/data/{app_package}/shared_prefs/{app_package}_preferences.xml | cut -c1-150 | head -n 1"',
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout
    consent_purposes = subprocess.run(
        f'adb shell su -c "grep -i iabtcf_purposeconsents data/data/{app_package}/shared_prefs/{app_package}_preferences.xml | cut -c1-150 | head -n 1"',
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
    ).stdout

    if not (li_purposes and consent_purposes):
        return "no active purposes"
    li_purposes = li_purposes[li_purposes.find(">") + 1 : li_purposes.rfind("<")]  # Only look at purpose numbers
    consent_purposes = consent_purposes[consent_purposes.find(">") + 1 : consent_purposes.rfind("<")]  # Only look at purpose numbers
    print(f"Purposes for the package: {app_package} LI: {li_purposes} Consent: {consent_purposes}")

    match analyzation:
        case "All":
            if not consent_purposes:
                return "no active purposes"
            return all_analyzation(li_purposes, consent_purposes)
        case "Nothing":
            return nothing_analyzation(li_purposes, consent_purposes)
        case "LI":
            if not li_purposes:
                return "no active purposes"
            return LI_analyzation(li_purposes, consent_purposes)


def pm_enable_disable(operation: str, package: str):
    subprocess.run(
        f'adb shell su -c "pm {operation} {package}"',
        shell=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def check_for_crash(snapshot_name: str, analyzation: str, app_index: int, val: int, app_package: str, ip_and_port: str) -> bool:
    curr_activity = subprocess.run(
        'adb shell "dumpsys activity activities | grep -i mactivitycomponent="',
        stdin=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    app_running = subprocess.run(
        (f'adb shell "ps -A | grep {app_package}"'), stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True
    ).stdout.strip()
    phone_status = subprocess.run(
        'adb shell "getprop sys.boot_completed"', text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    ).stdout.strip()
    if not "1" in phone_status:  # Phone reboot
        print(f"Soft reboot on: {app_package}")
        return True
    if not app_running or app_package not in curr_activity:
        csv_status_update(analyzation, app_index, val)
        print(f"App: {app_package} crashed")
        if ".NexusLauncherActivity" not in curr_activity:  # Implemented to fix Google white-screen
            snapshot_load(snapshot_name, ip_and_port)
        return True


def crash_handling(snapshot_name: str, analyzation: str, app_index: int, val: int, app_package: str, ip_and_port: str) -> bool:
    if check_for_crash(snapshot_name, analyzation, app_index, val, app_package, ip_and_port):
        csv_status_update(analyzation, app_index, val)
        return True
    return False


def kill_objection():
    obj_pid_num = global_util.find_pid("objection")
    global_util.kill_proc(obj_pid_num)

    obj_pid_cmd = subprocess.run(
        "wmic process where \"name='cmd.exe'\" get ProcessId, CommandLine",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.DEVNULL,
        text=True,
        shell=True,
    ).stdout
    if obj_pid_cmd:
        obj_pid_cmd = obj_pid_cmd[
            obj_pid_cmd.find('disable"') + len('disable"') :
        ].strip()  # objection cmd commandline looks like: objection ... "android sslpinning disable"
        obj_pid_cmd = obj_pid_cmd[: obj_pid_cmd.find(" ")]
        global_util.kill_proc(obj_pid_cmd)


apps, nothing, li, all = [], [], [], []
in_traffic = set()
traffic_headers = ["App package", "Nothing", "LI", "All"]
dynamic_apps, dynamic_cmps, dynamic_activities, dynamic_purpose_amounts, dynamic_found_purposes = [], [], [], [], []
dynamic_indices = {}
dynamic_headers = ["App package", "SdkId", "MainActivity", "Purpose Amount", "Found Purposes"]
dynamic_indices_to_add_to_traffic = set()
dynamic_csv = ""


def main(app_amt: int, interaction_method: str, restart_amt: int):
    global dynamic_csv

    ip = subprocess.run("netsh interface ipv4 show addresses", shell=True, text=True, stdout=subprocess.PIPE).stdout
    ip = ip[ip.find("Ethernet") : ]
    ip = ip[ip.find("DHCP enabled:") :]
    ip = ip[ip.find("Yes") :]
    ip = ip[ip.find("192") : ip.find("Subnet")].strip()
    ip_and_port = ip + ":8080"

    if not (interaction_method == "n" or interaction_method == "l" or interaction_method == "a"):
        print(f"Incorrect interaction method selected: {interaction_method}, quitting ..")
        quit()

    snapshot_name = "clean_snapshot"
    match interaction_method:
        case "l":
            analyzation = "LI"
            dynamic_csv = "dynamic_LI.csv"
        case "a":
            analyzation = "All"
            dynamic_csv = "dynamic_all.csv"
        case "n":
            analyzation = "Nothing"
            dynamic_csv = "dynamic_nothing.csv"
    if not global_util.boot_emu():
        print("Emulator could not boot correctly, quitting")
        quit()

    if not dynamic_util.check_appium_status():
        print("Appium could not boot correctly, quitting")
        quit()

    try:
        trafficFrame = pandas.read_csv(f"{dir_path}/csv-files/traffic.csv", usecols=traffic_headers, index_col=False)
        for index, row in trafficFrame.iterrows():
            in_traffic.add(row["App package"])
            apps.append(row["App package"])
            nothing.append(row["Nothing"])
            li.append(row["LI"])
            all.append(row["All"])

    except Exception as e:
        ans = input("Could not find 'traffic.csv', do you want to create the file (will overwrite if it already exists)? (y/N) ").lower()
        if ans == "y":
            data = {"App package": [], "Nothing": [], "LI": [], "All": []}
            df = pandas.DataFrame(data)
            df.to_csv(f"{dir_path}/csv-files/traffic.csv", mode="w", header=traffic_headers, index=False)
            print("Created traffic.csv, re-run program please.")
            quit()
        else:
            print("Could not find 'traffic.csv', quitting..")
            quit()

    try:
        statusFrame = pandas.read_csv(f"{dir_path}/csv-files/{dynamic_csv}", usecols=dynamic_headers, index_col=False)
        for index, row in statusFrame.iterrows():
            if int(row["Purpose Amount"]) >= 0 and row["App package"] not in in_traffic:
                apps.append(row["App package"])
                nothing.append(0)
                li.append(0)
                all.append(0)
            dynamic_indices_to_add_to_traffic.add(index)
            dynamic_indices[row["App package"]] = index
            dynamic_apps.append(row["App package"])
            dynamic_cmps.append(row["SdkId"])
            dynamic_activities.append(row["MainActivity"])
            dynamic_purpose_amounts.append(row["Purpose Amount"])
            dynamic_found_purposes.append(row["Found Purposes"])
    except Exception as e:
        print(e)
        print(f"Could not find {dynamic_csv}, quitting.")
        quit()

    ctr = 0
    total_sleep_period = 10  # Decides for how long each app is analyzed (2*10 seconds)
    sleep_period = 2
    mitm_status = subprocess.run(
        "tasklist | findstr mitm", shell=True, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    ).stdout
    if not mitm_status:
        mitm_proc_input = f"mitmdump -q -s {dir_path}\\traffic_analysis\\mitm_addon_stage_active.py"
        subprocess.Popen(mitm_proc_input, shell=True, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        print("Booting mitmdump")
    snapshot_load(snapshot_name, ip_and_port)
    signal.signal(signal.SIGINT, on_interrupt)
    # recurring_phone_crash = 0
    val = 0
    app_index = 0
    global_util.kill_running_apps()

    while app_index < len(apps):
        match analyzation:
            case "LI":
                val = 1 + li[app_index]
            case "All":
                val = 1 + all[app_index]
            case _:
                val = 1 + nothing[app_index]

        kill_objection()  # Terminate cmd which booted objection

        analysis_failed = False
        app_package = apps[app_index]
        dynamic_index = dynamic_indices[app_package]
        if val > 3 or dynamic_purpose_amounts[dynamic_index] < -1:
            app_index += 1
            continue
        if ctr >= app_amt:
            print(f"Analyzed {str(ctr)} applications, quitting..")
            break
        if (ctr + 1) % (restart_amt + 1) == 0:
            print("Rebooting phone")
            if not boot_emu_snapshot(snapshot_name, ip_and_port):
                print("Failed to reboot phone")
                overwrite_csvs()
            ctr += 1
            continue
        if not dynamic_util.check_appium_status():
            print("Appium could not boot correctly, quitting")
            overwrite_csvs()

        continue_or_reboot(snapshot_name, ip_and_port)
        if dynamic_purpose_amounts[dynamic_index] == 0 or dynamic_purpose_amounts[dynamic_index] == -1:
            ctr += 1
            cmp_id = str(dynamic_cmps[dynamic_index])
            app_activities = dynamic_activities[dynamic_index].split(";")
            update_emulator_location()  # Makes sure emulator is in Europe
            for activity_index in range(len(app_activities) - 1, -1, -1):
                app_activity = app_activities[activity_index]
                capabilities = dict(
                    platformName="Android",
                    platformVersion="15",
                    deviceName="emulator-5554",
                    automationName="UIAutomator2",
                    appPackage=app_package,
                    appActivity=app_activity,
                    avd="android_device",
                    autoGrantPermissions="true",
                )
                if analysis_failed:
                    break
                continue_or_reboot(snapshot_name, ip_and_port)
                try:
                    if not dynamic_util.check_appium_status():
                        print("Appium could not boot correctly, quitting")
                        overwrite_csvs()
                    driver = webdriver.Remote(
                        appium_server_url,
                        options=UiAutomator2Options().load_capabilities(capabilities),
                    )
                    check_boot_frida()  # Check if Frida is running, else boot
                    # A new minimzed (/min) cmd will be booted, running objection
                    json_dialog_interaction_data = {"analysis_type": "consent dialog interaction", "app_package": f"{app_package}"}
                    with open(f"{dir_path}\\traffic_analysis\\mitm_inputs.json", "w") as file:
                        json.dump(json_dialog_interaction_data, file)
                    subprocess.Popen(
                        [
                            "start",
                            "/min",
                            "cmd.exe",
                            "/k",
                            "objection",
                            "-g",
                            app_package,
                            "explore",
                            "--quiet",
                            "--startup-command",
                            "android sslpinning disable",
                        ],
                        shell=True,
                        stdin=subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        text=True,
                    )
                    time.sleep(3)
                    continue_or_reboot(snapshot_name, ip_and_port)
                    if not dynamic_analyzer.analysis(driver, analyzation, app_package, cmp_id, app_activity, True):
                        print(f"Dynamic analysis failed for app: {app_package}")
                        kill_objection()
                        if not crash_handling(snapshot_name, analyzation, app_index, val, app_package, ip_and_port):
                            dynamic_purpose_amounts[dynamic_index] -= 1
                        else:
                            csv_status_update(analyzation, app_index, val)
                        analysis_failed = True
                        continue
                    dynamic_purpose_amounts[dynamic_index] = 99
                    dynamic_activities[dynamic_index] = app_activity
                    time.sleep(2)  # Allows purposes to be stored correctly in shared_prefs
                    break

                except WebDriverException as e:
                    if activity_index == 0:
                        print(f"No functioning activities for: {app_package}.")
                        dynamic_purpose_amounts[dynamic_index] = -2
                        analysis_failed = True
                    else:
                        print(f"Could not boot application: {app_package} with activity: {app_activity}, trying next activity.")
                except Exception as e:
                    print(e)
                    print(f"Could not interact with consent dialog of app: {app_package}, moving on..")
                    if not crash_handling(snapshot_name, analyzation, app_index, val, app_package, ip_and_port):
                        dynamic_purpose_amounts[dynamic_index] -= 1
                    analysis_failed = True

        if analysis_failed:
            continue

        if dynamic_found_purposes[dynamic_index] == "unhandled" and dynamic_purpose_amounts[dynamic_index] > 0:
            continue_or_reboot(snapshot_name, ip_and_port)
            dynamic_found_purposes[dynamic_index] = extract_purposes(analyzation, app_package)
        if (
            dynamic_found_purposes[dynamic_index] == "no active purposes"
            or (analyzation == "Nothing" and dynamic_found_purposes[dynamic_index] != "0 LI & 0 consent.")
            or (
                (analyzation == "LI" and "0 LI" in dynamic_found_purposes[dynamic_index])
                or (analyzation == "LI" and "0 consent" not in dynamic_found_purposes[dynamic_index])
            )
            or (dynamic_purpose_amounts[dynamic_index] <= 0 and dynamic_purpose_amounts[dynamic_index] > -2)
        ):
            print(f"App crashed during consent dialog interaction: {app_package}, retrying")
            dynamic_found_purposes[dynamic_index] = "unhandled"
            if not crash_handling(snapshot_name, analyzation, app_index, val, app_package, ip_and_port):
                dynamic_purpose_amounts[dynamic_index] = -2
            continue

        traffic_failed = False
        print(f"Collecting traffic for: {app_package}")
        for i in range(total_sleep_period):
            time.sleep(sleep_period)
            if i > 1:
                if crash_handling(snapshot_name, analyzation, app_index, val, app_package, ip_and_port):
                    dynamic_purpose_amounts[dynamic_index] = 0
                    dynamic_found_purposes[dynamic_index] = "unhandled"
                    traffic_failed = True
                    print(f"Traffic failed for app: {app_package}")
                    csv_status_update(analyzation, app_index, val)
                    break

        if not traffic_failed:
            csv_status_update(analyzation, app_index, (val + 10))
            print(f"Traffic has been collected for: {app_package}")
        try:
            subprocess.run(
                f'adb shell "am force-stop {app_package}"',
                timeout=5,
                text=True,
                shell=True,
                stdin=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
            )
        except Exception as e:
            global_util.kill_running_apps()

        # Clear data to keep emulator fast
        subprocess.run(f'adb shell "pm clear {app_package}"', stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

    overwrite_csvs()


if __name__ == "__main__":
    app_amt = int(input("How many applications do you want to analyze the traffic for and interact with: "))
    interaction_method = input("Which method do you want to use for interacting with the applications (n[othing]/l[egitimate interest]/a[ll]): ").lower()
    restart_amt = int(input("How many applications do you want to analyze before rebooting the device: "))
    import subprocess
    import datetime
    import time
    import pandas
    import signal
    from plyer import notification
    import sys
    from os import path
    import json

    file_path = __file__
    dir_path = path.dirname(file_path)
    dir_path = path.dirname(dir_path)
    sys.path.append(f"{dir_path}")
    from appium import webdriver
    from appium.options.android import (
        UiAutomator2Options,
    )
    from selenium.common.exceptions import WebDriverException

    import dynamic_analysis.dynamic_analyzer as dynamic_analyzer
    import auxiliary.global_util as global_util
    import dynamic_analysis.dynamic_util as dynamic_util

    main(app_amt, interaction_method, restart_amt)
else:
    import subprocess
    import datetime
    import time
    import pandas
    import signal
    from plyer import notification
    import sys
    from os import path
    import json

    file_path = __file__
    dir_path = path.dirname(file_path)
    dir_path = path.dirname(dir_path)
    sys.path.append(f"{dir_path}")
    from appium import webdriver
    from appium.options.android import (
        UiAutomator2Options,
    )
    from selenium.common.exceptions import WebDriverException

    import dynamic_analysis.dynamic_analyzer as dynamic_analyzer
    import auxiliary.global_util as global_util
    import dynamic_analysis.dynamic_util as dynamic_util

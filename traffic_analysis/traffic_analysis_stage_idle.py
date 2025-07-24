import subprocess
import time
import pandas
import signal
from plyer import notification
import sys
from os import path

file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)
sys.path.append(f"{dir_path}\\auxiliary")
import global_util


# Check if Frida-server (f-server) is running and if not, potential to boot.
def on_interrupt(signal, frame):
    if apps and nothing and li and all:
        overwrite_csvs()


def check_boot_frida() -> bool:
    frida_check_res = subprocess.run(
        'adb shell "ps -A | grep f-server"', stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True
    ).stdout
    if not frida_check_res:
        print("Frida was not running, booting...")
        subprocess.Popen(
            "adb shell \"su -c '/data/local/tmp/./f-server'\"", stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, text=True
        )
        time.sleep(5)
        return False
    return True


def boot_emu_snapshot() -> bool:
    global_util.kill_emu()
    print("Starting phone")
    sleep_ctr = 0
    proc = subprocess.Popen(
        f"emulator -avd android_device -snapshot {snapshot_name}",
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
                f"emulator -avd android_device -snapshot {snapshot_name}",
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
            time.sleep(10)
            subprocess.run(
                (f'adb shell su -c "settings put global http_proxy {ip_and_port}"'),
                shell=True,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                text=True,
            )
            return True
        if (sleep_ctr + 1) % 21 == 0:
            print(f"Have waited {str(sleep_ctr * 2)} seconds trying to reboot emulator")
        sleep_ctr += 1


def continue_or_reboot():
    restart_timer = 0
    while True:
        if (restart_timer + 1) % 6 == 0:
            print(f"Waited {str(2 * restart_timer)} while checking status.")
        if restart_timer >= 35:
            print("Hard crash, rebooting phone")
            if not boot_emu_snapshot():
                print("Objection- and mitm-instances have NOT been terminated.")
                overwrite_csvs()
            break
        if global_util.emu_status():
            break
        time.sleep(2)
        restart_timer += 1
    return


def csv_status_update(index: int, val: int):
    match analyzation:
        case "LI":
            li[index] = val
        case "All":
            all[index] = val
        case _:
            nothing[index] = val


def overwrite_csvs():
    global_util.overwrite_csv(traffic_headers, [apps, nothing, li, all], "traffic.csv", False)
    global_util.overwrite_csv(
        dynamic_headers, [dynamic_apps, dynamic_cmps, dynamic_activities, dynamic_purpose_amounts, dynamic_found_purposes], dynamic_csv
    )


def snapshot_load(snapshot_name):
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
            return
    except Exception as e:
        pass
    if not boot_emu_snapshot():
        print("Failed to boot phone")
        overwrite_csvs()


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


def extract_purposes(app_package: str) -> str:
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


ip = subprocess.run("netsh interface ipv4 show addresses", shell=True, text=True, stdout=subprocess.PIPE).stdout
ip = ip[ip.find("Ethernet") : ]
ip = ip[ip.find("DHCP enabled:") :]
ip = ip[ip.find("Yes") :]
ip = ip[ip.find("192") : ip.find("Subnet")].strip()
ip_and_port = ip + ":8080"


app_amt = int(input("How many applications do you want to analyze the traffic for: "))
interaction_method = input("Which method has been used for interacting with the applications (n[othing]/l[egitimate interest]/a[ll]): ").lower()
restart_amt = int(input("How many applications do you want to analyze before rebooting the device: "))
if not (interaction_method == "n" or interaction_method == "l" or interaction_method == "a"):
    print(f"Incorrect interaction method selected: {interaction_method}, quitting ..")
    quit()

match interaction_method:
    case "l":
        analyzation = "LI"
        dynamic_csv = "dynamic_LI.csv"
        snapshot_name = "dynamic_LI_interaction"
    case "a":
        analyzation = "All"
        dynamic_csv = "dynamic_all.csv"
        snapshot_name = "dynamic_all_interaction"
    case "n":
        analyzation = "Nothing"
        dynamic_csv = "dynamic_nothing.csv"
        snapshot_name = "dynamic_nothing_interaction"

in_traffic = set()
apps, nothing, li, all = [], [], [], []
traffic_headers = ["App package", "Nothing", "LI", "All"]

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

dynamic_apps, dynamic_cmps, dynamic_activities, dynamic_purpose_amounts, dynamic_found_purposes = [], [], [], [], []
dynamic_indices = {}
dynamic_headers = ["App package", "SdkId", "MainActivity", "Purpose Amount", "Found Purposes"]
try:
    statusFrame = pandas.read_csv(f"{dir_path}/csv-files/{dynamic_csv}", usecols=dynamic_headers, index_col=False)
    for index, row in statusFrame.iterrows():
        if row["Purpose Amount"] > 0 and row["App package"] not in in_traffic:
            apps.append(row["App package"])
            nothing.append(0)
            li.append(0)
            all.append(0)
        dynamic_indices[row["App package"]] = index
        dynamic_apps.append(row["App package"])
        dynamic_cmps.append(row["SdkId"])
        dynamic_activities.append(row["MainActivity"])
        dynamic_purpose_amounts.append(row["Purpose Amount"])
        dynamic_found_purposes.append(row["Found Purposes"])
except Exception as e:
    print(f"Could not find {dynamic_csv}, quitting.")
    quit()

mitm_status = subprocess.run(
    "tasklist | findstr mitm", shell=True, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
).stdout
if not mitm_status:
    mitm_proc_input = f'mitmdump -q -s mitm_addon_stage_idle.py --set analysis_type="{analyzation}"'
    subprocess.Popen(mitm_proc_input, shell=True, text=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print("Booting mitmdump")
snapshot_load(snapshot_name)
signal.signal(signal.SIGINT, on_interrupt)
ctr = 0
sleep_period = 13  # Decides for how long each app is analyzed (3*13 seconds)
recurring_phone_crash = 0
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
    # If phone crashes 3 times in a row, we believe that is due to the application it tries to launch.
    if val > 3:
        app_index += 1
        continue
    app_package = apps[app_index]
    if ctr >= app_amt:
        print(f"Analyzed {str(ctr)} applications, quitting..")
        break
    if dynamic_found_purposes[dynamic_indices[app_package]] == "unhandled" and dynamic_purpose_amounts[dynamic_indices[app_package]] > 0:
        continue_or_reboot()
        dynamic_found_purposes[dynamic_indices[app_package]] = extract_purposes(app_package)
        continue
    elif (
        dynamic_found_purposes[dynamic_indices[app_package]] == "no active purposes"
        or (analyzation == "Nothing" and dynamic_found_purposes[dynamic_indices[app_package]] != "0 LI & 0 consent.")
        or (
            analyzation == "LI"
            and ("0 LI" in dynamic_found_purposes[dynamic_indices[app_package]] or "0 consent" not in dynamic_found_purposes[dynamic_indices[app_package]])
        )
        or dynamic_purpose_amounts[dynamic_indices[app_package]] <= 0
    ):
        print(f"Error in Found Purposes: {app_package}")
        app_index += 1
        continue

    print(f"Running: {app_package}")
    if (
        "1"
        in subprocess.run(
            'adb shell "getprop sys.boot_completed"', text=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
        ).stdout.strip()
    ):
        recurring_phone_crash = 0
    else:
        recurring_phone_crash += 1
        time.sleep(20)
    continue_or_reboot()

    if (ctr + 1) % (restart_amt + 1) == 0:
        print("Loading snapshot")
        snapshot_load(snapshot_name)

    check_boot_frida()  # Check if Frida is running, else boot
    # A new minimzed (/min) cmd will be booted, running objection
    subprocess.Popen(
        ["start", "/min", "cmd.exe", "/k", "objection", "-g", app_package, "explore", "--quiet", "--startup-command", "android sslpinning disable"],
        shell=True,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    app_running = True
    rerun_app = False
    google_play_login = ""
    for i in range(sleep_period):
        time.sleep(3)
        if i > 1:
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
                if recurring_phone_crash > 2:
                    val = -1
                    recurring_phone_crash = 0
                    csv_status_update(app_index, val)
                else:
                    csv_status_update(app_index, val)
                    rerun_app = True
                break
            if not app_running or app_package not in curr_activity:
                csv_status_update(app_index, val)
                rerun_app = True
                print(f"App: {app_package} crashed")
                if ".NexusLauncherActivity" not in curr_activity:  # Implemented to fix Google white-screen
                    snapshot_load(snapshot_name)
                break
            if i == sleep_period - 1:
                csv_status_update(app_index, (val + 10))

    obj_pid_num = global_util.find_pid("objection")
    global_util.kill_proc(obj_pid_num)

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
        rerun_app = True
    time.sleep(3)

    # Terminate cmd which booted objection
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

    ctr += 1
    if not rerun_app:
        app_index += 1

    if ".games.ui.signinflow.SignInActivity" in curr_activity:
        pm_enable_disable("disable", "com.google.android.gms")
        time.sleep(2)
        pm_enable_disable("enable", "com.google.android.gms")
    if "com.android.vending" in curr_activity:
        pm_enable_disable("disable", "com.android.vending")
        time.sleep(2)
        pm_enable_disable("enable", "com.android.vending")

subprocess.run(
    'adb shell su -c "settings put global http_proxy :0"',
    shell=True,
    stdin=subprocess.DEVNULL,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.PIPE,
    text=True,
)
overwrite_csvs()

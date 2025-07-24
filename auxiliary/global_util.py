import pandas
from plyer import notification
import subprocess
import time
from os import path

file_path = __file__
dir_path = path.dirname(file_path)
dir_path = path.dirname(dir_path)


def overwrite_csv(header_args: list[str], data_args: list[list[str]], csv: str, stop_code_execution: bool = True):
    data = {}
    for i in range(len(data_args)):
        data[header_args[i]] = data_args[i]
    df = pandas.DataFrame(data)
    df.to_csv(f"{dir_path}/csv-files/{csv}", mode="w", header=header_args, index=False)
    print(f"Updated {csv}")
    if stop_code_execution:
        notification.notify(title=f"Updated {csv}", message=f"Updated {csv}", timeout=1)
        quit()


def append_csv(header_args: list[str], data_args: list[list[str]], csvs: list[str]):
    if data_args[0]:
        data = {}
        for i in range(len(data_args)):
            data[header_args[i]] = data_args[i]
        df = pandas.DataFrame(data)
        for csv in csvs:
            df.to_csv(f"{dir_path}/csv-files/{csv}", mode="a", header=False, index=False)
            print(f"Appended to {csv}")


def read_csv(header_args: list[str], csv: str, data_args: list[list[str]], status_arg: str = None, app_indices: set[int] = None):
    try:
        statusFrame = pandas.read_csv(f"{dir_path}/csv-files/{csv}", usecols=header_args, index_col=False)
        for index, row in statusFrame.iterrows():
            if "Status" in header_args and row["Status"] == status_arg:
                app_indices.add(index)
            for i in range(len(header_args)):
                data_args[i].append(row[header_args[i]])
    except Exception as e:
        print(f"Could not find '{csv}', quitting.")
        quit()


# Read from 'csv' and add newly scraped apps from 'scraped_apps.csv'
def fetch_scraped_apps(header_args: list[str], csv: str):
    apps, status, countries, tcf_version, dates = [], [], [], [], []
    read_csv(
        header_args,
        csv,
        [apps, status, countries, tcf_version, dates],
    )

    curr_apps = set(apps)
    try:
        statusFrame = pandas.read_csv(f"{dir_path}/csv-files/scraped_apps.csv", usecols=["App package", "Date scraped"], index_col=False)
        for index, row in statusFrame.iterrows():
            if row["App package"] not in curr_apps:
                apps.append(row["App package"])
                status.append("Scraped")
                countries.append("Unknown")
                tcf_version.append("Unknown")
                dates.append(row["Date scraped"])
    except Exception as e:
        print(f"Could not find 'scraped_apps.csv', quitting.")
        quit()

    overwrite_csv(header_args, [apps, status, countries, tcf_version, dates], csv, False)


def count_running_activities(running_apps: list[str]) -> int:
    activity_amt = len(running_apps)
    for app in running_apps:
        if "com.android" in app or "com.google.android" in app or "com.google.mainline" in app:
            activity_amt -= 1
    return activity_amt


# Kills all currently running apps
def kill_running_apps():
    subprocess.run('adb shell "am kill-all"')  # Kill background processes
    running_apps = (
        subprocess.run(
            "adb shell su -c \"dumpsys activity activities | grep -i mactivitycomponent | cut -d '=' -f2 | cut -d '/' -f1\"",
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
        .stdout.strip()
        .split("\n")
    )
    for app in running_apps:
        app = app.strip()
        if app:
            subprocess.run(f'adb shell "am force-stop {app}"', stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)
    prev_activity_amt = count_running_activities(running_apps)
    if prev_activity_amt <= 1:
        return
    time.sleep(3)
    curr_activity_amt = prev_activity_amt
    while prev_activity_amt < curr_activity_amt:
        running_apps = (
            subprocess.run(
                "adb shell su -c \"dumpsys activity activities | grep -i mactivitycomponent | cut -d '=' -f2 | cut -d '/' -f1\"",
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
            )
            .stdout.strip()
            .split("\n")
        )
        curr_activity_amt = count_running_activities(running_apps)
        time.sleep(1)


def give_perms(app: str, emu: str = "emulator-5554"):
    permissions = subprocess.run(
        f'adb -s {emu} shell "dumpsys package {app} | grep -i granted=false | cut -d: -f1"',
        stdin=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.split("\n")
    for p in permissions:
        if p:
            p = p.strip()
            subprocess.run(
                (f'adb -s {emu} shell su -c "pm grant {app} {p}"'),
                stdin=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                stdout=subprocess.DEVNULL,
                text=True,
            )


def emu_status(emu: str = "emulator-5554") -> bool:
    curr_activity = subprocess.run(
        f'adb -s {emu} shell "dumpsys activity activities | grep -i mactivitycomponent="',
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout.strip()
    if ".NexusLauncherActivity" in curr_activity:
        return True
    return False


def boot_emu(emu: str = "emulator-5554") -> bool:
    if emu_status(emu):
        return True
    emu_name = "android_device"
    subprocess.Popen(
        f"emulator -avd {emu_name}",
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        text=True,
    )
    emu_ctr = 0
    while True:
        if emu_ctr == 50:
            print("Could not start emulator, trying coldstart")
            if not kill_emu():
                return False
            time.sleep(3)
            subprocess.Popen(
                f"emulator -avd {emu_name} -no-snapshot-load",
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                text=True,
            )
        if emu_ctr >= 100:
            print("Coldstart failed, quitting")
            return False
        time.sleep(2)
        if emu_status(emu):
            time.sleep(10)
            return True
        emu_ctr += 1


def kill_emu():
    qemu = find_pid("qemu")
    sleep_ctr = 0
    if qemu:
        print("Killing emulator")
        try:
            subprocess.run("adb emu kill", timeout=10, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL, text=True)
        except Exception as e:
            kill_proc(qemu)
        while True:
            adb_dev = subprocess.run("adb devices", stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.PIPE, text=True).stdout
            if "emulator" not in adb_dev:
                break
            if sleep_ctr > 20:
                print("Could not kill emulator")
                return False
            time.sleep(2)
            sleep_ctr += 1
    return True


def find_pid(proc_name: str) -> str:
    pid = subprocess.run(
        f"tasklist | findstr {proc_name}", shell=True, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout
    if not pid:
        return ""
    pid = pid[pid.find("exe") + len("exe") :].strip()
    pid = pid[: pid.find(" ")]
    return pid


def kill_proc(pid: str):
    subprocess.run((f"taskkill /F /PID {pid}"), shell=True, text=True, stdin=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdout=subprocess.DEVNULL)

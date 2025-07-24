from mitmproxy import http
from mitmproxy import addonmanager
import subprocess
import psycopg
from datetime import date
import re
import urllib.parse
import json
from os import path


def load_config():
    file_path = path.abspath(__file__)
    dir_path = path.dirname(file_path)
    dir_path = path.dirname(dir_path)
    with open(f"{dir_path}\\traffic_analysis\\mitm_inputs.json", "r") as file:
        return json.load(file)


def load(loader: addonmanager.Loader):
    loader.add_option(name="analysis_type", typespec=str, default="def_value", help="argument passed with mitmdump to specify analysis type")


def find_pd_regex(pattern, body, path) -> list[str]:
    matches = []
    matches = pattern.findall(body)
    if not matches:
        matches = pattern.findall(path)
    return matches


def response(flow: http.HTTPFlow):
    mitm_input_data = load_config()
    app_package = mitm_input_data["app_package"]
    if app_package == "":
        return
    analysis_type = mitm_input_data["analysis_type"]
    aaid = subprocess.run(
        "adb shell \"su -c 'grep adid data/data/com.google.android.gms/shared_prefs/adid_settings.xml | head -n 1'\"",
        stdin=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        text=True,
    ).stdout
    aaid = aaid[aaid.find(">") + 1 : aaid.rfind("<")]
    aid = subprocess.run(
        "adb shell \"su -c 'settings get secure android_id'\"", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout.strip()
    pub_ip = subprocess.run(
        "nslookup myip.opendns.com. resolver1.opendns.com", stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True
    ).stdout
    pub_ip = pub_ip[pub_ip.find("myip.opendns.com") + len("myip.opendns.com") :]
    pub_ip = pub_ip[pub_ip.find("Address:") + len("Address:") :].strip()
    if not pub_ip or not aid or not aaid:
        return

    user_email = "pojo000119@gmail.com"
    regex_intro = r'[\'"][^"\']+[\'"]\s*[:,]\s*[\'"]\s*'
    phone_num_regex_user = (
        regex_intro + r'(?:\+1\s?|1\s?)?\(?555\)?[\s.-]?123[\s.-]?4567[\'"]'
    )  # Find: "(anything not '"')" spaces : spaces "any version of our phone number"; Backslashes are to find specific chars and not use regex-functions

    phone_num_regex_pattern_user = re.compile(phone_num_regex_user)
    imei = "867400022047199"
    device_mac_regex = regex_intro + r'10[\s.\-:]?15[\s.\-:]?b2[\s.\-:]?00[\s.\-:]?00[\s.\-:]?00["\']'
    device_mac_regex_pattern = re.compile(device_mac_regex)
    latitude_longitude = regex_intro + r'57[\s.,-]68\d*[\s.,-]11[\s.,-]97\d*["\']'
    latitude = regex_intro + r'57[\s.,-]68\d*["\']'
    longitude = regex_intro + r'11[\s.,-]97\d*["\']'
    latitude_longitude_pattern = re.compile(latitude_longitude)
    latitude_pattern = re.compile(latitude)
    longitude_pattern = re.compile(longitude)
    imsi = "310260000000000"
    icc_id = "89860318640220133897"  # SIM-card serial number
    serial_num_regex = r'(?i)["\'][^"\']+["\']\s*:\s*["\']emulator35x3x11x0["\']'  # Handles letters of any case
    serial_num_regex_pattern = re.compile(serial_num_regex)

    pd_dict = {
        aaid: "AAID",
        aid: "AID",
        user_email: "user_email",
        phone_num_regex_user: "user_mobile",
        imei: "IMEI",
        device_mac_regex: "device_MAC",
        latitude_longitude: "device_location",
        latitude: "device_latitude_coordinate",
        longitude: "device_longitude_coordinate",
        imsi: "imsi",
        icc_id: "icc_id",
        serial_num_regex: "device_serial_num",
        pub_ip: "public_IP",
    }
    request_violation = []
    pd = []
    date_today = date.today()
    url = ""
    protobuf = False
    pd_found_in_path = False
    status_code = flow.response.status_code
    headers = str(flow.request.headers).lower()
    charset = "utf-8"
    if headers.find("content-type") != -1:  # Find encoding (most often utf-8)
        content_type = headers[headers.find("content-type") + len("content-type") :]
        if content_type.find("; charset") != -1:
            charset = content_type[content_type.find("; charset=") + len("; charset=") : content_type.find(")") - 1]
        elif "protobuf" in content_type:
            protobuf = True
    request_body = flow.request.get_content().decode(charset, errors="ignore")
    if flow.request.urlencoded_form:  # Url-encoded forms need to be specified
        request_body = str(flow.request.urlencoded_form)
    decoded_path = urllib.parse.unquote(flow.request.path)

    index = -1
    will_update_db = False
    for personal_data in pd_dict:
        matches = []
        match pd_dict[personal_data]:
            case "user_mobile":
                matches = find_pd_regex(phone_num_regex_pattern_user, request_body, decoded_path)
            case "device_MAC":
                matches = find_pd_regex(device_mac_regex_pattern, request_body, decoded_path)
            case "device_serial_num":
                matches = find_pd_regex(serial_num_regex_pattern, request_body, decoded_path)
            case "device_location":
                matches = find_pd_regex(latitude_longitude_pattern, request_body, decoded_path)
            case "device_latitude_coordinate":
                matches = find_pd_regex(latitude_pattern, request_body, decoded_path)
            case "device_longitude_coordinate":
                matches = find_pd_regex(longitude_pattern, request_body, decoded_path)
            case _:  # All non-regex PD

                index = request_body.find(personal_data)
                if index == -1:
                    index = decoded_path.find(personal_data)
                    if index == -1:
                        continue
                    else:
                        pd_found_in_path = True

                print("Violation found")
                will_update_db = True
                pd_key = "no_key_found (protobuf)"
                quote_char = '"'
                request_method = f"{str(flow.request.method)} from body"
                if pd_found_in_path:
                    decoded_path_cpy = decoded_path
                    amp_index = decoded_path_cpy[:index].rfind("&")
                    comma_index = decoded_path_cpy[:index].rfind(",")
                    bracket_index = decoded_path_cpy[:index].rfind("{")
                    question_mark_index = decoded_path_cpy[:index].rfind("?")
                    separator_index = max(amp_index, comma_index, bracket_index, question_mark_index) + 1
                    pd_key = decoded_path_cpy[separator_index:index]
                    request_method = f"{str(flow.request.method)} from URL"
                elif not protobuf:
                    request_body_cpy = request_body
                    if request_body_cpy[index - 1] == "'":
                        quote_char = request_body_cpy[index - 1]
                    request_body_cpy = request_body_cpy[: index - 1]  # Remove first quote of val
                    request_body_cpy = request_body_cpy[: request_body_cpy.rfind(quote_char)]  # Remove last quote of key
                    pd_key = request_body_cpy[request_body_cpy.rfind(quote_char) + 1 :]  # Removing ':"' with '-2' (from "key":"id")
                    if len(pd_key) >= 80:
                        pd_key = "Improper request-key (length/encoding)"

                request_violation.append(f'{request_method}: "{pd_key}":"{personal_data}"')
                pd.append(pd_dict[personal_data])
                continue
        if matches:
            print("Violation found")
            will_update_db = True
            request_violation.append(matches[0])
            pd.append(pd_dict[personal_data])
            continue
    if will_update_db:
        url = flow.request.url
        q_mark_index = url.find("?")
        if q_mark_index != -1:
            url = url[:q_mark_index]
        with psycopg.connect("dbname=android_tcf_traffic_analysis user=postgres password=postgres") as conn:
            with conn.cursor() as cur:
                query = """
                    INSERT INTO active_stage (app_package, request, url, pd, analysis, date, status_code)
                    SELECT %s, %s, %s, %s, %s, %s, %s
                    ON CONFLICT (app_package,request,url,analysis,status_code) DO NOTHING;"""  # The database-table has a constraint for (app_package,request,url,analysis, status_code) being unique
                values = [(app_package, request_violation[i], url, pd[i], analysis_type, date_today, status_code) for i in range(len(pd))]
                cur.executemany(query, values)
                conn.commit()

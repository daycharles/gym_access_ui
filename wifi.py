import json
import os

WIFI_CONFIG_PATH = "data/wifi.json"
WPA_SUPPLICANT_PATH = "/etc/wpa_supplicant/wpa_supplicant.conf"

def load_wifi_config():
    if os.path.exists(WIFI_CONFIG_PATH):
        with open(WIFI_CONFIG_PATH) as f:
            return json.load(f)
    return {"ssid": "", "password": ""}

def save_wifi_config(ssid, password):
    config = {"ssid": ssid, "password": password}
    with open(WIFI_CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def write_to_wpa_supplicant(ssid, password):
    content = f"""country=US
ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev
update_config=1

network={{
    ssid=\"{ssid}\"
    psk=\"{password}\"
    key_mgmt=WPA-PSK
}}
"""
    try:
        with open(WPA_SUPPLICANT_PATH, "w") as f:
            f.write(content)
        return True
    except PermissionError:
        return False

def restart_wifi():
    os.system("sudo wpa_cli -i wlan0 reconfigure")

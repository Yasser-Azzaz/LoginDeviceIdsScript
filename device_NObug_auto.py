import subprocess
import time
import os
import xml.etree.ElementTree as ET
from tqdm import tqdm
from datetime import datetime, timedelta
import platform

DEVICE_IDS_FILE = "device_ids.txt"
PACKAGE_NAME = "com.mobile.legends"
XML_FILENAME = "com.mobile.legends.v2.playerprefs.xml"
XML_PATH = f"/data/data/{PACKAGE_NAME}/shared_prefs/{XML_FILENAME}"
TEMP_XML_FILE = XML_FILENAME

EMU_SS_PATH = os.path.expanduser(r"~\AppData\Roaming\XuanZhi9\XuanZhi9\Pictures")
PHONE_SS_PATH = os.path.expanduser(r"~\Desktop\MlbbDeviceIdsSceenShots")

WAIT_TIMES = {
    'emulator': 22,
    'phone': 10
}

LOG_FILE = "results.log"
MAX_IDS_TO_PROCESS = 20000 

def run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return result.stdout.strip()

def list_devices():
    output = run(["adb", "devices", "-l"])
    lines = output.splitlines()[1:]
    devices = []
    for line in lines:
        if not line.strip(): continue
        parts = line.split()
        if len(parts) < 2: continue
        device_id = parts[0]
        model_info = next((p for p in parts if p.startswith("model:")), "model:Unknown")
        model_name = model_info.split(":")[1]
        device_type = "Emulator" if "emulator" in device_id.lower() else "Phone"
        devices.append((device_id, model_name, device_type))
    return devices

def choose_device(devices):
    print("\n📱 Connected Devices:")
    for i, (_, model, dtype) in enumerate(devices):
        print(f"[{i}] {model} ({dtype})")
    while True:
        idx = input("\nSelect device: ")
        if idx.isdigit() and 0 <= int(idx) < len(devices):
            return devices[int(idx)]
        print("⚠ Invalid selection.")

def read_ids():
    with open(DEVICE_IDS_FILE, "r") as f:
        all_ids = [line.strip() for line in f if line.strip()]
    return all_ids[:MAX_IDS_TO_PROCESS]

def delete_xml_file(device_id):
    # Uses -f to force delete even if the file was set to read-only (444) in the previous loop
    run(["adb", "-s", device_id, "shell", "su", "-c", f"rm -f {XML_PATH}"])

def pull_xml(device_id):
    run(["adb", "-s", device_id, "shell", "su", "-c", f"cp {XML_PATH} /sdcard/{XML_FILENAME}"])
    run(["adb", "-s", device_id, "pull", f"/sdcard/{XML_FILENAME}", TEMP_XML_FILE])

def update_device_id(device_id_value):
    tree = ET.parse(TEMP_XML_FILE)
    root = tree.getroot()
    updated = False
    for string in root.findall("string"):
        if string.attrib.get("name") in ["JsonDeviceID", "__Java_JsonDeviceID__"]:
            string.text = device_id_value
            updated = True
    if updated:
        tree.write(TEMP_XML_FILE, encoding="utf-8", xml_declaration=True)
    else:
        raise ValueError("Device ID keys not found in XML.")

def push_xml_and_lock(device_id):
    """Pushes the XML and immediately sets permissions to 444 (Read-Only)"""
    run(["adb", "-s", device_id, "push", TEMP_XML_FILE, f"/sdcard/{XML_FILENAME}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"cp /sdcard/{XML_FILENAME} {XML_PATH}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"chmod 444 {XML_PATH}"])

def launch_mlbb(device_id):
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])
    run(["adb", "-s", device_id, "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

def close_mlbb(device_id):
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])

def take_screenshot(device_id, filename, device_type):
    remote_path = f"/sdcard/Pictures/{filename}.png"
    run(["adb", "-s", device_id, "shell", "screencap", "-p", remote_path])
    if device_type == "Phone":
        os.makedirs(PHONE_SS_PATH, exist_ok=True)
        local_path = os.path.join(PHONE_SS_PATH, f"{filename}.png")
        run(["adb", "-s", device_id, "pull", remote_path, local_path])

def write_log(line):
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(line + "\n")

def handle_device(device_id, device_type, ids):
    wait_time = WAIT_TIMES[device_type.lower()]
    screenshot_path = EMU_SS_PATH if device_type == "Emulator" else PHONE_SS_PATH
    os.makedirs(screenshot_path, exist_ok=True)

    total = len(ids)
    start_time = time.time()
    processed_count = 0

    for i, did in enumerate(tqdm(ids, desc="Processing", unit="id")):
        index = i + 1
        ss_filename = str(index)
        ss_full_path = os.path.join(screenshot_path, f"{ss_filename}.png")

        if os.path.exists(ss_full_path):
            continue

        id_start_time = time.time()
        try:
            print(f"\n\033[94m🔄 [{index}/{total}] ID:\033[0m {did}")
            
            # --- PREPARATION ---
            delete_xml_file(device_id)
            launch_mlbb(device_id) # Let game generate a fresh file
            time.sleep(wait_time)
            close_mlbb(device_id)
            time.sleep(2)
            
            pull_xml(device_id)
            update_device_id(did)
            
            # --- STEP 1: FIRST PUSH & LOCK ---
            print("📤 [1/2] Pushing modified XML and locking (444)...")
            push_xml_and_lock(device_id)
            
            # --- STEP 2: REPEAT/PRIME STEP ---
            print("🎮 Launching to register changes (No SS)...")
            launch_mlbb(device_id)
            time.sleep(wait_time)
            close_mlbb(device_id)
            time.sleep(2)

            # --- STEP 3: SECOND PUSH & LOCK (Verification) ---
            print("📤 [2/2] Re-pushing and Re-locking XML...")
            push_xml_and_lock(device_id)
            
            # --- STEP 4: FINAL LAUNCH & SCREENSHOT ---
            print("📸 Final Launch for real screenshot...")
            launch_mlbb(device_id)
            time.sleep(wait_time) 
            take_screenshot(device_id, ss_filename, device_type)
            
            close_mlbb(device_id)
            processed_count += 1
            
            elapsed = time.time() - id_start_time
            print(f"\033[92m[✓] ID {index} done in {elapsed:.2f}s\033[0m")
            write_log(f"[OK] ID {index} - {did}")

        except Exception as e:
            print(f"\033[91m[✘] Failed ID {index} - {str(e)}\033[0m")
            write_log(f"[ERROR] ID {index} - {str(e)}")
            try: close_mlbb(device_id)
            except: pass

def main():
    devices = list_devices()
    if not devices: return
    selected = choose_device(devices)
    handle_device(selected[0], selected[2], read_ids())

if __name__ == "__main__":
    main()
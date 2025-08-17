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
    'phone': 11.5
}

LOG_FILE = "results.log"
MAX_IDS_TO_PROCESS = 100 # Maximum number of IDs to process

def run(cmd):
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)
    return result.stdout.strip()

def list_devices():
    output = run(["adb", "devices", "-l"])
    lines = output.splitlines()[1:]
    devices = []
    for line in lines:
        if not line.strip():
            continue
        parts = line.split()
        if len(parts) < 2:
            continue
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
        print("⚠ Invalid selection. Try again.")

def read_ids():
    with open(DEVICE_IDS_FILE, "r") as f:
        all_ids = [line.strip() for line in f if line.strip()]
    
    # Limit to maximum number of IDs
    if len(all_ids) > MAX_IDS_TO_PROCESS:
        print(f"\n⚠️ Found {len(all_ids)} IDs, but limiting to {MAX_IDS_TO_PROCESS} IDs as configured.")
        return all_ids[:MAX_IDS_TO_PROCESS]
    else:
        print(f"\n✅ Found {len(all_ids)} IDs (within the {MAX_IDS_TO_PROCESS} ID limit).")
        return all_ids

def delete_xml_file(device_id):
    """Delete the XML file from the device to force game to create a new one"""
    print("🗑️ Deleting old XML file...")
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

def push_xml(device_id):
    run(["adb", "-s", device_id, "push", TEMP_XML_FILE, f"/sdcard/{XML_FILENAME}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"cp /sdcard/{XML_FILENAME} {XML_PATH}"])

def launch_mlbb(device_id):
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])
    run(["adb", "-s", device_id, "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

def close_mlbb(device_id):
    """Close the Mobile Legends game"""
    print("🔒 Closing Mobile Legends...")
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

def play_sound():
    if platform.system() == "Windows":
        import winsound
        winsound.MessageBeep(winsound.MB_OK)

def handle_device(device_id, device_type, ids):
    wait_time = WAIT_TIMES[device_type.lower()]
    screenshot_path = EMU_SS_PATH if device_type == "Emulator" else PHONE_SS_PATH
    os.makedirs(screenshot_path, exist_ok=True)

    total = len(ids)
    start_time = time.time()
    processed_count = 0

    for i, did in enumerate(tqdm(ids, desc=f"{device_type} Processing", unit="id")):
        # Check if we've reached the limit
        if processed_count >= MAX_IDS_TO_PROCESS:
            print(f"\n\033[93m🛑 Reached maximum limit of {MAX_IDS_TO_PROCESS} IDs. Stopping...\033[0m")
            write_log(f"[LIMIT] Stopped after processing {MAX_IDS_TO_PROCESS} IDs")
            break

        index = i + 1
        ss_filename = str(index)
        ss_full_path = os.path.join(screenshot_path, f"{ss_filename}.png")

        if os.path.exists(ss_full_path):
            print(f"\033[96m[⭐] Skipped ID {index} - Screenshot already exists\033[0m")
            write_log(f"[SKIP] ID {index} - Screenshot already exists")
            continue

        id_start_time = time.time()
        try:
            print(f"\n\033[94m🔄 [{index}/{total}] {device_type} - Device ID:\033[0m {did}")
            
            # Step 1: Delete old XML file
            delete_xml_file(device_id)
            
            # Step 2: Launch game to create new XML file
            print("🚀 Launching game to create new XML file...")
            launch_mlbb(device_id)
            time.sleep(wait_time)  # Wait for game to fully load and create XML
            
            # Step 3: Close game
            close_mlbb(device_id)
            time.sleep(2)  # Short wait to ensure game is fully closed
            
            # Step 4: Pull the newly created XML file
            print("📥 Pulling newly created XML file...")
            pull_xml(device_id)
            
            # Step 5: Update device ID in XML
            print("✏️ Updating device ID in XML...")
            update_device_id(did)
            
            # Step 6: Push modified XML back
            print("📤 Pushing modified XML back...")
            push_xml(device_id)
            
            # Step 7: Launch game with modified XML
            print("🎮 Launching game with modified XML...")
            launch_mlbb(device_id)
            time.sleep(wait_time)  # Wait for game to load with new device ID
            
            # Step 8: Take screenshot
            print("📸 Taking screenshot...")
            take_screenshot(device_id, ss_filename, device_type)
            
            # Step 9: Close game again
            close_mlbb(device_id)

            processed_count += 1
            elapsed = time.time() - id_start_time
            avg_so_far = (time.time() - start_time) / processed_count
            remaining = min(total - index, MAX_IDS_TO_PROCESS - processed_count)
            est_finish = datetime.now() + timedelta(seconds=remaining * avg_so_far)

            print(f"\033[92m[✓] ID {index} done in {elapsed:.2f}s | Processed: {processed_count}/{MAX_IDS_TO_PROCESS} | Remaining: {remaining} | ETA: {est_finish.strftime('%H:%M:%S')}\033[0m")
            write_log(f"[OK] ID {index} - {did} - Took {elapsed:.2f}s - Processed count: {processed_count}")

        except Exception as e:
            print(f"\033[91m[✘] Failed ID {index} - {str(e)}\033[0m")
            write_log(f"[ERROR] ID {index} - {str(e)}")
            # Try to close game even if there was an error
            try:
                close_mlbb(device_id)
            except:
                pass

    total_time = time.time() - start_time
    play_sound()
    print(f"\n\033[95m✅ Completed processing {processed_count} IDs in {total_time/60:.2f} minutes\033[0m")
    write_log(f"\n--- Finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Time: {total_time:.2f}s | Processed: {processed_count} IDs ---\n")

def main():
    print("🔍 Scanning for devices...\n")
    devices = list_devices()
    if not devices:
        print("⚠ No devices found.")
        return
    selected = choose_device(devices)
    device_id, model, device_type = selected
    print(f"\n✅ Selected: {model} ({device_type})")
    ids = read_ids()
    handle_device(device_id, device_type, ids)

if __name__ == "__main__":
    main()
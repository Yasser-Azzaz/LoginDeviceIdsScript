import subprocess
import os
import xml.etree.ElementTree as ET

# --- Configuration ---
DEVICE_IDS_FILE = "device_ids.txt"
PACKAGE_NAME = "com.mobile.legends"
XML_FILENAME = "com.mobile.legends.v2.playerprefs.xml"
XML_PATH = f"/data/data/{PACKAGE_NAME}/shared_prefs/{XML_FILENAME}"
TEMP_XML_FILE = XML_FILENAME

# ──────────────────────────────────────────────
# ADB HELPERS
# ──────────────────────────────────────────────

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
        model_name = next((p for p in parts if p.startswith("model:")), "model:Unknown").split(":")[1]
        devices.append((device_id, model_name))
    return devices

def choose_device(devices):
    print("\n📱 Connected Devices:")
    for i, (did, model) in enumerate(devices):
        print(f"[{i}] {model} ({did})")
    while True:
        idx = input("\nSelect device index: ")
        if idx.isdigit() and 0 <= int(idx) < len(devices):
            return devices[int(idx)][0]
        print("⚠ Invalid selection.")

def pull_xml(device_id):
    """Pulls the original XML structure once per session."""
    run(["adb", "-s", device_id, "shell", "su", "-c", f"cp {XML_PATH} /sdcard/{XML_FILENAME}"])
    run(["adb", "-s", device_id, "pull", f"/sdcard/{XML_FILENAME}", TEMP_XML_FILE])

def update_device_id_in_xml(new_id):
    tree = ET.parse(TEMP_XML_FILE)
    root = tree.getroot()
    for string in root.findall("string"):
        if string.attrib.get("name") in ["JsonDeviceID", "__Java_JsonDeviceID__"]:
            string.text = new_id
    tree.write(TEMP_XML_FILE, encoding="utf-8", xml_declaration=True)

def push_and_lock(device_id):
    """Pushes the modified XML and locks it to Read-Only (444)."""
    run(["adb", "-s", device_id, "push", TEMP_XML_FILE, f"/sdcard/{XML_FILENAME}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"cp /sdcard/{XML_FILENAME} {XML_PATH}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"chmod 444 {XML_PATH}"])

def launch_game(device_id):
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])
    run(["adb", "-s", device_id, "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

def get_id_by_line(line_number):
    """Reads the specific line number from device_ids.txt."""
    if not os.path.exists(DEVICE_IDS_FILE):
        print(f"✘ Error: {DEVICE_IDS_FILE} not found!")
        return None
    try:
        with open(DEVICE_IDS_FILE, "r") as f:
            lines = f.readlines()
            # line_number is 1-based index (like line 1, line 2...)
            if 1 <= line_number <= len(lines):
                return lines[line_number - 1].strip()
            else:
                print(f"⚠ Error: Line {line_number} is out of range (Total lines: {len(lines)})")
                return None
    except Exception as e:
        print(f"✘ Error reading file: {e}")
        return None

# ──────────────────────────────────────────────
# MAIN INTERACTIVE LOOP
# ──────────────────────────────────────────────

def main():
    devices = list_devices()
    if not devices:
        print("No devices found via ADB.")
        return
    
    selected_device = choose_device(devices)
    
    print(f"📥 Initializing XML from device...")
    pull_xml(selected_device)

    while True:
        print("\n" + "─" * 40)
        user_input = input("Enter ID Line Number (or 'exit' to quit): ").strip().lower()

        if user_input == 'exit':
            print("👋 Exiting script.")
            break
        
        if not user_input.isdigit():
            print("⚠ Please enter a valid number.")
            continue
        
        line_num = int(user_input)
        target_id = get_id_by_line(line_num)
        
        if target_id:
            print(f"🚀 Processing Line {line_num} | ID: {target_id}")
            
            # 1. Update local temp XML
            update_device_id_in_xml(target_id)
            
            # 2. Push and lock it
            print("   📤 Pushing and locking XML (444)...")
            push_and_lock(selected_device)
            
            # 3. Launch
            print("   🎮 Launching MLBB...")
            launch_game(selected_device)
            
            print(f"\n✅ Done! MLBB is running with ID: {target_id}")
        else:
            print("❌ Operation failed for that line.")

if __name__ == "__main__":
    main()
import os
import re
import time
import subprocess
import keyboard

ADB_PATH = r"C:\LDPlayer\LDPlayer9\adb.exe"
DEVICE_ID_FILE = "MLBB_Device_IDs.txt"
PACKAGE_NAME = "com.mobile.legends"
ACTIVITY_NAME = "com.mobile.legends.UnityPlayerActivity"
XML_PATH = "/data/data/com.mobile.legends/shared_prefs/com.mobile.legends.v2.playerprefs.xml"
LOCAL_TEMP_XML = "temp_playerprefs.xml"
SCREENSHOT_PATH = "/storage/emulated/0/Pictures/"

device_ids = []
current_device_index = 0
mlbb_running = False

def run_adb_command(cmd_args, capture_output=False):
    full_cmd = [ADB_PATH, "-s", "127.0.0.1:5555"] + cmd_args
    try:
        result = subprocess.run(full_cmd, stdout=subprocess.PIPE if capture_output else None, stderr=subprocess.STDOUT, text=True)
        if capture_output:
            return result.stdout.strip()
    except Exception as e:
        print(f"❌ ADB command failed: {e}")
    return None

def load_device_ids():
    global device_ids
    if os.path.exists(DEVICE_ID_FILE):
        with open(DEVICE_ID_FILE, "r", encoding="utf-8") as f:
            device_ids = [line.strip() for line in f if line.strip()]
        print(f"✅ Loaded {len(device_ids)} Device IDs from {DEVICE_ID_FILE}")
    else:
        print(f"❌ Device ID file '{DEVICE_ID_FILE}' not found.")
        exit(1)

def stop_mlbb():
    global mlbb_running
    print("🛑 Mobile Legends stopped.")
    run_adb_command(["shell", "am", "force-stop", PACKAGE_NAME])
    mlbb_running = False

def launch_mlbb():
    global mlbb_running
    print("🚀 Launching Mobile Legends...\n")
    run_adb_command(["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])
    mlbb_running = True

def pull_xml():
    print("📥 Pulling XML from device...")
    run_adb_command(["shell", "su", "-c", f"chmod 666 {XML_PATH}"])
    run_adb_command(["pull", XML_PATH, LOCAL_TEMP_XML])
    if os.path.exists(LOCAL_TEMP_XML):
        return True
    print("❌ Pull failed: temp_playerprefs.xml not created.")
    return False

def modify_xml(device_id):
    if not pull_xml():
        print("❌ Failed to read XML file! Skipping this device.\n")
        return

    print("📖 Editing XML file...")
    with open(LOCAL_TEMP_XML, "r", encoding="utf-8") as f:
        xml_content = f.read()

    xml_content = re.sub(
        r'(<string name="JsonDeviceID">)(.*?)(</string>)',
        lambda m: m.group(1) + device_id + m.group(3),
        xml_content
    )

    xml_content = re.sub(
        r'(<string name="__Java_JsonDeviceID__">)(.*?)(</string>)',
        lambda m: m.group(1) + device_id + m.group(3),
        xml_content
    )

    with open(LOCAL_TEMP_XML, "w", encoding="utf-8") as f:
        f.write(xml_content)

    print("📤 Pushing modified XML to device...")
    run_adb_command(["push", LOCAL_TEMP_XML, XML_PATH])
    run_adb_command(["shell", "su", "-c", f"chmod 444 {XML_PATH}"])

    print("✅ XML file updated and set to read-only.\n")

def take_screenshot(device_number):
    """Take a screenshot and save it directly to device storage with numbered filename"""
    screenshot_filename = f"{device_number}.png"
    device_screenshot_path = f"{SCREENSHOT_PATH}{screenshot_filename}"
    
    print(f"📸 Taking screenshot for Device #{device_number}...")
    
    # Take screenshot and save directly to device storage
    result = run_adb_command([
        "shell", 
        "screencap", 
        "-p", 
        device_screenshot_path
    ], capture_output=True)
    
    if result is not None:
        print(f"✅ Screenshot saved as {screenshot_filename} in device Pictures folder")
    else:
        print(f"❌ Failed to take screenshot for Device #{device_number}")

def wait_for_app_load():
    """Wait for the app to fully load before taking screenshot"""
    print("⏳ Waiting for Mobile Legends to load...")
    time.sleep(30)  # Wait for full login screen to appear

def process_device_id(device_id, device_number):
    global mlbb_running
    print("======================================================================")
    print("🤖 AUTOMATED PROCESSING - DEVICE ID")
    print("======================================================================")
    print(f"🆔 Device ID: {device_id}")
    print(f"📱 Device Number: {device_number}")

    if mlbb_running:
        stop_mlbb()

    modify_xml(device_id)
    launch_mlbb()
    
    # Wait for app to load, then take screenshot
    wait_for_app_load()
    take_screenshot(device_number)

def main():
    global current_device_index
    load_device_ids()

    print(f"\n📁 Source File: {DEVICE_ID_FILE}")
    print(f"📊 Total Device IDs: {len(device_ids)}")
    print("📸 Screenshots will be saved to device Pictures folder as 1.png, 2.png, etc.")
    print("🤖 Script will automatically process all Device IDs. Press ESC to exit.\n")
    print("🚀 Starting automated processing in 3 seconds...")
    time.sleep(3)

    while current_device_index < len(device_ids):
        if keyboard.is_pressed("esc"):
            print("👋 Exiting script.")
            break

        device_number = current_device_index + 1  # Start numbering from 1
        process_device_id(device_ids[current_device_index], device_number)
        current_device_index += 1
        
        # Small delay between processing to allow for any manual intervention
        if current_device_index < len(device_ids):
            print(f"⏳ Moving to next device in 3 seconds... ({current_device_index}/{len(device_ids)} completed)")
            time.sleep(3)

    print("✅ All Device IDs have been processed automatically!")
    print("📸 Check your device's Pictures folder for all screenshots (1.png, 2.png, etc.)")
    print("👋 Script completed. Press any key to exit...")
    input()

if __name__ == "__main__":
    main()
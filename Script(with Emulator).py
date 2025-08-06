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
            return result.stdout.strip(), result.returncode
        return None, result.returncode
    except Exception as e:
        print(f"❌ ADB command failed: {e}")
        return None, -1

def check_root_access():
    """Check if device has root access"""
    print("🔍 Checking root access...")
    output, returncode = run_adb_command(["shell", "su", "-c", "id"], capture_output=True)
    if returncode == 0 and "uid=0" in output:
        print("✅ Root access confirmed")
        return True
    else:
        print("❌ Root access not available or not granted")
        return False

def check_file_exists():
    """Check if the XML file exists"""
    print("🔍 Checking if XML file exists...")
    output, returncode = run_adb_command(["shell", "su", "-c", f"ls -la {XML_PATH}"], capture_output=True)
    if returncode == 0:
        print(f"✅ XML file found: {output}")
        return True
    else:
        print(f"❌ XML file not found or inaccessible: {output}")
        return False

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
    print("🛑 Stopping Mobile Legends...")
    run_adb_command(["shell", "am", "force-stop", PACKAGE_NAME])
    # Wait a bit for the app to fully close
    time.sleep(3)
    mlbb_running = False
    print("✅ Mobile Legends stopped.")

def get_main_activity():
    """Get the correct main activity for Mobile Legends"""
    print("🔍 Finding correct main activity...")
    output, returncode = run_adb_command(["shell", "dumpsys", "package", PACKAGE_NAME], capture_output=True)
    
    if returncode == 0 and output:
        # Look for the main activity in the dumpsys output
        lines = output.split('\n')
        for line in lines:
            if 'android.intent.action.MAIN' in line and 'android.intent.category.LAUNCHER' in line:
                # Extract activity name from the line
                if 'ActivityInfo' in line:
                    parts = line.split()
                    for part in parts:
                        if PACKAGE_NAME in part and '/' in part:
                            activity = part.split('/')[-1]
                            return activity
    
    # Fallback: try common activity names
    common_activities = [
        "com.unity3d.player.UnityPlayerActivity",
        "com.unity3d.player.UnityPlayerNativeActivity", 
        "MainActivity",
        "SplashActivity",
        "LauncherActivity"
    ]
    
    return common_activities[0]  # Default fallback

def launch_mlbb():
    global mlbb_running
    print("🚀 Launching Mobile Legends...")
    
    # Try multiple methods to launch the app
    methods = [
        # Method 1: Use monkey (original method that was working)
        ["shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"],
        
        # Method 2: Use am start with package name only
        ["shell", "am", "start", "-n", f"{PACKAGE_NAME}/.MainActivity"],
        
        # Method 3: Use am start with Unity activity
        ["shell", "am", "start", "-n", f"{PACKAGE_NAME}/com.unity3d.player.UnityPlayerActivity"],
        
        # Method 4: Simple intent launch
        ["shell", "am", "start", "-a", "android.intent.action.MAIN", "-c", "android.intent.category.LAUNCHER", PACKAGE_NAME]
    ]
    
    for i, method in enumerate(methods, 1):
        print(f"🔄 Trying launch method {i}...")
        output, returncode = run_adb_command(method, capture_output=True)
        
        if returncode == 0 and "Error" not in output:
            print(f"✅ Mobile Legends launched successfully using method {i}")
            mlbb_running = True
            return True
        else:
            print(f"❌ Method {i} failed: {output}")
    
    print("❌ All launch methods failed")
    mlbb_running = False
    return False

def pull_xml():
    global LOCAL_TEMP_XML
    print("📥 Pulling XML from device...")
    
    # Clean up any existing temp file first
    if os.path.exists(LOCAL_TEMP_XML):
        try:
            os.remove(LOCAL_TEMP_XML)
            print("🧹 Cleaned up existing temp file")
        except Exception as e:
            print(f"⚠️ Warning: Could not remove existing temp file: {e}")
    
    # First, make the file readable with root
    output, returncode = run_adb_command(["shell", "su", "-c", f"chmod 644 {XML_PATH}"], capture_output=True)
    if returncode != 0:
        print(f"❌ Failed to change permissions: {output}")
        return False
    
    # Copy to a temporary location accessible by ADB
    temp_path = "/sdcard/temp_playerprefs.xml"
    
    # Clean up any existing temp file on device
    run_adb_command(["shell", "rm", temp_path])
    
    output, returncode = run_adb_command(["shell", "su", "-c", f"cp {XML_PATH} {temp_path}"], capture_output=True)
    if returncode != 0:
        print(f"❌ Failed to copy file to accessible location: {output}")
        return False
    
    # Make sure the temp file is readable
    run_adb_command(["shell", "chmod", "644", temp_path])
    
    # Try pulling to different local paths if current directory has issues
    local_paths = [
        LOCAL_TEMP_XML,  # Current directory
        f"C:\\temp\\{os.path.basename(LOCAL_TEMP_XML)}",  # C:\temp\
        f"{os.path.expanduser('~')}\\{os.path.basename(LOCAL_TEMP_XML)}",  # User home directory
    ]
    
    for local_path in local_paths:
        # Create directory if it doesn't exist
        local_dir = os.path.dirname(local_path)
        if local_dir and not os.path.exists(local_dir):
            try:
                os.makedirs(local_dir, exist_ok=True)
            except:
                continue
        
        print(f"🔄 Attempting to pull to: {local_path}")
        output, returncode = run_adb_command(["pull", temp_path, local_path], capture_output=True)
        
        if returncode == 0 and os.path.exists(local_path):
            print(f"✅ XML file pulled successfully to: {local_path}")
            # Update the global variable to use the successful path
            LOCAL_TEMP_XML = local_path
            # Clean up temporary file on device
            run_adb_command(["shell", "rm", temp_path])
            return True
        else:
            print(f"❌ Failed to pull to {local_path}: {output}")
    
    # Clean up temporary file on device
    run_adb_command(["shell", "rm", temp_path])
    print("❌ Failed to pull XML file to any location")
    return False

def push_xml():
    print("📤 Pushing modified XML to device...")
    
    # Push to temporary location first
    temp_path = "/sdcard/temp_playerprefs.xml"
    
    # Clean up any existing temp file on device
    run_adb_command(["shell", "rm", temp_path])
    
    output, returncode = run_adb_command(["push", LOCAL_TEMP_XML, temp_path], capture_output=True)
    if returncode != 0:
        print(f"❌ Failed to push file to temporary location: {output}")
        return False
    
    # Copy from temporary location to final destination with root
    output, returncode = run_adb_command(["shell", "su", "-c", f"cp {temp_path} {XML_PATH}"], capture_output=True)
    if returncode != 0:
        print(f"❌ Failed to copy file to final location: {output}")
        return False
    
    # Set proper permissions
    run_adb_command(["shell", "su", "-c", f"chmod 644 {XML_PATH}"])
    run_adb_command(["shell", "su", "-c", f"chown u0_a65:u0_a65 {XML_PATH}"])
    
    # Clean up temporary file on device
    run_adb_command(["shell", "rm", temp_path])
    
    # Clean up local temp file
    try:
        if os.path.exists(LOCAL_TEMP_XML):
            os.remove(LOCAL_TEMP_XML)
            print("🧹 Cleaned up local temp file")
    except Exception as e:
        print(f"⚠️ Warning: Could not clean up local temp file: {e}")
    
    print("✅ XML file pushed and permissions set")
    return True

def modify_xml(device_id):
    if not pull_xml():
        print("❌ Failed to pull XML file! Skipping this device.\n")
        return False

    print("📖 Editing XML file...")
    try:
        with open(LOCAL_TEMP_XML, "r", encoding="utf-8") as f:
            xml_content = f.read()

        # Replace JsonDeviceID
        xml_content = re.sub(
            r'(<string name="JsonDeviceID">)(.*?)(</string>)',
            lambda m: m.group(1) + device_id + m.group(3),
            xml_content
        )

        # Replace __Java_JsonDeviceID__
        xml_content = re.sub(
            r'(<string name="__Java_JsonDeviceID__">)(.*?)(</string>)',
            lambda m: m.group(1) + device_id + m.group(3),
            xml_content
        )

        with open(LOCAL_TEMP_XML, "w", encoding="utf-8") as f:
            f.write(xml_content)

        if not push_xml():
            print("❌ Failed to push modified XML file!")
            return False

        print("✅ XML file updated successfully.\n")
        return True
        
    except Exception as e:
        print(f"❌ Error modifying XML file: {e}")
        return False

def take_screenshot(device_number):
    """Take a screenshot and save it directly to device storage with numbered filename"""
    screenshot_filename = f"{device_number}.png"
    device_screenshot_path = f"{SCREENSHOT_PATH}{screenshot_filename}"
    
    print(f"📸 Taking screenshot for Device #{device_number}...")
    
    # Take screenshot and save directly to device storage
    output, returncode = run_adb_command([
        "shell", 
        "screencap", 
        "-p", 
        device_screenshot_path
    ], capture_output=True)
    
    if returncode == 0:
        print(f"✅ Screenshot saved as {screenshot_filename} in device Pictures folder")
        return True
    else:
        print(f"❌ Failed to take screenshot for Device #{device_number}: {output}")
        return False

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

    # Modify XML and check if successful
    if not modify_xml(device_id):
        print("❌ Skipping this device due to XML modification failure.")
        return False

    if not launch_mlbb():
        print("❌ Failed to launch Mobile Legends. Skipping screenshot.")
        return False
    
    # Wait for app to load, then take screenshot
    wait_for_app_load()
    take_screenshot(device_number)
    return True

def main():
    global current_device_index
    load_device_ids()

    print(f"\n📁 Source File: {DEVICE_ID_FILE}")
    print(f"📊 Total Device IDs: {len(device_ids)}")
    print("📸 Screenshots will be saved to device Pictures folder as 1.png, 2.png, etc.")
    
    # Check prerequisites
    if not check_root_access():
        print("❌ Root access is required for this script to work!")
        print("💡 Make sure your LDPlayer has root enabled and grant root access when prompted.")
        input("Press any key to exit...")
        return
    
    # Make sure MLBB is installed and has created the preferences file
    if not check_file_exists():
        print("❌ MLBB preferences file not found!")
        print("💡 Make sure Mobile Legends is installed and has been launched at least once.")
        input("Press any key to exit...")
        return
    
    print("🤖 Script will automatically process all Device IDs. Press ESC to exit.\n")
    print("🚀 Starting automated processing in 3 seconds...")
    time.sleep(3)

    successful_count = 0
    failed_count = 0

    while current_device_index < len(device_ids):
        if keyboard.is_pressed("esc"):
            print("👋 Exiting script.")
            break

        device_number = current_device_index + 1  # Start numbering from 1
        if process_device_id(device_ids[current_device_index], device_number):
            successful_count += 1
        else:
            failed_count += 1
            
        current_device_index += 1
        
        # Small delay between processing to allow for any manual intervention
        if current_device_index < len(device_ids):
            print(f"⏳ Moving to next device in 3 seconds... ({current_device_index}/{len(device_ids)} completed)")
            time.sleep(3)

    print(f"✅ Processing completed! Successfully processed: {successful_count}, Failed: {failed_count}")
    print("📸 Check your device's Pictures folder for all screenshots (1.png, 2.png, etc.)")
    print("👋 Script completed. Press any key to exit...")
    input()

if __name__ == "__main__":
    main()
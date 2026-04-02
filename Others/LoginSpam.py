import subprocess
import time
import os
from tqdm import tqdm
from datetime import datetime, timedelta
import platform

PACKAGE_NAME = "com.mobile.legends"
XML_FILENAME = "com.mobile.legends.v2.playerprefs.xml"
XML_PATH = f"/data/data/{PACKAGE_NAME}/shared_prefs/{XML_FILENAME}"

WAIT_TIME = 13  # 13 seconds wait time
LOG_FILE = "results.log"
MAX_ITERATIONS = 999999  # Reduced to a reasonable maximum number

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
        print("❌ Invalid selection. Try again.")

def set_xml_readonly(device_id):
    """Set XML file permissions to read-only (444)"""
    run(["adb", "-s", device_id, "shell", "su", "-c", f"chmod 444 {XML_PATH}"])
    print("🔒 XML file set to read-only (444)")

def launch_mlbb(device_id):
    """Launch MLBB app"""
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])
    time.sleep(1)  # Brief pause before launching
    run(["adb", "-s", device_id, "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

def close_mlbb(device_id):
    """Close MLBB app"""
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])

def write_log(line):
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(line + "\n")

def play_sound():
    if platform.system() == "Windows":
        import winsound
        winsound.MessageBeep(winsound.MB_OK)

def run_mlbb_cycles(device_id, device_type):
    """Run repeated MLBB open/close cycles"""
    print(f"\n🚀 Starting MLBB cycles on {device_type}")
    print(f"⏱️  Each cycle: Set XML read-only (444) → Open MLBB → Wait {WAIT_TIME}s → Close MLBB")
    print(f"🔄 Maximum iterations: {MAX_ITERATIONS} (or run indefinitely with Ctrl+C to stop)")
    print("Press Ctrl+C to stop\n")
    
    start_time = time.time()
    iteration = 0
    
    try:
        # Run indefinitely or until MAX_ITERATIONS
        while iteration < MAX_ITERATIONS:
            iteration += 1
            cycle_start_time = time.time()
            
            print(f"\n🔄 [{iteration}] Starting cycle...")
            write_log(f"[CYCLE {iteration}] Starting at {datetime.now().strftime('%H:%M:%S')}")
            
            # Set XML file to read-only BEFORE opening MLBB
            print("🔧 Setting XML permissions to read-only (444)...")
            set_xml_readonly(device_id)
            
            # Launch MLBB
            print("📱 Opening MLBB...")
            launch_mlbb(device_id)
            
            # Wait for the specified time
            print(f"⏳ Waiting {WAIT_TIME} seconds for MLBB to load...")
            time.sleep(WAIT_TIME)
            
            # Close MLBB
            print("🔒 Closing MLBB...")
            close_mlbb(device_id)
            
            # Calculate timing
            cycle_time = time.time() - cycle_start_time
            total_elapsed = time.time() - start_time
            avg_cycle_time = total_elapsed / iteration
            
            print(f"✅ Cycle {iteration} completed in {cycle_time:.2f}s")
            write_log(f"[CYCLE {iteration}] Completed in {cycle_time:.2f}s")
            
            # Brief pause between cycles
            time.sleep(2)
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Stopped by user after {iteration} cycles")
        write_log(f"[STOP] User interrupted after {iteration} cycles")
    except Exception as e:
        print(f"\n❌ Error during cycle {iteration}: {str(e)}")
        write_log(f"[ERROR] Cycle {iteration} failed: {str(e)}")
        # Continue to the next cycle instead of stopping
        time.sleep(2)
        return run_mlbb_cycles(device_id, device_type)  # Restart the function
    
    total_time = time.time() - start_time
    play_sound()
    print(f"\n🏁 Completed {iteration} cycles in {total_time/60:.2f} minutes")
    if iteration > 0:
        print(f"📊 Average cycle time: {total_time/iteration:.2f}s")
    write_log(f"\n--- Session finished at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | Total Time: {total_time:.2f}s | Cycles: {iteration} ---\n")

def main():
    print("🔍 Scanning for devices...\n")
    devices = list_devices()
    if not devices:
        print("❌ No devices found.")
        return
    
    # Device selection
    selected = choose_device(devices)
    device_id, model, device_type = selected
    print(f"\n✅ Selected: {model} ({device_type})")
    print("📝 Note: Make sure you've already manually set your device ID in the XML file!")
    
    # Run the cycles
    run_mlbb_cycles(device_id, device_type)

if __name__ == "__main__":
    main()
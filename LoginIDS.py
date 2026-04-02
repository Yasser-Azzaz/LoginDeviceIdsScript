import subprocess
import time
import os
import xml.etree.ElementTree as ET
from tqdm import tqdm
import cv2
import numpy as np
from skimage.metrics import structural_similarity as ssim

DEVICE_IDS_FILE = "device_ids.txt"
PACKAGE_NAME = "com.mobile.legends"
XML_FILENAME = "com.mobile.legends.v2.playerprefs.xml"

XML_PATH = f"/data/data/{PACKAGE_NAME}/shared_prefs/{XML_FILENAME}"
TEMP_XML_FILE = XML_FILENAME

EMU_SS_PATH = os.path.expanduser(r"~\AppData\Roaming\XuanZhi9\XuanZhi9\Pictures")
PHONE_SS_PATH = os.path.expanduser(r"~\Desktop\MlbbDeviceIdsSceenShots")

# --- Folder containing your 2-3 reference "bad" images ---
REFERENCE_IMAGES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reference_images")

SIMILARITY_THRESHOLD = 0.85  # 85% — tweak if needed

WAIT_TIMES = {
    'emulator': 22,
    'phone': 10
}

LOG_FILE = "results.log"
MAX_IDS_TO_PROCESS = 20000


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
        print("⚠ Invalid selection.")

def read_ids():
    with open(DEVICE_IDS_FILE, "r") as f:
        all_ids = [line.strip() for line in f if line.strip()]
    return all_ids[:MAX_IDS_TO_PROCESS]

def delete_xml_file(device_id):
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
    run(["adb", "-s", device_id, "push", TEMP_XML_FILE, f"/sdcard/{XML_FILENAME}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"cp /sdcard/{XML_FILENAME} {XML_PATH}"])
    run(["adb", "-s", device_id, "shell", "su", "-c", f"chmod 444 {XML_PATH}"])

def launch_mlbb(device_id):
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])
    run(["adb", "-s", device_id, "shell", "monkey", "-p", PACKAGE_NAME, "-c", "android.intent.category.LAUNCHER", "1"])

def close_mlbb(device_id):
    run(["adb", "-s", device_id, "shell", "am", "force-stop", PACKAGE_NAME])

def take_screenshot(device_id, filename, device_type):
    """Takes screenshot, always pulls to a temp local path. Returns the local path."""
    remote_path = f"/sdcard/Pictures/{filename}.png"
    run(["adb", "-s", device_id, "shell", "screencap", "-p", remote_path])

    if device_type == "Phone":
        save_dir = PHONE_SS_PATH
    else:
        save_dir = EMU_SS_PATH

    os.makedirs(save_dir, exist_ok=True)
    local_path = os.path.join(save_dir, f"{filename}.png")
    run(["adb", "-s", device_id, "pull", remote_path, local_path])
    return local_path

def write_log(line):
    with open(LOG_FILE, "a", encoding="utf-8") as log:
        log.write(line + "\n")


# ──────────────────────────────────────────────
# IMAGE VERIFICATION
# ──────────────────────────────────────────────

def load_reference_images():
    """Load all images from the reference_images folder. Exits if folder is empty or missing."""
    if not os.path.isdir(REFERENCE_IMAGES_DIR):
        print(f"⚠  reference_images/ folder not found at: {REFERENCE_IMAGES_DIR}")
        print("   Create it and place your 2–3 reference 'bad' images inside.")
        exit(1)

    refs = []
    for fname in os.listdir(REFERENCE_IMAGES_DIR):
        if fname.lower().endswith((".png", ".jpg", ".jpeg")):
            path = os.path.join(REFERENCE_IMAGES_DIR, fname)
            img = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if img is not None:
                refs.append((fname, img))

    if not refs:
        print("⚠  No valid images found in reference_images/. Add your bad-screen PNG/JPGs.")
        exit(1)

    print(f"✅ Loaded {len(refs)} reference image(s): {[r[0] for r in refs]}")
    return refs


def compare_images(img_path, ref_img_gray):
    """
    Compare a screenshot (by path) to a reference grayscale image.
    Resizes both to the same size before comparing.
    Returns SSIM score (0.0 – 1.0).
    """
    shot = cv2.imread(img_path, cv2.IMREAD_GRAYSCALE)
    if shot is None:
        return 0.0

    # Resize screenshot to match reference dimensions
    h, w = ref_img_gray.shape
    shot_resized = cv2.resize(shot, (w, h))

    score, _ = ssim(shot_resized, ref_img_gray, full=True)
    return score


def is_bad_screenshot(img_path, reference_images):
    """
    Returns (True, ref_name, score) if the screenshot matches ANY reference image
    at >= SIMILARITY_THRESHOLD. Otherwise returns (False, None, best_score).
    """
    for ref_name, ref_gray in reference_images:
        score = compare_images(img_path, ref_gray)
        print(f"   🔍 vs [{ref_name}]: similarity = {score:.2%}")
        if score >= SIMILARITY_THRESHOLD:
            return True, ref_name, score
    return False, None, 0.0


# ──────────────────────────────────────────────
# MAIN LOOP
# ──────────────────────────────────────────────

def handle_device(device_id, device_type, ids):
    wait_time = WAIT_TIMES[device_type.lower()]
    screenshot_path = EMU_SS_PATH if device_type == "Emulator" else PHONE_SS_PATH
    os.makedirs(screenshot_path, exist_ok=True)

    reference_images = load_reference_images()

    # --- Initial Pull Only ---
    print(f"📥 Pulling base XML for this session...")
    pull_xml(device_id) 
    # -------------------------

    total = len(ids)

    for i, did in enumerate(tqdm(ids, desc="Processing", unit="id")):
        index = i + 1
        ss_filename = str(index)
        ss_full_path = os.path.join(screenshot_path, f"{ss_filename}.png")

        # Skip already-processed IDs (resume support)
        if os.path.exists(ss_full_path):
            continue

        id_start_time = time.time()
        attempt = 0

        print(f"\n\033[94m🔄 [{index}/{total}] ID:\033[0m {did}")

        try:
            # Update the local XML with the new ID
            update_device_id(did)

            # ── VERIFICATION LOOP ──
            while True:
                attempt += 1
                print(f"\n   🔁 Attempt #{attempt} for ID {index}")

                # Push & lock XML
                print("   📤 Pushing modified XML and locking (444)...")
                push_xml_and_lock(device_id)

                # Launch, wait, screenshot
                print("   📸 Launching for screenshot...")
                launch_mlbb(device_id)
                time.sleep(wait_time)

                # Pull screenshot to a TEMP path for verification
                temp_ss_name = f"_temp_verify_{index}"
                temp_ss_path = take_screenshot(device_id, temp_ss_name, device_type)
                close_mlbb(device_id)
                time.sleep(2)

                # Verify
                bad, matched_ref, score = is_bad_screenshot(temp_ss_path, reference_images)

                if bad:
                    # Screenshot matched a bad reference — retry same ID
                    print(f"   \033[91m[✘] MATCH with '{matched_ref}' ({score:.2%}) — retrying same ID...\033[0m")
                    write_log(f"[RETRY] ID {index} attempt #{attempt} - matched '{matched_ref}' ({score:.2%}) - {did}")

                    # Clean up temp file
                    try:
                        os.remove(temp_ss_path)
                    except OSError:
                        pass
                    
                    # Note: We no longer "regenerate" here, we just loop back 
                    # and re-push the ID to the existing XML.

                else:
                    # Screenshot is clean — rename temp to final and move on
                    print(f"   \033[92m[✓] Clean screenshot (best similarity below threshold). Saving.\033[0m")
                    os.rename(temp_ss_path, ss_full_path)
                    break  # ← exit retry loop, advance to next ID

            elapsed = time.time() - id_start_time
            print(f"\033[92m[✓] ID {index} done in {elapsed:.2f}s after {attempt} attempt(s)\033[0m")
            write_log(f"[OK] ID {index} attempts={attempt} - {did}")

        except Exception as e:
            print(f"\033[91m[✘] Failed ID {index} - {str(e)}\033[0m")
            write_log(f"[ERROR] ID {index} - {str(e)}")
            try:
                close_mlbb(device_id)
            except Exception:
                pass
def main():
    devices = list_devices()
    if not devices:
        return
    selected = choose_device(devices)
    handle_device(selected[0], selected[2], read_ids())


if __name__ == "__main__":
    main()
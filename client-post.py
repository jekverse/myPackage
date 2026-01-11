import requests
import time
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
import sys
import subprocess
import re
import os
import uuid

# --- KONFIGURASI API ---
API_URL = os.getenv("API_URL", "")
API_KEY = os.getenv("API_KEY", "")

CF_CLIENT_ID = os.getenv("CF_CLIENT_ID", "")
CF_CLIENT_SECRET = os.getenv("CF_CLIENT_SECRET", "")

# Generate Unique Session ID for this VM instance
SESSION_ID = str(uuid.uuid4())

def get_system_info():
    """Mengambil Profile dan GPU dari environment variables"""
    profile_name = os.getenv("MODAL_ACCOUNT_NAME") or os.getenv("USER", "Unknown_User")

    try:
        # Coba jalankan nvidia-smi
        gpu_output = subprocess.check_output("nvidia-smi", shell=True, text=True, stderr=subprocess.DEVNULL)
        match_gpu = re.search(r"\|\s+\d+\s+(.*?)\s+On", gpu_output)
        full_gpu_name = match_gpu.group(1).strip() if match_gpu else ""

        gpu_dataset = ["B200", "H200", "H100", "A100, 80 GB", "A100, 40 GB", "L40S", "A10", "L4", "T4"]
        
        detected_gpu_type = "Unknown"
        for ds_name in gpu_dataset:
            clean_ds = ds_name.replace(",", "")
            if clean_ds in full_gpu_name:
                detected_gpu_type = "Nvidia " + ds_name
                break
        
        # Jika lolos nvidia-smi tapi tidak match list
        if detected_gpu_type == "Unknown":
            detected_gpu_type = "Nvidia Generic" # Atau biarkan Unknown

    except (subprocess.CalledProcessError, FileNotFoundError):
        # nvidia-smi failed or not found -> CPU Mode
        detected_gpu_type = "CPU"
    except Exception as e:
        print(f"Error detect GPU: {e}")
        detected_gpu_type = "CPU" # Safe fallback

    return profile_name, detected_gpu_type

# --- EKSEKUSI DAN LOOP ---
profile_name, gpu_type = get_system_info()

if not profile_name or profile_name == "Unknown_User":
    # Retry fallback logic if needed or just warn
    print("Warning: Profile Name tidak terdeteksi (MODAL_ACCOUNT_NAME env missing).")

print(f"--- Monitoring Aktif ---")
print(f"Account : {profile_name}")
print(f"GPU     : {gpu_type}")
print(f"Session : {SESSION_ID}")

CONFIG = {
    "account_name": profile_name,
    "gpu_type": gpu_type,
    "session_id": SESSION_ID
}

HEADERS = {
    "X-API-KEY": API_KEY,
    "Content-Type": "application/json"
}

if CF_CLIENT_ID and CF_CLIENT_SECRET:
    HEADERS["CF-Access-Client-Id"] = CF_CLIENT_ID
    HEADERS["CF-Access-Client-Secret"] = CF_CLIENT_SECRET
elif "jekarta.site" in API_URL:
    print("WARNING: Menggunakan domain jekarta.site tanpa CF_CLIENT_ID/SECRET mungkin akan gagal (403).")

# Use Session for connection pooling
session = requests.Session()
session.headers.update(HEADERS)

while True:
    try:
        response = session.post(API_URL, json=CONFIG, timeout=15, verify=False)
        if response.status_code == 200:
            try:
                res = response.json()
                if res.get("status") == "depleted":
                    print("\nSALDO HABIS!")
                    sys.exit(0)
                # Use \r to overwrite line, \033[K to clear rest of line
                print(f"\r[{time.strftime('%H:%M:%S')}] Sisa: {res['remaining']} | Est: {res['estimate']} \033[K", end="", flush=True)
            except ValueError:
                print(f"\r[{time.strftime('%H:%M:%S')}] Error: Invalid JSON response (Status 200) \033[K", end="", flush=True)
        else:
            # Handle non-200 errors (e.g. 502 Bad Gateway from Cloudflare)
            short_msg = "Bad Gateway/Server Error" if response.status_code in [502, 503, 504] else "Error"
            print(f"\r[{time.strftime('%H:%M:%S')}] Server Response {response.status_code}: {short_msg} | Body: {response.text[:100]} \033[K", end="", flush=True)
    except Exception as e:
        print(f"\r[{time.strftime('%H:%M:%S')}] Connection Error: {str(e)} \033[K", end="", flush=True)
    
    time.sleep(20)

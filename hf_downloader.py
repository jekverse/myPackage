import os
import sys
import shutil
import argparse
import subprocess
import time

# ============================================================================
# 1. KONFIGURASI USER (HARDCODED TOKEN)
# ============================================================================
# Masukkan token Hugging Face Anda (dimulai dengan hf_...) di sini:
MY_HF_TOKEN = "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" 

# ============================================================================
# 2. DEPENDENCY CHECK & SETUP
# ============================================================================
try:
    import huggingface_hub
    from huggingface_hub import hf_hub_download
except ImportError:
    print("⚠️  Library huggingface_hub tidak ditemukan. Menginstall otomatis...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-U", "huggingface_hub[hf_transfer]"])
    import huggingface_hub
    from huggingface_hub import hf_hub_download

# WAJIB: Aktifkan Rust Downloader untuk kecepatan maksimal
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# ============================================================================
# 3. CORE FUNCTIONS
# ============================================================================

def parse_hf_url(url):
    """Mengurai URL Hugging Face menjadi Repo ID, Filename, dan Branch."""
    clean_url = url.replace("https://huggingface.co/", "")
    
    if "/resolve/" in clean_url:
        splitter = "/resolve/"
    elif "/blob/" in clean_url:
        splitter = "/blob/"
    else:
        raise ValueError("URL tidak valid. Harus mengandung '/resolve/' atau '/blob/'.")

    parts = clean_url.split(splitter)
    repo_id = parts[0]
    remainder = parts[1]

    if "/" in remainder:
        branch, file_path_in_repo = remainder.split("/", 1)
    else:
        branch = remainder
        file_path_in_repo = remainder 

    filename_only = file_path_in_repo.split("/")[-1]
    
    return repo_id, file_path_in_repo, filename_only, branch

def download_file(url, output_dir):
    # Gunakan token dari variabel global
    token = MY_HF_TOKEN

    try:
        repo_id, file_path_in_repo, filename, branch = parse_hf_url(url)
        final_path = os.path.join(output_dir, filename)
        
        # Cek apakah file sudah ada
        if os.path.exists(final_path):
            print(f"⏭️  [SKIP] File sudah ada: {filename}")
            return True

        # Persiapan Folder
        os.makedirs(output_dir, exist_ok=True)
        temp_dir = os.path.join(output_dir, ".temp_hf") 
        
        print(f"{'─'*60}")
        print(f"⬇️  SEDANG MENDOWNLOAD...")
        print(f"📦 File   : {filename}")
        print(f"🔗 Repo   : {repo_id}")
        print(f"📂 Tujuan : {output_dir}")
        print(f"{'─'*60}")

        start_time = time.time()

        # Download Process (ke folder temp)
        downloaded_file_path = hf_hub_download(
            repo_id=repo_id,
            filename=file_path_in_repo,
            revision=branch,
            local_dir=temp_dir,
            local_dir_use_symlinks=False,
            token=token  # Token diambil dari variabel hardcoded
        )

        # Pindahkan file ke lokasi final
        shutil.move(downloaded_file_path, final_path)

        # Bersihkan Temp
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        duration = time.time() - start_time
        print(f"✅ [SELESAI] {filename} berhasil didownload!")
        print(f"⏱️  Waktu  : {duration:.2f} detik")
        print(f"{'='*60}\n")
        return True

    except Exception as e:
        print(f"❌ [GAGAL] Terjadi kesalahan saat mendownload {url}.")
        print(f"   Error: {str(e)}\n")
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

# ============================================================================
# 4. MAIN EXECUTION (CLI)
# ============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="HF Downloader Hardcoded Token")
    parser.add_argument("--url", type=str, required=True, help="Full URL file HF")
    parser.add_argument("--dir", type=str, required=True, help="Folder tujuan")

    args = parser.parse_args()

    # Jalankan download
    download_file(args.url, args.dir)

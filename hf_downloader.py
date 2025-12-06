import os
import sys
import shutil
import argparse
import subprocess
import time

# ============================================================================
# 1. DEPENDENCY CHECK & SETUP
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
# 2. CORE FUNCTIONS
# ============================================================================

def parse_hf_url(url):
    """
    Mengurai URL Hugging Face menjadi Repo ID, Filename, dan Branch.
    Support format: /resolve/branch/file atau /blob/branch/file
    """
    clean_url = url.replace("https://huggingface.co/", "")
    
    # Deteksi pemisah (resolve atau blob)
    if "/resolve/" in clean_url:
        splitter = "/resolve/"
    elif "/blob/" in clean_url:
        splitter = "/blob/"
    else:
        raise ValueError("URL tidak valid. Harus mengandung '/resolve/' atau '/blob/'.")

    parts = clean_url.split(splitter)
    repo_id = parts[0]
    remainder = parts[1] # isinya: branch/path/to/file.ext

    # Ambil branch (biasanya kata pertama setelah splitter)
    # Contoh remainder: "main/folder/file.safetensors" -> branch="main", file="folder/file.safetensors"
    if "/" in remainder:
        branch, file_path_in_repo = remainder.split("/", 1)
    else:
        # Kasus jarang: file ada di root branch tanpa folder
        branch = remainder
        file_path_in_repo = remainder 

    filename_only = file_path_in_repo.split("/")[-1]
    
    return repo_id, file_path_in_repo, filename_only, branch

def download_file(url, output_dir, token=None):
    try:
        # 1. Parsing URL
        repo_id, file_path_in_repo, filename, branch = parse_hf_url(url)
        
        final_path = os.path.join(output_dir, filename)
        
        # 2. Cek apakah file sudah ada
        if os.path.exists(final_path):
            print(f"⏭️  [SKIP] File sudah ada: {filename}")
            return True

        # 3. Persiapan Folder
        os.makedirs(output_dir, exist_ok=True)
        # Gunakan folder temp di dalam folder tujuan agar proses move cepat (satu partisi)
        temp_dir = os.path.join(output_dir, ".temp_hf") 
        
        print(f"{'─'*60}")
        print(f"⬇️  SEDANG MENDOWNLOAD...")
        print(f"📦 File   : {filename}")
        print(f"🔗 Repo   : {repo_id}")
        print(f"📂 Tujuan : {output_dir}")
        print(f"{'─'*60}")

        start_time = time.time()

        # 4. Download Process (ke folder temp)
        downloaded_file_path = hf_hub_download(
            repo_id=repo_id,
            filename=file_path_in_repo,
            revision=branch,
            local_dir=temp_dir,
            local_dir_use_symlinks=False, # Force file fisik
            token=token
        )

        # 5. Pindahkan file dari struktur folder temp ke root folder tujuan
        # hf_hub_download biasanya membuat struktur folder repo di dalam temp
        # Kita perlu memindahkan file aslinya ke output_dir/filename
        
        # Cari file yang baru didownload di dalam temp_dir (karena strukturnya bisa dalam)
        # Tapi karena kita tahu path pastinya dari return value:
        shutil.move(downloaded_file_path, final_path)

        # 6. Bersihkan Temp
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        duration = time.time() - start_time
        print(f"✅ [SELESAI] {filename} berhasil didownload!")
        print(f"⏱️  Waktu  : {duration:.2f} detik")
        print(f"{'='*60}\n")
        return True

    except Exception as e:
        print(f"❌ [GAGAL] Terjadi kesalahan saat mendownload.")
        print(f"   Error: {str(e)}\n")
        # Bersihkan temp jika gagal
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

# ============================================================================
# 3. MAIN EXECUTION (CLI)
# ============================================================================
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Hugging Face High-Speed Downloader")
    
    # Argumen Wajib
    parser.add_argument("--url", type=str, required=True, help="Full URL file dari Hugging Face")
    parser.add_argument("--dir", type=str, required=True, help="Folder tujuan penyimpanan")
    
    # Argumen Opsional (Token)
    parser.add_argument("--token", type=str, default=None, help="HF Token (opsional, bisa juga via env var HF_TOKEN)")

    args = parser.parse_args()

    # Cek Token: Prioritas Args > Env Var
    final_token = args.token if args.token else os.getenv("HF_TOKEN")

    # Jalankan
    download_file(args.url, args.dir, final_token)

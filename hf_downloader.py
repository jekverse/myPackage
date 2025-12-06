import sys
import subprocess
import os
import shutil
import argparse
import warnings

# ============================================================================
# 1. AUTO-INSTALL DEPENDENCIES
# ============================================================================
def install_package(package):
    print(f"📦 Installing missing package: {package}...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installed successfully.")
    except subprocess.CalledProcessError:
        print(f"❌ Failed to install {package}. Please install it manually.")
        sys.exit(1)

def ensure_dependencies():
    """Memastikan paket yang diperlukan sudah terinstall sebelum import"""
    required_packages = {
        "huggingface_hub": "huggingface_hub",
        "hf_transfer": "hf_transfer" # Penting untuk kecepatan download maksimal
    }
    
    import importlib.util
    for import_name, install_name in required_packages.items():
        if importlib.util.find_spec(import_name) is None:
            install_package(install_name)

# Jalankan pengecekan dependency
ensure_dependencies()

# ============================================================================
# IMPORTS SETELAH DEPENDENCY CHECK
# ============================================================================
try:
    from huggingface_hub import hf_hub_download
except ImportError:
    # Fallback double check jika import gagal meski sudah diinstall
    print("🔄 Reloading dependencies...")
    from huggingface_hub import hf_hub_download

# Aktifkan HF Transfer untuk kecepatan maksimal (Rust based)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# ============================================================================
# DEFINISI DIREKTORI OUTPUT (PRESET)
# ============================================================================
PRESET_DIRS = {
    "diffusion": "/root/ComfyUI/models/diffusion_models",
    "vae": "/root/workspace/ComfyUI/models/vae",
    "text_encoder": "/root/ComfyUI/models/text_encoders",
    "lora": "/root/ComfyUI/models/loras",
    "checkpoint": "/root/ComfyUI/models/checkpoints",
    "clip": "/root/ComfyUI/models/clip",
    "clip_vision": "/root/ComfyUI/models/clip_vision",
    "unet": "/root/ComfyUI/models/unet",
    "controlnet": "/root/ComfyUI/models/controlnet",
}

# ============================================================================
# DOWNLOAD FUNCTION
# ============================================================================
def download_url(url, output_dir):
    """Download file dari URL dengan hf_transfer"""
    
    # Ekstrak filename dari URL (mengambil bagian terakhir)
    filename = url.split('/')[-1]
    # Membersihkan query parameters jika ada (misal ?download=true)
    if '?' in filename:
        filename = filename.split('?')[0]
        
    final_path = os.path.join(output_dir, filename)
    
    # Skip jika sudah ada
    if os.path.exists(final_path):
        print(f"⏭️  Skipping: {filename} (already exists)")
        return True
    
    # Buat direktori jika belum ada
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n{'='*80}")
    print(f"📥 Downloading: {filename}")
    print(f"   → {final_path}")
    print(f"{'='*80}")
    
    try:
        # Parse URL
        # Support format: https://huggingface.co/Repo/ID/resolve/main/Path/To/File
        if "huggingface.co" not in url:
            raise ValueError("URL must be from huggingface.co")
            
        clean_url = url.replace("https://huggingface.co/", "")
        
        # Logika split untuk mendapatkan Repo ID dan File Path
        # Kita asumsikan format standar /resolve/{branch}/
        if "/resolve/" in clean_url:
            parts = clean_url.split("/resolve/")
            repo_id = parts[0]
            # Mengambil path setelah branch (misal 'main/')
            remainder = parts[1].split("/", 1)
            if len(remainder) < 2:
                 raise ValueError("Cannot parse file path from URL")
            file_path = remainder[1] # Path file di dalam repo
        else:
             # Fallback parsing kasar jika URL formatnya tidak standar resolve
             parts = clean_url.split("/")
             repo_id = "/".join(parts[:2])
             file_path = "/".join(parts[2:]) # Ini mungkin tidak akurat untuk blob, tapi dicoba

        # Download ke temp directory untuk menghindari file corrupt di folder utama
        temp_dir = os.path.join(output_dir, ".temp_download")
        os.makedirs(temp_dir, exist_ok=True)
        
        print(f"   Repo: {repo_id}")
        print(f"   File: {file_path}")
        
        # --- PERBAIKAN DI SINI ---
        # local_dir_use_symlinks dihapus karena deprecated
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=file_path,
            local_dir=temp_dir,
            # local_dir_use_symlinks=False  <-- DIHAPUS
        )
        
        # Move ke lokasi final
        # Kita harus memastikan direktori tujuan untuk file move tersedia
        # (terutama jika file_path mengandung folder)
        shutil.move(downloaded_path, final_path)
        
        # Cleanup temp
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        print(f"✅ Completed: {filename}\n")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {filename}")
        print(f"   Error: {e}\n")
        # Bersihkan temp jika gagal
        if 'temp_dir' in locals() and os.path.exists(temp_dir):
            shutil.rmtree(temp_dir, ignore_errors=True)
        return False

# ============================================================================
# BATCH DOWNLOAD FUNCTION
# ============================================================================
def download_batch(urls, output_dir):
    """Download multiple URLs"""
    print(f"\n{'='*40}")
    print(f"🚀 BATCH DOWNLOAD: {len(urls)} files")
    print(f"{'='*40}")
    print(f"⚡ Method: hf_transfer (ultra-fast)")
    print(f"📁 Output: {output_dir}")
    print(f"{'='*80}\n")
    
    success = 0
    failed = 0
    
    for i, url in enumerate(urls, 1):
        print(f"[{i}/{len(urls)}]")
        if download_url(url, output_dir):
            success += 1
        else:
            failed += 1
    
    print(f"\n{'='*80}")
    print(f"🎉 COMPLETE! ✅ {success}/{len(urls)} | ❌ {failed}/{len(urls)}")
    print(f"{'='*80}\n")

# ============================================================================
# MAIN CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🚀 Ultra-fast HuggingFace Model Downloader (hf_transfer)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download single file ke preset directory
  python app.py --url "https://huggingface.co/..." --dir diffusion
  
  # Download single file ke custom directory
  python app.py --url "https://huggingface.co/..." --dir /custom/path
  
  # Download multiple files (dari stdin atau file)
  python app.py --batch urls.txt --dir lora
  
  # Download multiple files inline
  python app.py --url "url1" --url "url2" --url "url3" --dir vae
        """
    )
    
    parser.add_argument(
        '--url',
        action='append',
        help='HuggingFace model URL (can be used multiple times)'
    )
    
    parser.add_argument(
        '--batch',
        type=str,
        help='File containing URLs (one per line)'
    )
    
    parser.add_argument(
        '--dir',
        required=True,
        help='Output directory (preset name or custom path)'
    )
    
    parser.add_argument(
        '--list-presets',
        action='store_true',
        help='Show all preset directories'
    )
    
    args = parser.parse_args()
    
    # Show presets
    if args.list_presets:
        print("\n📁 Available Preset Directories:\n")
        for name, path in PRESET_DIRS.items():
            print(f"  {name:<15} → {path}")
        print()
        return
    
    # Determine output directory
    if args.dir in PRESET_DIRS:
        output_dir = PRESET_DIRS[args.dir]
    else:
        output_dir = args.dir
    
    # Collect URLs
    urls = []
    
    if args.url:
        urls.extend(args.url)
    
    if args.batch:
        if not os.path.exists(args.batch):
            print(f"❌ Error: File not found: {args.batch}")
            return
        
        with open(args.batch, 'r') as f:
            batch_urls = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            urls.extend(batch_urls)
    
    if not urls:
        print("❌ Error: No URLs provided. Use --url or --batch")
        parser.print_help()
        return
    
    # Download
    if len(urls) == 1:
        download_url(urls[0], output_dir)
    else:
        download_batch(urls, output_dir)

if __name__ == "__main__":
    main()
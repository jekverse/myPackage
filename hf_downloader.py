import argparse
import os
import shutil
import concurrent.futures
import time
from tqdm import tqdm
from huggingface_hub import hf_hub_download, login

# Aktifkan HF Transfer (Download super cepat berbasis Rust)
os.environ["HF_HUB_ENABLE_HF_TRANSFER"] = "1"

# ============================================================================
# DEFINISI DIREKTORI OUTPUT (PRESET)
# ============================================================================
PRESET_DIRS = {
    "diffusion": "/root/workspace/ComfyUI/models/diffusion_models",
    "vae": "/root/workspace/ComfyUI/models/vae",
    "text_encoder": "/root/workspace/ComfyUI/models/text_encoders",
    "lora": "/root/workspace/ComfyUI/models/loras",
    "checkpoint": "/root/workspace/ComfyUI/models/checkpoints",
    "clip": "/root/workspace/ComfyUI/models/clip",
    "clip_vision": "/root/workspace/ComfyUI/models/clip_vision",
    "unet": "/root/workspace/ComfyUI/models/unet",
    "controlnet": "/root/workspace/ComfyUI/models/controlnet",
}

# ============================================================================
# DOWNLOAD FUNCTION
# ============================================================================
def download_url(url, output_dir, token=None):
    """Download file dari URL dengan hf_transfer"""
    
    # Ekstrak filename dan repo_id dari URL
    try:
        if "/resolve/" in url:
            parts = url.split("/resolve/")
            base_url = parts[0]
            repo_id = base_url.replace("https://huggingface.co/", "")
            
            path_parts = parts[1].split("/", 1)
            revision = path_parts[0]
            file_path = path_parts[1]
            filename = file_path.split("/")[-1]
        else:
            filename = url.split('/')[-1]
            repo_id = None 
            revision = None
            file_path = None
    except Exception:
        filename = url.split('/')[-1]
        repo_id = None

    final_path = os.path.join(output_dir, filename)
    
    # Skip jika file sudah ada
    if os.path.exists(final_path):
        print(f"⏭️  Skipping: {filename} (already exists)")
        return True
    
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📥 Downloading: {filename}")
    
    try:
        temp_dir = os.path.join(output_dir, ".temp_download")
        os.makedirs(temp_dir, exist_ok=True)
        
        # Token di-handle oleh login() global, tapi kita pass juga ke fungsi
        # sebagai redundancy.
        if repo_id and file_path:
             downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=file_path,
                revision=revision,
                local_dir=temp_dir,
                token=token 
            )
        else:
            parts = url.replace("https://huggingface.co/", "").split("/resolve/main/")
            if len(parts) != 2:
                 raise ValueError(f"Could not parse HF URL: {url}")
            repo_id = parts[0]
            file_path = parts[1]
            
            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=file_path,
                local_dir=temp_dir,
                token=token
            )

        shutil.move(downloaded_path, final_path)
        print(f"✅ Completed: {filename}")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {filename}")
        print(f"   Error: {e}")
        return False

# ============================================================================
# BATCH DOWNLOAD FUNCTION
# ============================================================================
def download_batch(urls, output_dir, max_workers=4, token=None):
    print(f"\n{'='*40}")
    print(f"🚀 BATCH DOWNLOAD: {len(urls)} files")
    print(f"{'='*40}")
    print(f"⚡ Method: hf_transfer (ultra-fast)")
    print(f"🔄 Checkpoint: {output_dir}")
    print(f"🧵 Workers: {max_workers}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    success_count = 0
    failed_count = 0
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_url = {executor.submit(download_url, url, output_dir, token): url for url in urls}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_url), total=len(urls), unit="file", desc="🚀 Total Progress"):
            url = future_to_url[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                print(f"❌ Exception for {url}: {exc}")
                failed_count += 1
    
    elapsed = time.time() - start_time
    
    temp_dir = os.path.join(output_dir, ".temp_download")
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir, ignore_errors=True)

    print(f"\n{'='*80}")
    print(f"🎉 COMPLETE! in {elapsed:.2f}s")
    print(f"✅ Success: {success_count} | ❌ Failed: {failed_count}")
    print(f"{'='*80}\n")

# ============================================================================
# MAIN CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🚀 Ultra-fast HuggingFace Model Downloader (hf_transfer + Parallel)"
    )
    
    parser.add_argument('--url', action='append')
    parser.add_argument('--batch', type=str)
    parser.add_argument('--dir', required=True)
    parser.add_argument('--list-presets', action='store_true')
    parser.add_argument('--jobs', '-j', type=int, default=4)
    parser.add_argument('--token', type=str, default=os.environ.get("HF_TOKEN"))
    
    args = parser.parse_args()

    # =========================================================
    # AUTHENTICATION FIX
    # =========================================================
    if args.token:
        # Gunakan fungsi login resmi. Ini akan menulis token ke cache
        # yang dibaca oleh modul hf_transfer (Rust)
        try:
            print(f"🔐 Authenticating with Hugging Face Hub...")
            login(token=args.token, add_to_git_credential=False)
            os.environ["HF_TOKEN"] = args.token # Set env var juga untuk double safety
            
            masked_token = f"*******{args.token[-5:]}" if len(args.token) > 5 else "Set"
            print(f"✅ Auth Success ({masked_token})")
        except Exception as e:
            print(f"⚠️ Auth Warning: {e}")
    else:
        print("⚪ HF Token: ❌ Not detected (Public models only)")
    
    if args.list_presets:
        print("\n📁 Available Preset Directories:\n")
        for name, path in PRESET_DIRS.items():
            print(f"  {name:<15} → {path}")
        return
    
    if args.dir in PRESET_DIRS:
        output_dir = PRESET_DIRS[args.dir]
    else:
        output_dir = args.dir
    
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
        print("❌ Error: No URLs provided.")
        return
    
    if len(urls) == 1:
        download_url(urls[0], output_dir, args.token)
    else:
        download_batch(urls, output_dir, max_workers=args.jobs, token=args.token)

if __name__ == "__main__":
    main()
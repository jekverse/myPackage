import argparse
import os
import shutil
import concurrent.futures
import time
from tqdm import tqdm
from huggingface_hub import hf_hub_download

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
    
    # Ekstrak filename dari URL
    # Handle URL format: https://huggingface.co/repo/id/resolve/main/folder/file.ext
    try:
        if "/resolve/" in url:
            parts = url.split("/resolve/")
            base_url = parts[0]
            repo_id = base_url.replace("https://huggingface.co/", "")
            
            # parts[1] is "main/folder/file.ext" or "branch/folder/file.ext"
            # We need to separate revision (branch) from filepath
            path_parts = parts[1].split("/", 1)
            revision = path_parts[0]
            file_path = path_parts[1]
            filename = file_path.split("/")[-1] # Only keep the filename, flatten structure
        else:
             # Fallback for simple URLs or blob URLs if user makes mistake, though resolve is standard
            filename = url.split('/')[-1]
            repo_id = None # Cannot determine easily without standard format
            revision = None
            file_path = None
    except Exception:
        filename = url.split('/')[-1]
        repo_id = None

    final_path = os.path.join(output_dir, filename)
    
    # Skip jika sudah ada
    if os.path.exists(final_path):
        print(f"⏭️  Skipping: {filename} (already exists)")
        return True
    
    # Buat direktori jika belum ada
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"📥 Downloading: {filename}")
    
    try:
        # Download ke temp directory
        temp_dir = os.path.join(output_dir, ".temp_download")
        os.makedirs(temp_dir, exist_ok=True)
        
        if repo_id and file_path:
             downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=file_path,
                revision=revision,
                local_dir=temp_dir,
                token=token 
            )
        else:
            # Fallback parsing strategy if regex/split above failed or non-standard URL
             # Re-parse strictly for main branch if simple logic applied
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

        # Move ke lokasi final
        shutil.move(downloaded_path, final_path)
        
        # Cleanup temp (file specific, don't remove whole dir as other threads might use it)
        # However, hf_hub_download with local_dir might structure things differently. 
        # But since we move the file immediately, it should be fine.
        # Ideally we clean up empty dirs in temp later.
        
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
    """Download multiple URLs in parallel"""
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
        # Map futures to URLs
        future_to_url = {executor.submit(download_url, url, output_dir, token): url for url in urls}
        
        for future in tqdm(concurrent.futures.as_completed(future_to_url), total=len(urls), unit="file", desc="🚀 Total Progress", disable=False):
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
    
    # Cleanup temp dir root if exists
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
        description="🚀 Ultra-fast HuggingFace Model Downloader (hf_transfer + Parallel)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download single file
  python app.py --url "https://huggingface.co/..." --dir diffusion
  
  # Download multiple files parallel
  python app.py --batch urls.txt --dir lora --jobs 8
  
  # Authenticated download
  python app.py --url "..." --dir vae --token "hf_..."
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
    
    parser.add_argument(
        '--jobs', '-j',
        type=int,
        default=4,
        help='Number of parallel downloads (default: 4)'
    )
    
    parser.add_argument(
        '--token',
        type=str,
        default=os.environ.get("HF_TOKEN"),
        help='HuggingFace Token (optional, defaults to HF_TOKEN env var)'
    )
    
    args = parser.parse_args()

    # Token Info
    if args.token:
        masked_token = f"*******{args.token[-5:]}" if len(args.token) > 5 else "Set"
        print(f"🔑 HF Token: ✅ Detected ({masked_token})")
    else:
        print("⚪ HF Token: ❌ Not detected (Public models only)")
    
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
        # Single file, just run directly
        download_url(urls[0], output_dir, args.token)
    else:
        # Multiple files, use batch with thread pool
        download_batch(urls, output_dir, max_workers=args.jobs, token=args.token)

if __name__ == "__main__":
    main()

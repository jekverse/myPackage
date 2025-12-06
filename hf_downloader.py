import argparse
import os
import shutil
from huggingface_hub import hf_hub_download

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
    
    # Ekstrak filename dari URL
    filename = url.split('/')[-1]
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
        parts = url.replace("https://huggingface.co/", "").split("/resolve/main/")
        if len(parts) != 2:
            raise ValueError("Invalid HuggingFace URL format")
        
        repo_id = parts[0]
        file_path = parts[1]
        
        # Download ke temp directory
        temp_dir = os.path.join(output_dir, ".temp_download")
        os.makedirs(temp_dir, exist_ok=True)
        
        downloaded_path = hf_hub_download(
            repo_id=repo_id,
            filename=file_path,
            local_dir=temp_dir,
            local_dir_use_symlinks=False
        )
        
        # Move ke lokasi final
        shutil.move(downloaded_path, final_path)
        
        # Cleanup temp
        shutil.rmtree(temp_dir, ignore_errors=True)
        
        print(f"✅ Completed: {filename}\n")
        return True
        
    except Exception as e:
        print(f"❌ Failed: {filename}")
        print(f"   Error: {e}\n")
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

Preset Directories:
  diffusion     → /root/workspace/ComfyUI/models/diffusion_models
  vae           → /root/workspace/ComfyUI/models/vae
  text_encoder  → /root/workspace/ComfyUI/models/text_encoders
  lora          → /root/workspace/ComfyUI/models/loras
  checkpoint    → /root/workspace/ComfyUI/models/checkpoints
  clip          → /root/workspace/ComfyUI/models/clip
  clip_vision   → /root/workspace/ComfyUI/models/clip_vision
  unet          → /root/workspace/ComfyUI/models/unet
  controlnet    → /root/workspace/ComfyUI/models/controlnet
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

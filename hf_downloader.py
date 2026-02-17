import argparse
import os
import shutil
import concurrent.futures
import time
from tqdm import tqdm
from huggingface_hub import hf_hub_download, login

# Aktifkan HF Xet High Performance (Pengganti deprecated HF Transfer)
os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"

# ============================================================================
# DEFINISI DIREKTORI OUTPUT (PRESET)
# ============================================================================
PRESET_DIRS = {
    "diffusion": "/root/ComfyUI/models/diffusion_models",
    "vae": "/root/ComfyUI/models/vae",
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
def download_url(url, output_dir, token=None):
    """Download file dari URL dengan hf-xet (High Performance)"""
    
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
def download_batch(tasks, max_workers=4, token=None):
    """
    Download multiple URLs in parallel
    tasks: list of dictionaries {'url': url, 'dir': output_dir}
    """
    print(f"\n{'='*40}")
    print(f"🚀 BATCH DOWNLOAD: {len(tasks)} files")
    print(f"{'='*40}")
    print(f"⚡ Method: hf-xet (High Performance)")
    print(f"🧵 Workers: {max_workers}")
    print(f"{'='*80}\n")
    
    start_time = time.time()
    success_count = 0
    failed_count = 0
    
    # Track temporary directories to clean up later
    temp_dirs = set()

    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit tasks
        future_to_info = {}
        for task in tasks:
            url = task['url']
            out_dir = task['dir']
            temp_dirs.add(os.path.join(out_dir, ".temp_download"))
            future = executor.submit(download_url, url, out_dir, token)
            future_to_info[future] = url

        for future in tqdm(concurrent.futures.as_completed(future_to_info), total=len(tasks), unit="file", desc="🚀 Total Progress"):
            url = future_to_info[future]
            try:
                if future.result():
                    success_count += 1
                else:
                    failed_count += 1
            except Exception as exc:
                print(f"❌ Exception for {url}: {exc}")
                failed_count += 1
    
    elapsed = time.time() - start_time
    
    # Cleanup temp dirs found
    for t_dir in temp_dirs:
        if os.path.exists(t_dir):
            shutil.rmtree(t_dir, ignore_errors=True)

    print(f"\n{'='*80}")
    print(f"🎉 COMPLETE! in {elapsed:.2f}s")
    print(f"✅ Success: {success_count} | ❌ Failed: {failed_count}")
    print(f"{'='*80}\n")

    


# ============================================================================
# MAIN CLI
# ============================================================================
def main():
    parser = argparse.ArgumentParser(
        description="🚀 Ultra-fast HuggingFace Model Downloader (hf-xet + Parallel)"
    )
    
    parser.add_argument('--url', action='append')
    parser.add_argument('--batch', type=str)
    parser.add_argument('--dir', required=False, help='Output directory (required unless using JSON batch with explicit dirs)')
    parser.add_argument('--list-presets', action='store_true')
    parser.add_argument('--jobs', '-j', type=int, default=4)
    parser.add_argument('--token', type=str, default=os.environ.get("HF_TOKEN"))
    
    args = parser.parse_args()

    # =========================================================
    # AUTHENTICATION FIX
    # =========================================================
    if args.token:
        # Gunakan fungsi login resmi. Ini akan menulis token ke cache
        # yang dibaca oleh modul hf-xet
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
    
    # --- Prepare Tasks ---
    tasks = []
    
    # 1. Handle JSON Batch (supports custom dirs per file)
    if args.batch and args.batch.endswith('.json'):
        import json
        if not os.path.exists(args.batch):
            print(f"❌ Error: File not found: {args.batch}")
            return
        
        try:
            with open(args.batch, 'r') as f:
                data = json.load(f)
                
            for item in data:
                # Resolve directory: item 'directory' or 'dir' > args.dir (global fallback)
                # item directory can be absolute OR a preset name
                d = item.get('directory') or item.get('dir')
                u = item.get('url')
                
                if not u:
                    continue
                    
                # If no per-item dir, use global --dir. If that's missing too, error for this item?
                # For mixed usage, we expect --dir if JSON doesn't strictly specify it.
                target_dir = None
                
                if d:
                   target_dir = PRESET_DIRS.get(d, d) # Check preset map, else treat as path
                elif args.dir:
                   target_dir = PRESET_DIRS.get(args.dir, args.dir)
                   
                if target_dir:
                    tasks.append({'url': u, 'dir': target_dir})
                else:
                    print(f"⚠️ Skipping URL without directory: {u}")
                    
        except Exception as e:
            print(f"❌ Error reading JSON batch: {e}")
            return

    # 2. Handle Text Batch (uses global --dir)
    elif args.batch:
        if not args.dir:
            print("❌ Error: --dir is required for text batch files")
            return
            
        output_dir = PRESET_DIRS.get(args.dir, args.dir)
        if not os.path.exists(args.batch):
            print(f"❌ Error: File not found: {args.batch}")
            return
        
        with open(args.batch, 'r') as f:
            lines = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            for u in lines:
                tasks.append({'url': u, 'dir': output_dir})

    # 3. Handle CLI URLs (uses global --dir)
    if args.url:
        if not args.dir and not tasks:
             # Only strictly require global dir if we rely on it. 
             # But usually CLI usage implies global dir.
             pass 
             
        # Fallback to global dir if available
        if args.dir:
            output_dir = PRESET_DIRS.get(args.dir, args.dir)
            for u in args.url:
                tasks.append({'url': u, 'dir': output_dir})
        elif not tasks:
            print("❌ Error: --dir is required for --url arguments")
            return

    if not tasks:
        print("❌ Error: No valid download tasks found.")
        return
    
    # Execute
    if len(tasks) == 1:
        download_url(tasks[0]['url'], tasks[0]['dir'], args.token)
    else:
        # Note: 'output_dir' param in batch is now removed/irrelevant, handled per task
        download_batch(tasks, max_workers=args.jobs, token=args.token)

if __name__ == "__main__":
    main()
import shutil
import os

def install_config():
    src = "extra_model_paths.yaml"
    dst = "/root/ComfyUI/extra_model_paths.yaml"
    
    print(f"Copying {src} to {dst}...")

    # Check if destination directory exists
    if not os.path.exists(os.path.dirname(dst)):
        print(f"⚠️ Warning: Destination directory {os.path.dirname(dst)} not found!")
    
    try:
        shutil.copy(src, dst)
        print("✅ Configuration installed successfully!")
    except Exception as e:
        print(f"❌ Error installing config: {e}")

if __name__ == "__main__":
    install_config()

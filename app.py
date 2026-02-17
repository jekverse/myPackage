import shutil
import os

def _decrypt_token(encrypted_hex, key):
    # Simple XOR decryption
    encrypted = bytes.fromhex(encrypted_hex).decode('latin1')
    return "".join(chr(ord(c) ^ ord(k)) for c, k in zip(encrypted, key * (len(encrypted) // len(key) + 1)))

def setup_environment():
    # Encrypted HF token (XOR with key 'modal-deploy-key')
    encrypted_token = "05093b152b5d1e2718352e1274022f030f202b050655273518013d3a47320d34022d260425"
    key = "modal-deploy-key"
    token = _decrypt_token(encrypted_token, key)
    
    env_vars = {
        "HF_TOKEN": token,
        "HF_XET_HIGH_PERFORMANCE": "1"
    }
    bashrc_path = os.path.expanduser("~/.bashrc")
    
    try:
        current_content = ""
        if os.path.exists(bashrc_path):
            with open(bashrc_path, "r") as f:
                current_content = f.read()
        
        with open(bashrc_path, "a") as f:
            for key, value in env_vars.items():
                command = f'export {key}="{value}"'
                if command not in current_content:
                    f.write(f"\n{command}\n")
                    print(f"✅ Added {key} to {bashrc_path}")
                else:
                    print(f"ℹ️ {key} already present in {bashrc_path}")
            
    except Exception as e:
        print(f"❌ Error setting environment variables: {e}")

def install_config():
    src = "extra_model_paths.yaml"
    dst = "/root/ComfyUI/extra_model_paths.yaml"
    
    print(f"Copying {src} to {dst}...")
    
    if not os.path.exists("/root/ComfyUI"):
        print("⚠️ Warning: /root/ComfyUI directory not found! Is ComfyUI installed?")
        # Create directory if needed? Or just fail? 
        # Usually running this means ComfyUI should be there.
    
    try:
        shutil.copy(src, dst)
        print("✅ Configuration installed successfully!")
    except Exception as e:
        print(f"❌ Error installing config: {e}")

if __name__ == "__main__":
    setup_environment()
    install_config()

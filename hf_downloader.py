import os
import re
import sys
import time
import shutil
import subprocess
import platform
import requests
from pathlib import Path
from urllib.parse import urlparse, unquote
from datetime import datetime

# =============================================
# CONFIGURATION
# =============================================

# Hugging Face Configuration
HF_TOKEN = ""
HF_USERNAME = ""

# CivitAI Configuration
CIVITAI_TOKEN = ""

class UniversalDownloader:
    def __init__(self):
        self.start_time = None
        self.system = platform.system()
        self.aria2_installed = False
        self.hf_packages_installed = False

    # =============================================
    # UTILITY FUNCTIONS
    # =============================================

    def log_message(self, message, level="INFO"):
        """Log pesan dengan timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] [{level}] {message}")

    def format_bytes(self, bytes_size):
        """Format bytes ke human readable format"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_size < 1024.0:
                return f"{bytes_size:.2f} {unit}"
            bytes_size /= 1024.0
        return f"{bytes_size:.2f} PB"

    def format_time(self, seconds):
        """Format seconds ke readable time"""
        if seconds < 60:
            return f"{int(seconds)}s"
        elif seconds < 3600:
            mins = int(seconds / 60)
            secs = int(seconds % 60)
            return f"{mins}m {secs}s"
        else:
            hours = int(seconds / 3600)
            mins = int((seconds % 3600) / 60)
            return f"{hours}h {mins}m"

    # =============================================
    # PLATFORM DETECTION
    # =============================================

    def detect_platform(self, url):
        """Deteksi platform dari URL"""
        url_lower = url.lower()

        if 'huggingface.co' in url_lower or 'hf.co' in url_lower:
            return 'huggingface'
        elif 'civitai.com' in url_lower:
            return 'civitai'
        else:
            return 'other'

    # =============================================
    # DIRECTORY SELECTION
    # =============================================

    def get_comfyui_directory(self):
        """Pilih direktori ComfyUI dari menu dengan opsi custom"""
        directories = {
            "1": "/root/ComfyUI/models/diffusion_models",
            "2": "/root/ComfyUI/models/text_encoders",
            "3": "/root/ComfyUI/models/loras",
            "4": "/root/ComfyUI/models/vae",
            "5": "/root/ComfyUI/models/clip",
            "6": "/root/ComfyUI/models/clip_vision",
            "7": "/root/ComfyUI/models/checkpoints",
            "8": "/root/ComfyUI/models/audio_encoders",
            "9": "/root/ComfyUI/models/upscale_models",
            "10": "/root/ComfyUI/models/controlnet",
            "11": "/root",
            "12": "custom"
        }

        print("\n📁 Pilih direktori tujuan:")
        print("   1.  Diffusion Models (/root/ComfyUI/models/diffusion_models)")
        print("   2.  Text Encoders (/root/ComfyUI/models/text_encoders)")
        print("   3.  LoRAs (/root/ComfyUI/models/loras)")
        print("   4.  VAE (/root/ComfyUI/models/vae)")
        print("   5.  CLIP (/root/ComfyUI/models/clip)")
        print("   6.  CLIP Vision (/root/ComfyUI/models/clip_vision)")
        print("   7.  Checkpoints (/root/ComfyUI/models/checkpoints)")
        print("   8.  Audio Encoders (/root/ComfyUI/models/audio_encoders)")
        print("   9.  Upscale Models (/root/ComfyUI/models/upscale_models)")
        print("   10. ControlNet (/root/ComfyUI/models/controlnet)")
        print("   11. Root Directory (/root)")
        print("   12. Custom Directory (input manual)")

        while True:
            choice = input("\nPilih direktori (1-12): ").strip()

            if choice in directories:
                if choice == "12":
                    # Input manual untuk direktori custom
                    while True:
                        custom_dir = input("📝 Masukkan path direktori custom: ").strip()
                        if custom_dir:
                            # Ekspansi path relatif dan home directory
                            custom_dir = os.path.expanduser(custom_dir)
                            custom_dir = os.path.abspath(custom_dir)

                            # Konfirmasi direktori
                            print(f"📁 Direktori yang dipilih: {custom_dir}")
                            if not os.path.exists(custom_dir):
                                create_dir = input("📁 Direktori tidak ada. Buat otomatis? (y/n): ").strip().lower()
                                if create_dir == 'y':
                                    try:
                                        os.makedirs(custom_dir, exist_ok=True)
                                        print(f"✅ Direktori berhasil dibuat: {custom_dir}")
                                        return custom_dir
                                    except Exception as e:
                                        print(f"❌ Gagal membuat direktori: {e}")
                                        continue
                                else:
                                    continue
                            else:
                                return custom_dir
                        else:
                            print("❌ Direktori tidak boleh kosong!")
                else:
                    return directories[choice]
            else:
                print("❌ Pilihan tidak valid! Masukkan angka 1-12.")

    # =============================================
    # PACKAGE INSTALLATION
    # =============================================

    def install_packages(self):
        """Install packages yang diperlukan untuk Hugging Face"""
        required_packages = {
            'hf_xet': 'hf_xet',
            'huggingface_hub': 'huggingface_hub',
            'tqdm': 'tqdm',
            'requests': 'requests'
        }

        missing_packages = []

        print("🔍 Memeriksa dependencies Hugging Face...")

        for package_name, import_name in required_packages.items():
            try:
                __import__(import_name)
                print(f"✅ {package_name} sudah terinstall")
            except ImportError:
                print(f"❌ {package_name} belum terinstall")
                missing_packages.append(package_name)

        if missing_packages:
            print(f"\n📦 Menginstall {len(missing_packages)} package yang missing...")

            for package in missing_packages:
                print(f"⏳ Installing {package}...")
                try:
                    subprocess.check_call([sys.executable, "-m", "pip", "install", package, "-q"])
                    print(f"✅ {package} berhasil diinstall")
                except subprocess.CalledProcessError as e:
                    print(f"❌ Error installing {package}: {e}")
                    return False
        else:
            print("🎉 Semua dependencies Hugging Face sudah tersedia!")

        self.hf_packages_installed = True
        return True

    def check_aria2_installed(self):
        """Check if aria2 is installed"""
        try:
            subprocess.run(['aria2c', '--version'], capture_output=True, check=True)
            print("✅ aria2 sudah terinstall")
            self.aria2_installed = True
            return True
        except (subprocess.CalledProcessError, FileNotFoundError):
            print("❌ aria2 belum terinstall")
            self.aria2_installed = False
            return False

    def install_aria2(self):
        """Install aria2 berdasarkan OS"""
        if self.aria2_installed:
            return True

        print("📦 Menginstall aria2...")

        # Installation commands berdasarkan OS
        install_commands = {
            'Linux': [
                "sudo apt update && sudo apt install -y aria2",
                "sudo yum install -y aria2",
                "sudo dnf install -y aria2",
                "sudo pacman -S --noconfirm aria2",
                "sudo zypper install -y aria2"
            ],
            'Darwin': [  # macOS
                "brew install aria2",
                "/bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\" && brew install aria2"
            ],
            'Windows': [
                "winget install aria2.aria2",
                "choco install aria2",
                "scoop install aria2"
            ]
        }

        if self.system not in install_commands:
            print(f"❌ OS {self.system} tidak didukung untuk auto-install")
            self._show_manual_installation()
            return False

        commands = install_commands[self.system]

        for i, cmd in enumerate(commands, 1):
            try:
                print(f"🔄 Mencoba metode {i}/{len(commands)}: {cmd.split()[0]}...")

                if self.system == 'Windows':
                    result = subprocess.run(
                        ['powershell', '-Command', cmd],
                        capture_output=True,
                        text=True,
                        timeout=300
                    )
                else:
                    result = subprocess.run(
                        cmd,
                        shell=True,
                        capture_output=True,
                        text=True,
                        timeout=300
                    )

                if result.returncode == 0:
                    print(f"✅ aria2 berhasil diinstall dengan {cmd.split()[0]}!")
                    if self.check_aria2_installed():
                        return True

                print(f"⚠️ Metode {i} gagal, mencoba metode berikutnya...")

            except subprocess.TimeoutExpired:
                print(f"⏰ Timeout pada metode {i}, mencoba metode berikutnya...")
                continue
            except Exception as e:
                print(f"❌ Error pada metode {i}: {e}")
                continue

        # Jika semua metode auto-install gagal
        print("\n❌ Auto-installation gagal. Silakan install aria2 secara manual:")
        self._show_manual_installation()
        return False

    def _show_manual_installation(self):
        """Tampilkan instruksi manual installation"""
        print("\n📖 INSTRUKSI MANUAL INSTALLATION:")
        print("="*50)

        if self.system == 'Linux':
            print("🐧 LINUX:")
            print("• Ubuntu/Debian: sudo apt install aria2")
            print("• CentOS/RHEL:   sudo yum install aria2")
            print("• Fedora:        sudo dnf install aria2")
            print("• Arch Linux:    sudo pacman -S aria2")
            print("• openSUSE:      sudo zypper install aria2")

        elif self.system == 'Darwin':
            print("🍎 macOS:")
            print("1. Install Homebrew terlebih dahulu:")
            print("   /bin/bash -c \"$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)\"")
            print("2. Install aria2:")
            print("   brew install aria2")
            print("\nAlternatif: Download dari https://github.com/aria2/aria2/releases")

        elif self.system == 'Windows':
            print("🪟 WINDOWS:")
            print("1. Chocolatey: choco install aria2")
            print("2. Scoop:      scoop install aria2")
            print("3. Winget:     winget install aria2.aria2")
            print("4. Manual:     Download dari https://github.com/aria2/aria2/releases")

        print("="*50)

    def setup_dependencies(self, platform):
        """Setup dependencies berdasarkan platform yang terdeteksi"""
        if platform == 'huggingface':
            return self.install_packages()
        elif platform == 'civitai' or platform == 'other':
            if not self.check_aria2_installed():
                install_choice = input("\n📥 aria2 belum terinstall. Install otomatis? (y/n): ")
                if install_choice.lower() == 'y':
                    return self.install_aria2()
                else:
                    print("❌ aria2 diperlukan untuk menjalankan download.")
                    self._show_manual_installation()
                    return False
            return True
        return True

    # =============================================
    # HUGGING FACE DOWNLOADER
    # =============================================

    def setup_hf_xet(self):
        """Setup hf_xet dan login"""
        print("🚀 Mengaktifkan hf_xet untuk kecepatan maksimal...")
        os.environ["HF_XET_HIGH_PERFORMANCE"] = "1"

        try:
            from huggingface_hub import login
            print(f"🔐 Login sebagai: {HF_USERNAME}")
            login(token=HF_TOKEN, add_to_git_credential=True)
            print("✅ Login berhasil!")
        except Exception as e:
            print(f"⚠️  Warning login: {e}")
            print("🔄 Melanjutkan tanpa authentication...")

    def parse_hf_url(self, url):
        """Parse URL Hugging Face untuk extract repo_id dan filename"""
        # Pattern: https://huggingface.co/{repo_id}/resolve/main/{filename}
        pattern = r'https://huggingface\.co/([^/]+/[^/]+)/resolve/main/(.+)'
        match = re.match(pattern, url)

        if match:
            repo_id = match.group(1)
            filename = match.group(2)
            return repo_id, filename
        else:
            raise ValueError("URL format tidak valid. Gunakan format: https://huggingface.co/USER/REPO/resolve/main/PATH")

    def download_from_huggingface(self, url, local_dir):
        """Download model dari Hugging Face dengan hf_xet"""
        try:
            from huggingface_hub import hf_hub_download

            # Setup hf_xet
            self.setup_hf_xet()

            # Parse URL untuk mendapatkan repo_id dan filename
            repo_id, filename = self.parse_hf_url(url)

            # Ekstrak nama file untuk display
            file_name = os.path.basename(filename)

            # Pastikan direktori ada
            os.makedirs(local_dir, exist_ok=True)

            self.log_message(f"📥 Parsing URL berhasil!")
            self.log_message(f"🏷️  Repo: {repo_id}")
            self.log_message(f"📄 File: {file_name}")
            self.log_message(f"📁 Tujuan: {local_dir}")

            start_time = time.time()

            # Download dengan hf_xet
            self.log_message("🚀 Memulai download dengan hf_xet...")

            downloaded_path = hf_hub_download(
                repo_id=repo_id,
                filename=filename,
                token=HF_TOKEN,
                resume_download=True
            )

            # Pindah file ke direktori yang diinginkan dengan nama flat
            final_filename = os.path.basename(filename)
            final_path = os.path.join(local_dir, final_filename)

            # Pastikan direktori tujuan ada
            os.makedirs(local_dir, exist_ok=True)

            # Copy file ke lokasi final
            shutil.copy2(downloaded_path, final_path)
            downloaded_path = final_path

            self.log_message(f"📁 File disimpan dengan struktur flat: {final_filename}")

            end_time = time.time()
            download_time = end_time - start_time

            # Verifikasi dan log hasil
            if os.path.exists(downloaded_path):
                file_size = os.path.getsize(downloaded_path)
                file_size_gb = file_size / (1024**3)
                speed_mbps = (file_size / (1024**2)) / max(download_time, 0.1)

                self.log_message("🎉 DOWNLOAD BERHASIL!", "SUCCESS")
                self.log_message(f"📍 Lokasi: {downloaded_path}")
                self.log_message(f"📏 Ukuran: {file_size_gb:.2f} GB")
                self.log_message(f"⏱️  Waktu: {download_time:.1f} detik")
                self.log_message(f"🚄 Kecepatan: {speed_mbps:.1f} MB/s")

                return True
            else:
                self.log_message("❌ File tidak ditemukan setelah download", "ERROR")
                return False

        except ValueError as e:
            self.log_message(f"❌ URL Error: {str(e)}", "ERROR")
            return False
        except Exception as e:
            self.log_message(f"❌ Download Error: {str(e)}", "ERROR")
            return False

    # =============================================
    # CIVITAI DOWNLOADER
    # =============================================

    def get_civitai_filename(self, url):
        """Ambil nama file dari CivitAI menggunakan API atau header response"""
        try:
            print("🔍 Mendeteksi nama file dari CivitAI...")

            # Method 1: HEAD request untuk ambil Content-Disposition
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'application/octet-stream, */*',
                'Referer': 'https://civitai.com/'
            }

            # Pastikan URL sudah memiliki token
            prepared_url = self.prepare_civitai_url(url)

            response = requests.head(prepared_url, headers=headers, allow_redirects=True, timeout=15)

            # Cek Content-Disposition header
            if 'Content-Disposition' in response.headers:
                content_disp = response.headers['Content-Disposition']
                filename_match = re.search(r'filename\*?=(?:UTF-8\'\')?["\']?([^"\';\r\n]+)', content_disp)
                if filename_match:
                    filename = unquote(filename_match.group(1))
                    print(f"✅ Nama file terdeteksi dari header: {filename}")
                    return filename

            # Method 2: Coba ambil dari API CivitAI jika ada model ID
            model_id = self.extract_civitai_model_id(url)
            if model_id:
                api_filename = self.get_filename_from_civitai_api(model_id)
                if api_filename:
                    print(f"✅ Nama file terdeteksi dari API: {api_filename}")
                    return api_filename

            # Method 3: Parse dari URL
            parsed_url = urlparse(url)
            url_filename = unquote(os.path.basename(parsed_url.path))
            if url_filename and '.' in url_filename:
                print(f"✅ Nama file terdeteksi dari URL: {url_filename}")
                return url_filename

            print("⚠️ Nama file tidak terdeteksi, menggunakan fallback")
            return None

        except Exception as e:
            print(f"⚠️ Error mendeteksi nama file: {e}")
            return None

    def extract_civitai_model_id(self, url):
        """Extract model ID dari URL CivitAI"""
        try:
            patterns = [
                r'civitai\.com/models/(\d+)',
                r'civitai\.com/api/download/models/(\d+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, url)
                if match:
                    return match.group(1)
            return None
        except:
            return None

    def get_filename_from_civitai_api(self, model_id):
        """Ambil filename dari CivitAI API"""
        try:
            api_url = f"https://civitai.com/api/v1/models/{model_id}"
            headers = {}
            if CIVITAI_TOKEN:
                headers['Authorization'] = f'Bearer {CIVITAI_TOKEN}'

            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'modelVersions' in data and data['modelVersions']:
                    files = data['modelVersions'][0].get('files', [])
                    if files:
                        return files[0].get('name')
            return None
        except:
            return None

    def prepare_civitai_url(self, url):
        """Prepare URL CivitAI dengan token jika diperlukan"""
        print("🎨 URL CivitAI terdeteksi, memproses authentication...")

        # Jika token sudah ada di URL, gunakan apa adanya
        if 'token=' in url:
            print("✅ Token sudah ada di URL")
            return url

        # Tambahkan token ke URL jika belum ada
        if CIVITAI_TOKEN:
            separator = '&' if '?' in url else '?'
            url_with_token = f"{url}{separator}token={CIVITAI_TOKEN}"
            print("✅ Token authentication ditambahkan ke URL")
            return url_with_token

        return url

    def download_from_civitai(self, url, directory, filename=None):
        """Download dari CivitAI menggunakan aria2"""
        try:
            # Auto-generate filename jika tidak ada
            if filename is None:
                detected_filename = self.get_civitai_filename(url)
                if detected_filename:
                    filename = detected_filename
                else:
                    filename = f"civitai_model_{int(time.time())}.safetensors"

                print(f"📝 Menggunakan filename: {filename}")

            # Full path untuk file
            filepath = os.path.join(directory, filename)

            # Check existing file
            if os.path.exists(filepath):
                file_size = os.path.getsize(filepath)
                print(f"⚠️  File {filename} sudah ada ({self.format_bytes(file_size)})")
                overwrite = input("Timpa file? (y/n): ")
                if overwrite.lower() != 'y':
                    print("❌ Download dibatalkan.")
                    return False

            print(f"\n📥 DOWNLOAD INFO:")
            print(f"🔗 URL: {url}")
            print(f"📁 Direktori: {os.path.abspath(directory)}")
            print(f"📄 Filename: {filename}")
            print(f"🎨 Platform: CivitAI (dengan authentication)")
            print("-" * 60)

            # Pastikan direktori ada
            Path(directory).mkdir(parents=True, exist_ok=True)

            # Prepare URL untuk CivitAI
            prepared_url = self.prepare_civitai_url(url)

            # Headers untuk CivitAI
            headers = [
                '--header=User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                '--header=Accept: application/octet-stream, */*',
                '--header=Referer: https://civitai.com/'
            ]

            # Konfigurasi aria2 untuk kecepatan maksimum
            cmd = [
                'aria2c',
                '--file-allocation=none',
                '--max-connection-per-server=4',
                '--split=4',
                '--min-split-size=1M',
                '--max-concurrent-downloads=1',
                '--continue=true',
                '--allow-overwrite=true',
                '--auto-file-renaming=false',
                '--disable-ipv6=true',
                '--console-log-level=notice',
                '--summary-interval=1',
                '--human-readable=true',
                '--show-console-readout=true',
                '--check-certificate=false',
                '--timeout=60',
                '--retry-wait=5',
                '--max-tries=10',
                '--follow-metalink=mem',
                '--metalink-enable-unique-protocol=false',
                '--dir=' + directory,
                '--out=' + filename,
            ] + headers + [prepared_url]

            # Jalankan aria2c dengan real-time output
            print(f"📁 Menyimpan ke: {filepath}")
            print("🔄 Progress download:\n")

            start_time = time.time()

            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1
            )

            # Parse dan display output real-time
            for line in process.stdout:
                line = line.strip()
                if line:
                    if '[' in line and ']' in line and ('DL:' in line or 'CN:' in line):
                        sys.stdout.write('\r' + line)
                        sys.stdout.flush()
                    elif 'Download complete' in line:
                        print('\n✅ ' + line)
                    elif 'STATUS' in line and 'OK' in line:
                        print('\n✅ Download selesai!')
                    elif 'ERROR' in line or 'WARN' in line:
                        print('\n⚠️  ' + line)
                    elif line.startswith('[') and ('file(s) downloaded' in line):
                        print('\n' + line)

            process.wait()

            if process.returncode == 0 and os.path.exists(filepath):
                end_time = time.time()
                download_time = end_time - start_time
                file_size = os.path.getsize(filepath)

                print(f"\n🎉 DOWNLOAD BERHASIL!")
                print(f"📊 Ukuran file: {self.format_bytes(file_size)}")
                print(f"⏱️  Waktu download: {self.format_time(download_time)}")
                print(f"🚄 Kecepatan rata-rata: {self.format_bytes(file_size/max(download_time, 0.1))}/s")
                print(f"📍 Lokasi file: {os.path.abspath(filepath)}")
                return True
            else:
                print(f"\n❌ DOWNLOAD GAGAL dengan kode: {process.returncode}")
                # Cleanup partial file
                if os.path.exists(filepath):
                    try:
                        os.remove(filepath)
                        print("🗑️  File tidak lengkap telah dihapus")
                    except:
                        pass
                return False

        except Exception as e:
            print(f"\n❌ Error CivitAI download: {str(e)}")
            return False

    # =============================================
    # MAIN DOWNLOAD FUNCTION
    # =============================================

    def download_file(self, url, directory, filename=None):
        """Main download function dengan auto-detection platform"""
        platform = self.detect_platform(url)

        print(f"\n🔍 PLATFORM DETECTION:")
        print(f"🌐 URL: {url}")
        print(f"📊 Platform: {platform.upper()}")

        # Setup dependencies berdasarkan platform
        if not self.setup_dependencies(platform):
            return False

        # Route ke downloader yang sesuai
        if platform == 'huggingface':
            print("🤗 Menggunakan Hugging Face downloader (hf_xet)...")
            return self.download_from_huggingface(url, directory)

        elif platform == 'civitai':
            print("🎨 Menggunakan CivitAI downloader (aria2)...")
            return self.download_from_civitai(url, directory, filename)

        else:
            print("🌐 Menggunakan Generic downloader (aria2)...")
            return self.download_from_civitai(url, directory, filename)  # Use aria2 for other URLs

    # =============================================
    # USER INTERFACE
    # =============================================

    def get_user_input(self):
        """Ambil input URL dan direktori dari user"""
        print("\n" + "="*70)
        print("📥 UNIVERSAL AI MODEL DOWNLOADER")
        print("   Supports: Hugging Face • CivitAI • Other URLs")
        print("="*70)

        # Input URL
        print("📝 Contoh URL yang didukung:")
        print("   🤗 HF: https://huggingface.co/USER/REPO/resolve/main/model.safetensors")
        print("   🎨 CivitAI: https://civitai.com/api/download/models/123456")
        print("   🌐 Other: https://example.com/model.safetensors")

        url = input("\n🔗 Masukkan URL download: ").strip()
        if not url:
            return None, None, None

        # Deteksi platform dan beri info ke user
        platform = self.detect_platform(url)
        print(f"🔍 Platform terdeteksi: {platform.upper()}")

        # Pilih direktori dari menu
        local_dir = self.get_comfyui_directory()

        # Input filename (optional untuk non-HF)
        filename = None
        if platform != 'huggingface':
            if platform == 'civitai':
                print("🎨 CivitAI - nama file akan dideteksi otomatis")
                custom_filename = input("📝 Nama file custom (Enter=auto-detect): ").strip()
            else:
                custom_filename = input("📝 Nama file (Enter=auto dari URL): ").strip()

            if custom_filename:
                filename = custom_filename

        return url, local_dir, filename

def main():
    """Main function untuk interactive download"""

    print("=" * 70)
    print("    🚀 UNIVERSAL AI MODEL DOWNLOADER 🚀")
    print("    Auto-detect: Hugging Face • CivitAI • Generic URLs")
    print("=" * 70)

    downloader = UniversalDownloader()
    download_count = 0

    print("\n🎯 Universal Downloader siap! Tekan Ctrl+C untuk keluar.")

    try:
        while True:
            # Ambil input user
            url, local_dir, filename = downloader.get_user_input()

            # Cek jika user ingin keluar (input kosong)
            if not url:
                print("❌ URL tidak boleh kosong. Coba lagi...")
                continue

            # Download model dengan auto-detection
            success = downloader.download_file(url, local_dir, filename)

            if success:
                download_count += 1
                downloader.log_message(f"📊 Total file berhasil: {download_count}")

            # Tanya apakah ingin melanjutkan
            print("\n" + "-"*50)
            continue_choice = input("🔄 Download file lain? (y/n, Enter=yes): ").strip().lower()
            if continue_choice in ['n', 'no', 'tidak']:
                break

    except KeyboardInterrupt:
        print(f"\n\n🛑 Download dihentikan oleh user.")
        downloader.log_message(f"Selesai! Total download berhasil: {download_count}")
    except Exception as e:
        downloader.log_message(f"Error tidak terduga: {str(e)}", "ERROR")

# =============================================
# QUICK DOWNLOAD FUNCTIONS
# =============================================

def quick_download(url, directory="./downloads", filename=None):
    """
    Quick download function untuk penggunaan langsung

    Args:
        url: URL untuk didownload (auto-detect platform)
        directory: Direktori tujuan (default: ./downloads)
        filename: Nama file (default: auto dari URL/platform)

    Returns:
        bool: True jika berhasil, False jika gagal
    """
    downloader = UniversalDownloader()
    return downloader.download_file(url, directory, filename)

def batch_download_individual(url_directory_map):
    """
    Download multiple files dengan direktori individual untuk setiap file

    Args:
        url_directory_map: Dict {url: directory}

    Returns:
        dict: {'success': count, 'failed': count, 'total': count, 'results': []}
    """
    downloader = UniversalDownloader()

    total = len(url_directory_map)
    success_count = 0
    failed_count = 0
    results = []

    print(f"📦 BATCH DOWNLOAD: {total} file(s)")
    print("=" * 60)

    for i, (url, directory) in enumerate(url_directory_map.items(), 1):
        platform = downloader.detect_platform(url)
        print(f"\n[{i}/{total}] {platform.upper()}: auto-filename")
        print(f"📁 Target: {directory}")

        start_time = time.time()
        success = downloader.download_file(url, directory, None)  # filename = None for auto-detect
        end_time = time.time()

        result = {
            'url': url,
            'directory': directory,
            'platform': platform,
            'success': success,
            'time': end_time - start_time
        }
        results.append(result)

        if success:
            success_count += 1
        else:
            failed_count += 1

        print("-" * 60)

    final_result = {
        'success': success_count,
        'failed': failed_count,
        'total': total,
        'results': results
    }

    print(f"\n📊 BATCH SELESAI:")
    print(f"✅ Berhasil: {success_count}")
    print(f"❌ Gagal: {failed_count}")
    print(f"📁 Total: {total}")

    # Breakdown by platform
    platform_stats = {}
    for result in results:
        platform = result['platform']
        if platform not in platform_stats:
            platform_stats[platform] = {'success': 0, 'failed': 0}

        if result['success']:
            platform_stats[platform]['success'] += 1
        else:
            platform_stats[platform]['failed'] += 1

    print("\n📈 BREAKDOWN BY PLATFORM:")
    for platform, stats in platform_stats.items():
        total_platform = stats['success'] + stats['failed']
        success_rate = (stats['success'] / total_platform * 100) if total_platform > 0 else 0
        print(f"   {platform.upper()}: {stats['success']}/{total_platform} ({success_rate:.1f}%)")

    # Breakdown by directory (untuk individual mode)
    directory_stats = {}
    for result in results:
        directory = result['directory']
        if directory not in directory_stats:
            directory_stats[directory] = {'success': 0, 'failed': 0}

        if result['success']:
            directory_stats[directory]['success'] += 1
        else:
            directory_stats[directory]['failed'] += 1

    if len(directory_stats) > 1:  # Hanya tampilkan jika ada multiple directories
        print("\n📁 BREAKDOWN BY DIRECTORY:")
        for directory, stats in directory_stats.items():
            total_dir = stats['success'] + stats['failed']
            success_rate = (stats['success'] / total_dir * 100) if total_dir > 0 else 0
            short_dir = directory.split('/')[-1] if '/' in directory else directory
            print(f"   {short_dir}: {stats['success']}/{total_dir} ({success_rate:.1f}%)")

    return final_result

def batch_download(urls, directory="./downloads"):
    """
    Download multiple files sekaligus ke direktori yang sama (backward compatibility)

    Args:
        urls: List URLs atau dict {url: filename}
        directory: Direktori tujuan

    Returns:
        dict: {'success': count, 'failed': count, 'total': count, 'results': []}
    """
    # Convert ke url_directory_map format
    if isinstance(urls, list):
        url_directory_map = {url: directory for url in urls}
    else:
        # Jika dict {url: filename}, abaikan filename dan gunakan directory yang sama
        url_directory_map = {url: directory for url in urls.keys()}

    return batch_download_individual(url_directory_map)

def download_mixed_batch():
    """
    Interactive batch download untuk mixed URLs dengan opsi direktori
    """
    print("\n📦 BATCH DOWNLOAD MODE")
    print("Masukkan multiple URLs (berbeda platform), ketik 'done' untuk mulai download")

    urls = []
    while True:
        url = input(f"URL #{len(urls)+1} (atau 'done'): ").strip()
        if url.lower() == 'done':
            break
        elif url:
            urls.append(url)
        else:
            print("URL kosong, diabaikan.")

    if not urls:
        print("❌ Tidak ada URL untuk didownload")
        return

    downloader = UniversalDownloader()

    # Pilihan mode direktori
    print(f"\n📁 MODE DIREKTORI:")
    print("1. 📂 Sama - Semua file ke direktori yang sama")
    print("2. 📁 Individual - Setiap file ke direktori berbeda")

    while True:
        dir_mode = input("\nPilih mode direktori (1-2): ").strip()
        if dir_mode in ['1', '2']:
            break
        else:
            print("❌ Pilihan tidak valid! Pilih 1 atau 2.")

    url_directory_map = {}

    if dir_mode == '1':
        # Mode: Semua file ke direktori yang sama
        print("\n📂 DIREKTORI UNTUK SEMUA FILE:")
        directory = downloader.get_comfyui_directory()

        # Map semua URL ke direktori yang sama
        for url in urls:
            url_directory_map[url] = directory

        # Konfirmasi batch
        print(f"\n📋 KONFIRMASI BATCH:")
        print(f"📁 Direktori: {directory}")
        print(f"📄 Total files: {len(urls)}")

        for i, url in enumerate(urls, 1):
            platform = downloader.detect_platform(url)
            print(f"   {i}. {platform.upper()}: {url[:50]}...")

    else:
        # Mode: Setiap file ke direktori berbeda
        print("\n📁 PILIH DIREKTORI UNTUK SETIAP FILE:")

        for i, url in enumerate(urls, 1):
            platform = downloader.detect_platform(url)
            print(f"\n[{i}/{len(urls)}] {platform.upper()}")
            print(f"🔗 URL: {url[:60]}...")

            directory = downloader.get_comfyui_directory()
            url_directory_map[url] = directory

        # Konfirmasi batch dengan detail per-file
        print(f"\n📋 KONFIRMASI BATCH:")
        print(f"📄 Total files: {len(urls)}")
        print("📁 Direktori per file:")

        for i, (url, directory) in enumerate(url_directory_map.items(), 1):
            platform = downloader.detect_platform(url)
            print(f"   {i}. {platform.upper()}: {directory}")
            print(f"      └─ {url[:50]}...")

    confirm = input(f"\n🚀 Mulai batch download {len(urls)} files? (y/n): ")
    if confirm.lower() != 'y':
        print("❌ Batch download dibatalkan")
        return

    # Execute batch download dengan individual directories
    return batch_download_individual(url_directory_map)

# =============================================
# HELPER FUNCTIONS
# =============================================

def show_supported_platforms():
    """Tampilkan informasi platform yang didukung"""
    print("\n🌐 PLATFORM YANG DIDUKUNG:")
    print("=" * 50)
    print("🤗 HUGGING FACE:")
    print("   • Method: hf_xet (kecepatan maksimal)")
    print("   • Auth: HF Token (otomatis)")
    print("   • Format: https://huggingface.co/USER/REPO/resolve/main/FILE")
    print("   • Features: Resume download, private repos")

    print("\n🎨 CIVITAI:")
    print("   • Method: aria2 (multi-connection)")
    print("   • Auth: CivitAI Token (otomatis)")
    print("   • Format: https://civitai.com/api/download/models/ID")
    print("   • Features: Auto filename detection, resume download")

    print("\n🌐 GENERIC URLs:")
    print("   • Method: aria2 (fallback)")
    print("   • Auth: None (public URLs)")
    print("   • Format: Any direct download URL")
    print("   • Features: Resume download, progress monitoring")
    print("=" * 50)

def show_configuration():
    """Tampilkan konfigurasi saat ini"""
    print("\n⚙️  KONFIGURASI SAAT INI:")
    print("=" * 50)
    print(f"🤗 Hugging Face Token: {'✅ Configured' if HF_TOKEN else '❌ Not set'}")
    print(f"🎨 CivitAI Token: {'✅ Configured' if CIVITAI_TOKEN else '❌ Not set'}")
    print(f"👤 HF Username: {HF_USERNAME}")
    print("=" * 50)

    if not HF_TOKEN:
        print("⚠️  Hugging Face token tidak dikonfigurasi.")
        print("   Private repositories tidak dapat diakses.")

    if not CIVITAI_TOKEN:
        print("⚠️  CivitAI token tidak dikonfigurasi.")
        print("   Beberapa model mungkin memerlukan authentication.")

def interactive_menu():
    """Menu interaktif utama"""
    while True:
        print("\n" + "="*70)
        print("    🚀 UNIVERSAL AI MODEL DOWNLOADER 🚀")
        print("="*70)
        print("1. 📥 Single Download (Interactive)")
        print("2. 📦 Batch Download (Multiple URLs)")
        print("3. 🌐 Show Supported Platforms")
        print("4. ⚙️  Show Configuration")
        print("5. 🚪 Exit")

        choice = input("\nPilih menu (1-5): ").strip()

        if choice == '1':
            main()
        elif choice == '2':
            download_mixed_batch()
        elif choice == '3':
            show_supported_platforms()
        elif choice == '4':
            show_configuration()
        elif choice == '5':
            print("👋 Terima kasih telah menggunakan Universal Downloader!")
            break
        else:
            print("❌ Pilihan tidak valid! Pilih 1-5.")

# =============================================
# RUN PROGRAM
# =============================================

if __name__ == "__main__":
    try:
        # Mode 1: Interactive menu (default)
        interactive_menu()

        # Mode 2: Quick single download
        # quick_download("https://huggingface.co/USER/REPO/resolve/main/model.safetensors", "/path/to/dir")

        # Mode 3: Batch download
        # batch_download([
        #     "https://huggingface.co/USER/REPO/resolve/main/model1.safetensors",
        #     "https://civitai.com/api/download/models/123456"
        # ], "/root/ComfyUI/models/loras")

    except Exception as e:
        print(f"❌ Fatal error: {e}")
        sys.exit(1)
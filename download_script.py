import os
import sys
import shutil
import zipfile
import subprocess
import requests
import time
import errno
from rich.console import Console
from rich.progress import Progress

console = Console()

if getattr(sys, 'frozen', False):
    # Running as compiled exe
    BASE_DIR = os.path.dirname(sys.executable)
else:
    # Running as script
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

INTERNAL_DOWNLOADS = os.path.join(BASE_DIR, "internal_downloads")
GCC_DIR = os.path.join(INTERNAL_DOWNLOADS, "gcc")
VCPKG_DIR = os.path.join(INTERNAL_DOWNLOADS, "vcpkg")

# LLVM-MinGW (UCRT, 64-bit) 
# Provides Clang/LLD with MinGW-w64 runtime.
GCC_URL = "https://github.com/mstorsjo/llvm-mingw/releases/download/20251202/llvm-mingw-20251202-ucrt-x86_64.zip"
# MinGit
GIT_URL = "https://github.com/git-for-windows/git/releases/download/v2.43.0.windows.1/MinGit-2.43.0-64-bit.zip"

GIT_DIR = os.path.join(INTERNAL_DOWNLOADS, "git")

def download_file(url, target_path):
    # Check if we have a valid stdout for progress bar
    use_progress = True
    if sys.stdout is None or getattr(sys.stdout, 'isatty', lambda: False)() == False:
         # In GUI/Noconsole mode, we might not have a proper tty
         # Rich can handle non-tty but checking None is crucial
         if sys.stdout is None:
             use_progress = False

    try:
        with requests.get(url, stream=True) as response:
            response.raise_for_status()
            total_size = int(response.headers.get("content-length", 0))
            
            if use_progress:
                with Progress(console=console) as progress:
                    task = progress.add_task(f"[green]Downloading {os.path.basename(target_path)}...", total=total_size)
                    with open(target_path, "wb") as f:
                        for chunk in response.iter_content(chunk_size=8192):
                            f.write(chunk)
                            progress.update(task, advance=len(chunk))
            else:
                # Silent download
                with open(target_path, "wb") as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
    except Exception as e:
        # Propagate exception to caller
        raise e

def install_git():
    if os.path.exists(GIT_DIR) and os.path.exists(os.path.join(GIT_DIR, "cmd", "git.exe")):
         return

    os.makedirs(INTERNAL_DOWNLOADS, exist_ok=True)
    zip_path = os.path.join(INTERNAL_DOWNLOADS, "git.zip")
    
    if not os.path.exists(zip_path):
        console.print(f"[yellow]Downloading MinGit from {GIT_URL}...[/yellow]")
        try:
            download_file(GIT_URL, zip_path)
        except Exception as e:
            console.print(f"[red]Failed to download Git: {e}[/red]")
            return

    console.print("[yellow]Extracting Git...[/yellow]")
    try:
        os.makedirs(GIT_DIR, exist_ok=True)
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(GIT_DIR)
        
        console.print("[green]Git installed successfully.[/green]")
        os.remove(zip_path)
    except Exception as e:
         console.print(f"[red]Failed to extract Git: {e}[/red]")

def install_gcc():
    # We download llvm-mingw but name the dir 'gcc' to keep standard with other scripts
    # or we can rename variables, but 'gcc' implies 'compiler directory' here.
    if os.path.exists(GCC_DIR) and os.path.exists(os.path.join(GCC_DIR, "bin", "clang++.exe")):
        # console.print("[green]Compiler is already installed.[/green]")
        return

    os.makedirs(INTERNAL_DOWNLOADS, exist_ok=True)
    zip_path = os.path.join(INTERNAL_DOWNLOADS, "compiler.zip")
    
    if not os.path.exists(zip_path):
        console.print(f"[yellow]Downloading LLVM-MinGW from {GCC_URL}...[/yellow]")
        download_file(GCC_URL, zip_path)
 
    console.print("[yellow]Extracting Compiler...[/yellow]")
    # Raising exception if this fails is good
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(INTERNAL_DOWNLOADS)
    
    # Determine extracted folder name (starts with llvm-mingw)
    extracted_name = None
    for name in os.listdir(INTERNAL_DOWNLOADS):
        if name.startswith("llvm-mingw"):
            extracted_name = name
            break
    
    if extracted_name:
            extracted_path = os.path.join(INTERNAL_DOWNLOADS, extracted_name)
            
            # Robust move/rename with retries
            max_retries = 5
            for i in range(max_retries):
                try:
                    if os.path.exists(GCC_DIR):
                        # Force remove read-only files if necessary
                        def on_rm_error(func, path, exc_info):
                            os.chmod(path, 0o777)
                            func(path)
                        shutil.rmtree(GCC_DIR, onerror=on_rm_error)
                    
                    # Wait a tiny bit for FS to release locks
                    time.sleep(0.5) 
                    
                    shutil.move(extracted_path, GCC_DIR)
                    break
                except PermissionError:
                    if i < max_retries - 1:
                        time.sleep(1)
                    else:
                        raise
                except OSError as e:
                     # Access denied or folder not empty
                     if e.errno == errno.EACCES or e.errno == errno.ENOTEMPTY:
                         if i < max_retries - 1:
                             time.sleep(1)
                             continue
                     raise
    else:
        raise Exception(f"Extraction failed: Could not find llvm-mingw folder in {INTERNAL_DOWNLOADS}")
    
    console.print("[green]Compiler installed successfully.[/green]")
    if os.path.exists(zip_path):
        os.remove(zip_path)


def install_vcpkg(git_path_env=None):
    if os.path.exists(VCPKG_DIR) and os.path.exists(os.path.join(VCPKG_DIR, "vcpkg.exe")):
         # console.print("[green]vcpkg is already installed.[/green]")
         return

    console.print("[yellow]Cloning vcpkg...[/yellow]")
    
    # Use the git we just installed if available
    # We assume 'git' command is available in the environment passed, or in global path
    env = os.environ.copy()
    if git_path_env:
        env["PATH"] = git_path_env + os.pathsep + env["PATH"]
    
    if os.path.exists(VCPKG_DIR):
        shutil.rmtree(VCPKG_DIR)
    
    subprocess.run(["git", "clone", "https://github.com/microsoft/vcpkg.git", VCPKG_DIR], check=True, env=env)
    
    console.print("[yellow]Bootstrapping vcpkg...[/yellow]")
    bootstrap_script = os.path.join(VCPKG_DIR, "bootstrap-vcpkg.bat")
    subprocess.run([bootstrap_script], cwd=VCPKG_DIR, check=True, shell=True, env=env)
    
    console.print("[green]vcpkg installed successfully.[/green]")

if __name__ == "__main__":
    console.print("[bold blue]Checking dependencies...[/bold blue]")
    install_git()
    install_gcc()
    
    # Add git to path for vcpkg install
    git_cmd_path = os.path.join(GIT_DIR, "cmd")
    install_vcpkg(git_path_env=git_cmd_path)
    
    console.print("[bold blue]Dependencies check complete.[/bold blue]")

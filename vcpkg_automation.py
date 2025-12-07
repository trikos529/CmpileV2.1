import os
import subprocess
from rich.console import Console

console = Console()

class VcpkgManager:
    def __init__(self, internal_downloads_path):
        self.vcpkg_root = os.path.join(internal_downloads_path, "vcpkg")
        self.vcpkg_exe = os.path.join(self.vcpkg_root, "vcpkg.exe")
        # specific triplet for MinGW
        self.triplet = "x64-mingw-dynamic" 

    def is_installed(self):
        return os.path.exists(self.vcpkg_exe)

    def install_package(self, package_name):
        if not self.is_installed():
            console.print("[red]vcpkg not found. Please run caching/download script first.[/red]")
            return False

        console.print(f"[yellow]Installing {package_name} for {self.triplet}...[/yellow]")
        try:
            # We don't capture output here so the user can see progress
            # Enforce host triplet to avoid VS requirement
            subprocess.run(
                [self.vcpkg_exe, "install", f"{package_name}:{self.triplet}", f"--host-triplet={self.triplet}"],
                check=True,
                cwd=self.vcpkg_root
            )
            console.print(f"[green]Successfully installed {package_name}.[/green]")
            return True
        except subprocess.CalledProcessError:
            console.print(f"[red]Failed to install {package_name}.[/red]")
            return False

    def get_installed_path(self):
        return os.path.join(self.vcpkg_root, "installed", self.triplet)

    def get_include_path(self):
        return os.path.join(self.get_installed_path(), "include")

    def get_lib_path(self):
        return os.path.join(self.get_installed_path(), "lib")
    
    def get_bin_path(self):
        return os.path.join(self.get_installed_path(), "bin")

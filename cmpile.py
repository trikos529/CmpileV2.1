import os
import sys
import subprocess
import shlex

# Import our modules
import ui
import download_script
import vcpkg_automation
import package_finder

# Constants
INTERNAL_DOWNLOADS = download_script.INTERNAL_DOWNLOADS
GCC_BIN = os.path.join(download_script.GCC_DIR, "bin")
GPP_EXE = os.path.join(GCC_BIN, "clang++.exe")
GCC_EXE = os.path.join(GCC_BIN, "clang.exe")
GIT_CMD = os.path.join(download_script.INTERNAL_DOWNLOADS, "git", "cmd")

def setup_git_env():
    """Adds local git to PATH if present."""
    if not download_script.is_tool_on_path("git") and os.path.exists(GIT_CMD):
        if GIT_CMD not in os.environ["PATH"]:
            os.environ["PATH"] = GIT_CMD + os.pathsep + os.environ["PATH"]
            return True
    return False

def ensure_environment(log_func):
    """Checks and sets up GCC, Git and vcpkg."""
    log_func("Checking environment...")

    # Check/Install Git first
    download_script.install_git(log_func=log_func)
    setup_git_env()

    # Check GCC
    if not (download_script.is_tool_on_path("clang") or download_script.is_tool_on_path("gcc")):
        if not os.path.exists(GPP_EXE):
            log_func("GCC not found. installing...")
            try:
                download_script.install_gcc(log_func=log_func)
            except Exception as e:
                log_func(f"Failed to install GCC: {e}", "bold red")
                raise e

    # Add internal GCC to PATH if no system compiler is found
    if not (download_script.is_tool_on_path("clang") or download_script.is_tool_on_path("gcc")):
        if GCC_BIN not in os.environ["PATH"]:
            os.environ["PATH"] = GCC_BIN + os.pathsep + os.environ["PATH"]

    # Check vcpkg
    vcpkg_mgr = vcpkg_automation.VcpkgManager(INTERNAL_DOWNLOADS, log_func=log_func)
    if not vcpkg_mgr.is_installed() and not download_script.is_tool_on_path("vcpkg"):
        log_func("vcpkg not found. installing...")
        try:
            download_script.install_vcpkg(git_path_env=GIT_CMD, log_func=log_func)
        except Exception as e:
            log_func(f"Failed to install vcpkg: {e}", "bold red")
            raise e

    return vcpkg_mgr

def get_compiler_for_file(filepath):
    """Returns the appropriate compiler executable."""
    if filepath.endswith(('.c', '.C')):
        if download_script.is_tool_on_path("clang"): return "clang"
        if download_script.is_tool_on_path("gcc"): return "gcc"
        return GCC_EXE

    if download_script.is_tool_on_path("clang++"): return "clang++"
    if download_script.is_tool_on_path("g++"): return "g++"
    return GPP_EXE

class CmpileBuilder:
    def __init__(self, log_callback=None):
        self.log_callback = log_callback

    def log(self, message, style=""):
        if self.log_callback:
            self.log_callback(message, style)
        else:
            # Fallback to UI print if no callback (CLI mode)
            if "error" in style or "bold red" in style:
                ui.display_error(message)
            elif "success" in style or "bold green" in style:
                ui.display_success(message)
            else:
                ui.display_status(message)

    def build_and_run(self, source_files, compiler_flags=None, clean=False, run=True):

        expanded_files = []
        for path in source_files:
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for file in files:
                        if file.endswith(('.c', '.cpp', '.C', '.CPP')):
                            expanded_files.append(os.path.join(root, file))
            elif os.path.isfile(path):
                expanded_files.append(path)

        if not expanded_files:
            self.log("No valid source files found.", "bold red")
            return False

        files = [os.path.abspath(f) for f in expanded_files]
        for path in files:
            if not os.path.exists(path):
                self.log(f"File not found: {path}", "bold red")
                return False

        # 1. Environment Setup
        try:
            vcpkg_mgr = ensure_environment(self.log)
        except Exception as e:
            self.log(f"Environment setup failed: {e}", "bold red")
            return False

        # 2. Dependency Analysis
        all_includes = set()
        for src in files:
            self.log(f"Analyzing {os.path.basename(src)}...")
            includes = package_finder.find_includes(src)
            all_includes.update(includes)

        required_packages = package_finder.map_includes_to_packages(all_includes)

        if required_packages:
            self.log(f"Identified dependencies: {', '.join(required_packages)}")
            for pkg in required_packages:
                 if not vcpkg_mgr.install_package(pkg):
                     self.log(f"Failed to install dependency: {pkg}", "bold red")
                     return False # Stop if dependency fails
        else:
            self.log("No external dependencies detected.")

        # 3. Compilation
        self.log("Compiling...")

        OUT_DIR = "out"
        if not os.path.exists(OUT_DIR):
            os.makedirs(OUT_DIR)

        object_files = []

        include_path = vcpkg_mgr.get_include_path()
        lib_path = vcpkg_mgr.get_lib_path()

        base_compile_flags = []
        if os.path.exists(include_path):
            base_compile_flags.extend(["-I", include_path])
        if compiler_flags:
            try:
                base_compile_flags.extend(shlex.split(compiler_flags))
            except:
                base_compile_flags.extend(compiler_flags.split())

        compilation_failed = False
        for src in files:
            compiler = get_compiler_for_file(src)
            base_name = os.path.basename(src)
            obj_name = os.path.splitext(base_name)[0] + ".o"
            obj_path = os.path.join(OUT_DIR, obj_name)
            object_files.append(obj_path)

            needs_recompile = True
            if os.path.exists(obj_path) and not clean:
                if os.path.getmtime(src) < os.path.getmtime(obj_path):
                    needs_recompile = False

            if needs_recompile:
                self.log(f"Compiling {base_name}...")
                cmd = [compiler, "-c", src, "-o", obj_path] + base_compile_flags
                try:
                    # Capture stderr to show compile errors
                    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                    if result.stderr:
                        self.log(result.stderr, "bold red")
                except subprocess.CalledProcessError as e:
                    self.log(f"Compilation failed for {src}.", "bold red")
                    self.log(e.stderr, "bold red")
                    compilation_failed = True
                    break
            else:
                 self.log(f"Skipping {base_name} (up to date)")

        if compilation_failed:
            return False

        # Link
        self.log("Linking...")

        cpp_in_use = any(get_compiler_for_file(src) in [GPP_EXE, "g++", "clang++"] for src in files)
        if cpp_in_use:
            if download_script.is_tool_on_path("clang++"): linker = "clang++"
            elif download_script.is_tool_on_path("g++"): linker = "g++"
            else: linker = GPP_EXE
        else:
            if download_script.is_tool_on_path("clang"): linker = "clang"
            elif download_script.is_tool_on_path("gcc"): linker = "gcc"
            else: linker = GCC_EXE

        exe_name = os.path.splitext(os.path.basename(files[0]))[0] + ".exe"
        output_exe = os.path.join(OUT_DIR, exe_name)

        cmd = [linker] + object_files + ["-o", output_exe]
        if os.path.exists(lib_path):
            cmd.extend(["-L", lib_path])

        # Add required libraries. This is a simplified approach.
        # A more robust solution would involve checking vcpkg's installed files.
        if required_packages:
            for pkg in required_packages:
                 if pkg == "nlohmann-json": continue
                 if pkg == "fmt": cmd.append("-lfmt"); continue
                 if pkg == "sqlite3": cmd.append("-lsqlite3"); continue
                 if pkg == "curl": cmd.append("-lcurl"); continue
                 cmd.append(f"-l{pkg}")

        cmd.extend(["-static-libgcc", "-static-libstdc++"])

        try:
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            if result.stderr:
                self.log(result.stderr, "bold red")
            self.log("Build successful!", "bold green")
        except subprocess.CalledProcessError as e:
            self.log("Linking failed.", "bold red")
            self.log(e.stderr, "bold red")
            return False

        if run:
            self.log("Running...", "bold")

            env = os.environ.copy()
            bin_path = vcpkg_mgr.get_bin_path()
            if os.path.exists(bin_path):
                env["PATH"] = bin_path + os.pathsep + env["PATH"]

            try:
                p = subprocess.Popen([output_exe], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1, encoding='utf-8', errors='replace')

                # Stream output
                if p.stdout:
                    for line in iter(p.stdout.readline, ''):
                        if line.strip(): self.log(line.strip())

                # Check for errors after execution
                p.wait()
                if p.returncode != 0:
                    err_data = p.stderr.read() if p.stderr else ""
                    if err_data.strip():
                        self.log(f"Execution finished with return code {p.returncode}", "bold red")
                        self.log(err_data.strip(), "bold red")

            except Exception as e:
                self.log(f"Execution error: {e}", "bold red")

        return True

def main():
    ui.display_header()
    args = ui.parse_arguments()

    # Define a logger for the CLI that maps to the `ui` functions
    def cli_logger(message, style=""):
        if "error" in style or "bold red" in style:
            ui.display_error(message)
        elif "success" in style or "bold green" in style:
            ui.display_success(message)
        else:
            ui.display_status(message)

    # In CLI mode, the builder is provided with our CLI logger
    builder = CmpileBuilder(log_callback=cli_logger)
    builder.build_and_run(args.files, args.compiler_flags, args.clean, run=True)

if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        pass
    except Exception as e:
        print(f"Critical Error: {e}")

    if (len(sys.argv) > 1 or getattr(sys, 'frozen', False)) and not any('gui' in arg.lower() for arg in sys.argv):
         print("\n")
         input("Press Enter to exit...")
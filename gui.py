import customtkinter as ctk
import os
import threading
from tkinter import filedialog
import cmpile
import sys
import json

# Set theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cmpile V2")
        self.geometry("800x600")

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Cmpile V2", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_file_btn = ctk.CTkButton(self.sidebar_frame, text="Add Files", command=self.add_files)
        self.add_file_btn.grid(row=1, column=0, padx=20, pady=10)

        self.clear_btn = ctk.CTkButton(self.sidebar_frame, text="Clear List", fg_color="transparent", border_width=2, command=self.clear_files)
        self.clear_btn.grid(row=2, column=0, padx=20, pady=10)

        self.quit_button = ctk.CTkButton(self.sidebar_frame, text="Quit", fg_color="transparent", border_width=2, command=self.quit)
        self.quit_button.grid(row=5, column=0, padx=20, pady=10, sticky="s")

        # Create Tabview
        self.tab_view = ctk.CTkTabview(self, corner_radius=8)
        self.tab_view.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.tab_view.add("Build")
        self.tab_view.add("Compiler Profiles")

        # Build Tab
        self.build_tab = self.tab_view.tab("Build")
        self.build_tab.grid_rowconfigure(4, weight=1)
        self.build_tab.grid_columnconfigure(0, weight=1)

        # Frame for file list and search bar
        self.file_frame = ctk.CTkFrame(self.build_tab)
        self.file_frame.grid(row=1, column=0, sticky="nsew", pady=(0, 10), padx=10)
        self.file_frame.grid_columnconfigure(0, weight=1)

        self.search_entry = ctk.CTkEntry(self.file_frame, placeholder_text="Search files...")
        self.search_entry.grid(row=0, column=0, sticky="ew", padx=10, pady=(5, 5))
        self.search_entry.bind("<KeyRelease>", self.filter_files)

        self.file_list_frame = ctk.CTkScrollableFrame(self.file_frame, label_text="Source Files")
        self.file_list_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))

        self.options_frame = ctk.CTkFrame(self.build_tab)
        self.options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10), padx=10)

        self.flags_entry = ctk.CTkEntry(self.options_frame, placeholder_text="Compiler Flags (e.g. -O2 -Wall)")
        self.flags_entry.pack(side="left", expand=True, fill="x", padx=10, pady=10)

        self.clean_checkbox = ctk.CTkCheckBox(self.options_frame, text="Clean Build")
        self.clean_checkbox.pack(side="left", padx=10, pady=10)

        self.build_btn = ctk.CTkButton(self.options_frame, text="Build & Run", command=self.start_build, fg_color="green", hover_color="darkgreen")
        self.build_btn.pack(side="right", padx=10, pady=10)

        self.log_label = ctk.CTkLabel(self.build_tab, text="Output Log", anchor="w")
        self.log_label.grid(row=3, column=0, sticky="w", padx=10, pady=(10,0))

        self.log_textbox = ctk.CTkTextbox(self.build_tab, height=200, font=("Consolas", 12))
        self.log_textbox.grid(row=4, column=0, sticky="nsew", padx=10, pady=10)
        self.log_textbox.configure(state="disabled")

        # Compiler Profiles Tab
        self.profiles_tab = self.tab_view.tab("Compiler Profiles")
        self.profiles_tab.grid_columnconfigure(0, weight=1)
        self.profiles_tab.grid_rowconfigure(1, weight=1)

        self.profile_selection_frame = ctk.CTkFrame(self.profiles_tab)
        self.profile_selection_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)

        self.profile_label = ctk.CTkLabel(self.profile_selection_frame, text="Select Profile:")
        self.profile_label.pack(side="left", padx=10, pady=10)

        self.profile_menu = ctk.CTkOptionMenu(self.profile_selection_frame, command=self.load_profile_data)
        self.profile_menu.pack(side="left", padx=10, pady=10)

        self.profile_editor_frame = ctk.CTkFrame(self.profiles_tab)
        self.profile_editor_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=10)
        self.profile_editor_frame.grid_columnconfigure(1, weight=1)

        self.c_compiler_label = ctk.CTkLabel(self.profile_editor_frame, text="C Compiler:")
        self.c_compiler_label.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.c_compiler_entry = ctk.CTkEntry(self.profile_editor_frame)
        self.c_compiler_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        self.cpp_compiler_label = ctk.CTkLabel(self.profile_editor_frame, text="C++ Compiler:")
        self.cpp_compiler_label.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.cpp_compiler_entry = ctk.CTkEntry(self.profile_editor_frame)
        self.cpp_compiler_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        self.linker_label = ctk.CTkLabel(self.profile_editor_frame, text="Linker:")
        self.linker_label.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.linker_entry = ctk.CTkEntry(self.profile_editor_frame)
        self.linker_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        self.profile_buttons_frame = ctk.CTkFrame(self.profiles_tab)
        self.profile_buttons_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)

        self.save_profile_btn = ctk.CTkButton(self.profile_buttons_frame, text="Save Profile", command=self.save_current_profile)
        self.save_profile_btn.pack(side="left", padx=10, pady=10)

        self.new_profile_btn = ctk.CTkButton(self.profile_buttons_frame, text="New Profile", command=self.create_new_profile)
        self.new_profile_btn.pack(side="right", padx=10, pady=10)

        self.source_files = []
        self.builder = cmpile.CmpileBuilder(log_callback=self.log_message)

        self.profiles = {}
        self.load_profiles()

    def load_profiles(self):
        if not os.path.exists("profiles.json"):
            default_profiles = {
                "Default": {
                    "c_compiler": "gcc",
                    "cpp_compiler": "g++",
                    "linker": "g++"
                }
            }
            with open("profiles.json", "w") as f:
                json.dump(default_profiles, f, indent=4)

        with open("profiles.json", "r") as f:
            self.profiles = json.load(f)

        self.profile_menu.configure(values=list(self.profiles.keys()))
        self.profile_menu.set(list(self.profiles.keys())[0])
        self.load_profile_data(list(self.profiles.keys())[0])

    def load_profile_data(self, profile_name):
        profile = self.profiles.get(profile_name, {})
        self.c_compiler_entry.delete(0, "end")
        self.c_compiler_entry.insert(0, profile.get("c_compiler", ""))
        self.cpp_compiler_entry.delete(0, "end")
        self.cpp_compiler_entry.insert(0, profile.get("cpp_compiler", ""))
        self.linker_entry.delete(0, "end")
        self.linker_entry.insert(0, profile.get("linker", ""))

    def save_current_profile(self):
        profile_name = self.profile_menu.get()
        self.profiles[profile_name] = {
            "c_compiler": self.c_compiler_entry.get(),
            "cpp_compiler": self.cpp_compiler_entry.get(),
            "linker": self.linker_entry.get()
        }
        with open("profiles.json", "w") as f:
            json.dump(self.profiles, f, indent=4)
        self.log_message(f"Profile '{profile_name}' saved.", "success")

    def create_new_profile(self):
        dialog = ctk.CTkInputDialog(text="Enter new profile name:", title="Create New Profile")
        profile_name = dialog.get_input()
        if profile_name and profile_name not in self.profiles:
            self.profiles[profile_name] = {
                "c_compiler": "",
                "cpp_compiler": "",
                "linker": ""
            }
            self.profile_menu.configure(values=list(self.profiles.keys()))
            self.profile_menu.set(profile_name)
            self.load_profile_data(profile_name)

    def add_files(self):
        files = filedialog.askopenfilenames(filetypes=[("C/C++ Files", "*.c *.cpp *.h *.hpp")])
        if files:
            for f in files:
                if f not in self.source_files:
                    self.source_files.append(f)
            self.refresh_file_list()

    def clear_files(self):
        self.source_files = []
        self.refresh_file_list()

    def refresh_file_list(self, filter_text=""):
        # Clear existing widgets
        for widget in self.file_list_frame.winfo_children():
            widget.destroy()

        # Add checkboxes for each file
        for f in self.source_files:
            if filter_text.lower() in f.lower():
                checkbox = ctk.CTkCheckBox(self.file_list_frame, text=f)
                checkbox.pack(anchor="w", padx=10, pady=2)
                checkbox.select() # Select by default

    def filter_files(self, event=None):
        search_term = self.search_entry.get()
        self.refresh_file_list(search_term)

    def get_selected_files(self):
        selected_files = []
        for widget in self.file_list_frame.winfo_children():
            if isinstance(widget, ctk.CTkCheckBox) and widget.get() == 1:
                selected_files.append(widget.cget("text"))
        return selected_files

    def log_message(self, message, style=""):
        self.after(0, lambda: self._append_log(message, style))

    def _append_log(self, message, style):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_build(self):
        selected_files = self.get_selected_files()
        if not selected_files:
            self.log_message("Please select source files first!", "error")
            return

        flags = self.flags_entry.get()
        clean = self.clean_checkbox.get() == 1

        self.build_btn.configure(state="disabled")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")

        profile = self.profiles.get(self.profile_menu.get())
        self.builder = cmpile.CmpileBuilder(log_callback=self.log_message, profile=profile)

        thread = threading.Thread(target=self.run_build_process, args=(selected_files, flags, clean))
        thread.start()

    def run_build_process(self, files, flags, clean):
        try:
            self.builder.build_and_run(files, compiler_flags=flags, clean=clean, run=True)
        except Exception as e:
            self.log_message(f"A critical error occurred: {e}", "error")
        finally:
            self.after(0, lambda: self.build_btn.configure(state="normal"))

    def quit(self):
        self.destroy()

if __name__ == "__main__":
    try:
        import multiprocessing
        multiprocessing.freeze_support()
    except:
        pass

    app = App()
    app.mainloop()
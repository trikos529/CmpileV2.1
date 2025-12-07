import customtkinter as ctk
import os
import threading
from tkinter import filedialog
import cmpile

# Set theme
ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("Cmpile V2")
        self.geometry("800x600")

        # Grid configuration
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar setup
        self.sidebar_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.sidebar_frame.grid(row=0, column=0, rowspan=4, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(4, weight=1)

        self.logo_label = ctk.CTkLabel(self.sidebar_frame, text="Cmpile V2", font=ctk.CTkFont(size=20, weight="bold"))
        self.logo_label.grid(row=0, column=0, padx=20, pady=(20, 10))

        self.add_file_btn = ctk.CTkButton(self.sidebar_frame, text="Add Files", command=self.add_files)
        self.add_file_btn.grid(row=1, column=0, padx=20, pady=10)

        self.clear_btn = ctk.CTkButton(self.sidebar_frame, text="Clear List", fg_color="transparent", border_width=2, command=self.clear_files)
        self.clear_btn.grid(row=2, column=0, padx=20, pady=10)
        
        # Main Area
        self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        self.main_frame.grid(row=0, column=1, sticky="nsew", padx=20, pady=20)
        self.main_frame.grid_rowconfigure(1, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)

        # File List
        self.file_list_label = ctk.CTkLabel(self.main_frame, text="Source Files", anchor="w")
        self.file_list_label.grid(row=0, column=0, sticky="w")
        
        self.file_textbox = ctk.CTkTextbox(self.main_frame, height=150)
        self.file_textbox.grid(row=1, column=0, sticky="nsew", pady=(0, 10))
        self.file_textbox.configure(state="disabled")

        # Options
        self.options_frame = ctk.CTkFrame(self.main_frame)
        self.options_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        
        self.flags_entry = ctk.CTkEntry(self.options_frame, placeholder_text="Compiler Flags (e.g. -O2 -Wall)")
        self.flags_entry.pack(side="left", expand=True, fill="x", padx=10, pady=10)
        
        self.clean_checkbox = ctk.CTkCheckBox(self.options_frame, text="Clean Build")
        self.clean_checkbox.pack(side="left", padx=10, pady=10)

        self.build_btn = ctk.CTkButton(self.options_frame, text="Build & Run", command=self.start_build, fg_color="green", hover_color="darkgreen")
        self.build_btn.pack(side="right", padx=10, pady=10)

        # Output Log
        self.log_label = ctk.CTkLabel(self.main_frame, text="Output Log", anchor="w")
        self.log_label.grid(row=3, column=0, sticky="w")

        self.log_textbox = ctk.CTkTextbox(self.main_frame, height=200, font=("Consolas", 12))
        self.log_textbox.grid(row=4, column=0, sticky="nsew")
        self.log_textbox.configure(state="disabled")
        
        # State
        self.source_files = []
        self.builder = cmpile.CmpileBuilder(log_callback=self.log_message)

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

    def refresh_file_list(self):
        self.file_textbox.configure(state="normal")
        self.file_textbox.delete("0.0", "end")
        for f in self.source_files:
            self.file_textbox.insert("end", f"{os.path.basename(f)}  ({f})\n")
        self.file_textbox.configure(state="disabled")

    def log_message(self, message, style=""):
        # This is called from background thread, so we must schedule update on main thread
        # Tkinter is not thread safe for direct widgets updates usually, but 
        # customtkinter might handle it or we use after/root functions.
        # Safe way: use after() does not work easily with args from thread?
        # Actually in Python Tkinter, simple updates from threads often work but can crash.
        # Recommended: queue. Or just try directly (often works on Windows), or use after_idle.
        # Let's try direct update first, if it crashes, we use a queue.
        # 'after' is safer.
        self.after(0, lambda: self._append_log(message, style))

    def _append_log(self, message, style):
        self.log_textbox.configure(state="normal")
        self.log_textbox.insert("end", message + "\n")
        self.log_textbox.see("end")
        self.log_textbox.configure(state="disabled")

    def start_build(self):
        if not self.source_files:
            self.log_message("Please select source files first!", "error")
            return
        
        flags = self.flags_entry.get()
        clean = self.clean_checkbox.get() == 1
        
        self.build_btn.configure(state="disabled")
        self.log_textbox.configure(state="normal")
        self.log_textbox.delete("0.0", "end")
        self.log_textbox.configure(state="disabled")
        
        # Run in thread to not freeze UI
        thread = threading.Thread(target=self.run_build_process, args=(flags, clean))
        thread.start()

    def run_build_process(self, flags, clean):
        # Redirect stdout/stderr to capture download script output
        class RedirectText:
            def __init__(self, callback, style=""):
                self.callback = callback
                self.style = style
            def write(self, string):
                if string.strip(): self.callback(string.strip(), self.style)
            def flush(self): pass

        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = RedirectText(self.log_message)
        sys.stderr = RedirectText(self.log_message, "error")

        try:
            self.builder.build_and_run(self.source_files, compiler_flags=flags, clean=clean, run=True)
        except Exception as e:
            self.log_message(f"Critical GUI Error: {e}", "error")
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            self.after(0, lambda: self.build_btn.configure(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()

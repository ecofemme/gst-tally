# tally_launcher.py
import os
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
import subprocess
import glob
from pathlib import Path


def setup_tcl_tk():
    """Find and set up Tcl/Tk environment variables for uv Python."""
    try:
        # Get the Python base prefix
        base_prefix = sys.base_prefix

        # Common base locations for Tcl/Tk
        potential_base_paths = [
            os.path.join(base_prefix, "tcl"),
            os.path.join(base_prefix, "lib"),
            os.path.join(os.path.dirname(base_prefix), "tcl"),
            base_prefix,
            os.path.join(base_prefix, "Tcl", "lib"),
            "/Library/Frameworks",
        ]

        # Find Tcl version
        tcl_path = None
        for base_path in potential_base_paths:
            if not os.path.exists(base_path):
                continue

            # Find tcl directory using glob pattern for version
            tcl_dirs = glob.glob(os.path.join(base_path, "tcl*"))
            if not tcl_dirs and os.path.exists(
                os.path.join(base_path, "Tcl.framework")
            ):
                # Check for macOS framework
                tcl_dirs = glob.glob(
                    os.path.join(base_path, "Tcl.framework", "Versions", "*")
                )

            for dir in tcl_dirs:
                if os.path.exists(os.path.join(dir, "init.tcl")):
                    tcl_path = dir
                    break

            if tcl_path:
                break

        # Find Tk version
        tk_path = None
        for base_path in potential_base_paths:
            if not os.path.exists(base_path):
                continue

            # Find tk directory using glob pattern for version
            tk_dirs = glob.glob(os.path.join(base_path, "tk*"))
            if not tk_dirs and os.path.exists(os.path.join(base_path, "Tk.framework")):
                # Check for macOS framework
                tk_dirs = glob.glob(
                    os.path.join(base_path, "Tk.framework", "Versions", "*")
                )

            for dir in tk_dirs:
                if os.path.exists(os.path.join(dir, "tk.tcl")):
                    tk_path = dir
                    break

            if tk_path:
                break

        # Set environment variables if paths were found
        if tcl_path:
            os.environ["TCL_LIBRARY"] = tcl_path
            print(f"Set TCL_LIBRARY to {tcl_path}")
        else:
            print("Warning: Could not find Tcl library directory")

        if tk_path:
            os.environ["TK_LIBRARY"] = tk_path
            os.environ["TKPATH"] = tk_path
            print(f"Set TK_LIBRARY to {tk_path}")
        else:
            print("Warning: Could not find Tk library directory")

        return tcl_path is not None and tk_path is not None

    except Exception as e:
        print(f"Error setting up Tcl/Tk: {e}")
        return False


# Initialize X11 threads for Linux before importing tkinter
if sys.platform.startswith("linux"):
    # Set the threading flag for X11
    os.environ["PYTHONTHREADED"] = "1"

    try:
        # Try to initialize X threads via _tkinter
        import _tkinter

        _tkinter.TkappInitStubs("", "", 1)
    except Exception as e:
        print(f"Note: Could not pre-initialize X11 threads: {e}")
        print(
            "If you encounter X11 threading issues, try installing python3-xlib and run again."
        )


class TallyLauncherGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("GST Tally Converter")
        self.root.geometry("600x400")

        # Set script directory as the working directory
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create the UI
        self.create_widgets()

    def create_widgets(self):
        # Main frame with padding
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Title
        title_label = tk.Label(
            main_frame,
            text="WooCommerce to Tally Converter",
            font=("Arial", 14, "bold"),
        )
        title_label.pack(pady=(0, 20))

        # Config file selection
        config_frame = tk.Frame(main_frame)
        config_frame.pack(fill=tk.X, pady=5)

        config_label = tk.Label(config_frame, text="Config File:", width=15, anchor="w")
        config_label.pack(side=tk.LEFT)

        self.config_var = tk.StringVar(value="config.yaml")
        config_entry = tk.Entry(config_frame, textvariable=self.config_var, width=40)
        config_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)

        config_button = tk.Button(
            config_frame, text="Browse", command=self.browse_config
        )
        config_button.pack(side=tk.RIGHT)

        # Status area
        self.status_text = scrolledtext.ScrolledText(main_frame, height=10, width=60)
        self.status_text.pack(fill=tk.BOTH, expand=True, pady=10)

        # Buttons frame
        button_frame = tk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)

        convert_button = tk.Button(
            button_frame,
            text="Convert",
            command=self.run_conversion,
            bg="#4CAF50",
            fg="white",
            padx=20,
        )
        convert_button.pack(side=tk.RIGHT, padx=5)

        quit_button = tk.Button(
            button_frame, text="Quit", command=self.root.destroy, padx=20
        )
        quit_button.pack(side=tk.RIGHT, padx=5)

    def browse_config(self):
        filename = filedialog.askopenfilename(
            initialdir=self.script_dir,
            title="Select Config File",
            filetypes=(("YAML files", "*.yaml *.yml"), ("All files", "*.*")),
        )
        if filename:
            self.config_var.set(filename)

    def log(self, message):
        self.status_text.insert(tk.END, message + "\n")
        self.status_text.see(tk.END)
        self.root.update()

    def run_conversion(self):
        config_path = self.config_var.get()

        # Clear status area
        self.status_text.delete(1.0, tk.END)

        # Check if config file exists
        if not os.path.exists(config_path):
            self.log(f"Error: Config file '{config_path}' not found!")
            return

        # Change to script directory
        os.chdir(self.script_dir)

        self.log("Starting conversion process...")

        try:
            # Run the main script with uv run python
            process = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "python",
                    "woo_csv_to_tally_xml.py",
                    "--config",
                    config_path,
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )

            # Stream the output to the status area
            for line in process.stdout:
                self.log(line.strip())

            process.wait()

            if process.returncode == 0:
                self.log("\nConversion completed successfully!")
                messagebox.showinfo("Success", "Conversion completed successfully!")
            else:
                self.log("\nConversion failed with errors.")
                messagebox.showerror(
                    "Error", "Conversion failed. Check the log for details."
                )

        except Exception as e:
            self.log(f"Error: {str(e)}")
            messagebox.showerror("Error", f"An error occurred: {str(e)}")


def main():
    # Set up Tcl/Tk environment variables
    setup_tcl_tk()

    # Initialize the GUI
    root = tk.Tk()
    app = TallyLauncherGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()

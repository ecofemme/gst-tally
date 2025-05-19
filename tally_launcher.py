import os
import sys
import subprocess
from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
)
from PyQt5.QtWidgets import QLabel, QLineEdit, QTextEdit, QFileDialog, QMessageBox


class TallyLauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GST Tally Converter")
        self.setMinimumSize(600, 400)

        # Set script directory as the working directory
        self.script_dir = os.path.dirname(os.path.abspath(__file__))

        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Title
        title_label = QLabel("WooCommerce to Tally Converter")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)

        # Config file selection
        config_layout = QHBoxLayout()
        config_label = QLabel("Config File:")
        config_label.setMinimumWidth(100)
        config_layout.addWidget(config_label)

        self.config_input = QLineEdit("config.yaml")
        config_layout.addWidget(self.config_input)

        self.browse_button = QPushButton("Browse")
        self.browse_button.clicked.connect(self.browse_config)
        config_layout.addWidget(self.browse_button)

        main_layout.addLayout(config_layout)

        # Status area
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        main_layout.addWidget(self.status_text)

        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()

        self.quit_button = QPushButton("Quit")
        self.quit_button.clicked.connect(self.close)
        button_layout.addWidget(self.quit_button)

        self.convert_button = QPushButton("Convert")
        self.convert_button.setStyleSheet("background-color: #4CAF50; color: white;")
        self.convert_button.clicked.connect(self.run_conversion)
        button_layout.addWidget(self.convert_button)

        main_layout.addLayout(button_layout)

    def browse_config(self):
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Select Config File",
            self.script_dir,
            "YAML files (*.yaml *.yml);;All files (*.*)",
        )
        if filename:
            self.config_input.setText(filename)

    def log(self, message):
        self.status_text.append(message)
        # Auto-scroll to bottom
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()  # Force UI update

    def run_conversion(self):
        config_path = self.config_input.text()

        # Clear status area
        self.status_text.clear()

        # Check if config file exists
        if not os.path.exists(config_path):
            self.log(f"Error: Config file '{config_path}' not found!")
            return

        # Change to script directory
        os.chdir(self.script_dir)

        self.log("Starting conversion process...")

        try:
            # Run the main script with uv run
            process = subprocess.Popen(
                ["uv", "run", "woo_csv_to_tally_xml.py", "--config", config_path],
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
                QMessageBox.information(
                    self, "Success", "Conversion completed successfully!"
                )
            else:
                self.log("\nConversion failed with errors.")
                QMessageBox.critical(
                    self, "Error", "Conversion failed. Check the log for details."
                )

        except Exception as e:
            self.log(f"Error: {str(e)}")
            QMessageBox.critical(self, "Error", f"An error occurred: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = TallyLauncherGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

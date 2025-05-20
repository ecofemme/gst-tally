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
from PyQt5.QtWidgets import QLabel, QTextEdit


class TallyLauncherGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GST Tally Converter")
        self.setMinimumSize(600, 400)
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.config_path = "config.yaml"
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        title_label = QLabel("WooCommerce to Tally Converter")
        title_label.setStyleSheet("font-size: 16pt; font-weight: bold;")
        main_layout.addWidget(title_label)
        main_layout.addSpacing(20)
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        main_layout.addWidget(self.status_text)
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

    def log(self, message):
        self.status_text.append(message)
        scrollbar = self.status_text.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        QApplication.processEvents()

    def run_conversion(self):
        self.status_text.clear()
        if not os.path.exists(self.config_path):
            self.log(f"Error: Config file '{self.config_path}' not found!")
            return
        os.chdir(self.script_dir)
        self.log("Starting conversion process...")
        try:
            process = subprocess.Popen(
                ["uv", "run", "woo_csv_to_tally_xml.py", "--config", self.config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True,
            )
            for line in process.stdout:
                self.log(line.strip())
            process.wait()
            if process.returncode == 0:
                self.log("\nConversion completed successfully!")
            else:
                self.log("\nConversion failed with errors.")
        except Exception as e:
            self.log(f"Error: {str(e)}")


def main():
    app = QApplication(sys.argv)
    window = TallyLauncherGUI()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

import sys
import os
import time
import platform
import psutil
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

TARGET_TOKEN = "mendel"
SHUTDOWN_DURATION = 10  # durée animation en secondes

class ShutdownWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        self.showFullScreen()

        # Layout principal vertical centré
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        # Logo M stylisé orange
        self.logo = QLabel("M")
        self.logo.setFont(QFont("Arial", 160, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.logo)

        # Texte d'extinction
        self.text = QLabel("Extinction en cours...")
        self.text.setFont(QFont("Arial", 24, QFont.Bold))
        self.text.setStyleSheet("color: white;")
        self.text.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.text)

        # Spinner centré
        spinner_layout = QHBoxLayout()
        spinner_layout.setAlignment(Qt.AlignCenter)
        self.spinner = QLabel("")
        self.spinner.setFont(QFont("Arial", 40))
        self.spinner.setStyleSheet("color: white;")
        self.spinner.setAlignment(Qt.AlignCenter)
        spinner_layout.addWidget(self.spinner)
        main_layout.addLayout(spinner_layout)

        self.setLayout(main_layout)

        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.index = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_spinner)
        self.timer.start(100)

        # Lancement de l'arrêt après 0.1s pour que l'UI se dessine
        QTimer.singleShot(100, self.perform_shutdown)

    def update_spinner(self):
        self.spinner.setText(self.frames[self.index % len(self.frames)])
        self.index += 1

    def perform_shutdown(self):
        # Kill tous les processus contenant TARGET_TOKEN sauf celui-ci
        self.kill_mendel_processes()
        # Laisser l'animation tourner au moins SHUTDOWN_DURATION
        QTimer.singleShot(SHUTDOWN_DURATION * 1000, self.finish_shutdown)

    def finish_shutdown(self):
        QApplication.quit()

    def kill_mendel_processes(self):
        my_pid = os.getpid()
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                pid = proc.info["pid"]
                name = (proc.info["name"] or "").lower()
                cmdline_list = proc.info.get("cmdline") or []
                cmdline_str = " ".join(str(x) for x in cmdline_list).lower()

                if pid == my_pid:
                    continue  # ne pas se tuer soi-même
                if TARGET_TOKEN in name or TARGET_TOKEN in cmdline_str:
                    proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

        # Attendre un peu puis forcer les restants
        time.sleep(1)
        for proc in psutil.process_iter(attrs=["pid", "name", "cmdline"]):
            try:
                pid = proc.info["pid"]
                name = (proc.info["name"] or "").lower()
                cmdline_list = proc.info.get("cmdline") or []
                cmdline_str = " ".join(str(x) for x in cmdline_list).lower()
                if pid == my_pid:
                    continue
                if TARGET_TOKEN in name or TARGET_TOKEN in cmdline_str:
                    try:
                        proc.kill()
                    except Exception:
                        pass
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

def main():
    app = QApplication(sys.argv)
    window = ShutdownWindow()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
import sys
import os
import psutil  # pip install psutil
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class ShutdownWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        self.showFullScreen()

        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        # Logo M stylisé
        self.logo = QLabel("M")
        self.logo.setFont(QFont("Arial", 160, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.logo)

        # Spinner et texte d'arrêt
        spinner_layout = QVBoxLayout()
        spinner_layout.setAlignment(Qt.AlignCenter)

        self.spinner = QLabel("")
        self.spinner.setFont(QFont("Arial", 40))
        self.spinner.setStyleSheet("color: white;")
        self.spinner.setAlignment(Qt.AlignCenter)
        spinner_layout.addWidget(self.spinner)

        self.text = QLabel("Arrêt en cours…")
        self.text.setFont(QFont("Arial", 20))
        self.text.setStyleSheet("color: white;")
        self.text.setAlignment(Qt.AlignCenter)
        spinner_layout.addWidget(self.text)

        main_layout.addLayout(spinner_layout)
        self.setLayout(main_layout)

        # Frames du spinner (braille pour effet circulaire)
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.index = 0

        # Timer pour le spinner
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_spinner)
        self.timer.start(100)

        # Timer pour killer les processus Mendel
        QTimer.singleShot(500, self.kill_mendel_processes)  # 0.5s après lancement

    def update_spinner(self):
        self.spinner.setText(self.frames[self.index % len(self.frames)])
        self.index += 1

    def kill_mendel_processes(self):
        # Kill tous les processus dont le nom contient "MENDEL" (desktop, apps, etc.)
        current_pid = os.getpid()
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                pid = proc.info['pid']
                name = proc.info['name'] or ""
                cmdline = " ".join(proc.info['cmdline'] or [])
                # Vérifier si "MENDEL" est dans le nom ou dans la ligne de commande
                if pid != current_pid and "MENDEL" in name.upper() or "MENDEL" in cmdline.upper():
                    p = psutil.Process(pid)
                    p.terminate()  # envoi SIGTERM
            except Exception:
                pass

        # Après 3 secondes, fermer la fenêtre
        QTimer.singleShot(3000, self.close_shutdown)

    def close_shutdown(self):
        self.timer.stop()
        self.close()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ShutdownWindow()
    window.show()
    sys.exit(app.exec_())
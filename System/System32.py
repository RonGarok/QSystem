from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu
)
from PyQt5.QtCore import Qt, QTimer, QDateTime
from PyQt5.QtGui import QFont, QPixmap
import sys
import os
import subprocess
from art import text2art  # ✅ Correction ici
import ctypes

class QSystemDesktop(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("QSystem Desktop")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.showFullScreen()
        self.setStyleSheet("background-color: black;")

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # 🖼️ Image de fond
        bg_label = QLabel(self)
        bg_label.setAlignment(Qt.AlignCenter)
        bg_path = os.path.join(os.path.dirname(__file__), "BG.png")
        pixmap = QPixmap(bg_path)
        if not pixmap.isNull():
            screen_size = QApplication.primaryScreen().size()
            bg_label.setPixmap(pixmap.scaled(screen_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        else:
            bg_label.setText("❌ BG.png introuvable")
            bg_label.setStyleSheet("color: red; font-size: 18px;")
        layout.addWidget(bg_label)

        # Barre des tâches
        taskbar = QHBoxLayout()
        taskbar.setContentsMargins(5, 5, 5, 5)

        # Bouton Q (menu démarrant)
        q_button = QPushButton("🟦 Q")
        q_button.setFixedSize(60, 30)
        q_button.setStyleSheet("background-color: #333; color: white;")
        q_button.setMenu(self.create_menu())
        taskbar.addWidget(q_button)

        # Boutons d'apps
        for name, script in [
            ("NotePad", "NotePad.py"),
            ("Fichier", "Fichier.py"),
            ("Calculatrice", "Calculator.py"),
            ("Python", "Python.py"),
            ("Weather", "Weather.py")
        ]:
            btn = QPushButton(name)
            btn.setFixedSize(100, 30)
            btn.setStyleSheet("background-color: #444; color: white;")
            btn.clicked.connect(lambda _, s=script: self.lancer_script(s))
            taskbar.addWidget(btn)

        # Spacer
        taskbar.addStretch()

        # Heure et date
        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: white; font-size: 14px;")
        self.clock_label.setAlignment(Qt.AlignRight)
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        taskbar.addWidget(self.clock_label)

        layout.addLayout(taskbar)

    def update_time(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("HH:mm:ss — dd/MM/yyyy"))

    def create_menu(self):
        menu = QMenu()

        actions = {
            "NotePad": "NotePad.py",
            "Fichier": "Fichier.py",
            "Calculatrice": "Calculator.py",
            "Python": "Python.py",
            "Paint": "Paint.py",
            "Terminal": "CMD.py",
            "Zip": "Zip.py",
            "Task Manager": "TaskManager.py",
            "UpdateCenter": os.path.join(os.path.dirname(os.path.dirname(__file__)), "UpdateCenter", "UpdateCenter.py"),

            "Weather": "Weather.py",
            "BackGround": "ChangeBG.py",
            "Weather": "Wheather.py",
            "Reboot" : "reboot",
            "Éteindre": "shutdown"
        }

        for name, action in actions.items():
            act = menu.addAction(name)
            if action == "shutdown":
                act.triggered.connect(self.shutdown)
            elif action == "reboot":
                act.triggered.connect(lambda: ctypes.windll.user32.MessageBoxW(
                    0,
                    "L'option de reboot est encore en cours de développement",
                    "SYSTEM ERROR",
                    0x10
                ))
            else:
                act.triggered.connect(lambda _, s=action: self.lancer_script(s))

        return menu


    def lancer_script(self, script_name):
        chemin = os.path.join(os.path.dirname(__file__), script_name)
        subprocess.Popen(["python", chemin])

    def shutdown(self):
        print("🛑 Fermeture du système...")
        os.system("taskkill /f /im python.exe")
        os.system("taskkill /f /im QSystem.exe")
        sys.exit()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = QSystemDesktop()
    sys.exit(app.exec_())

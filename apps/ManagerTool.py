import sys
import os
import shutil
import subprocess
import requests
from contextlib import suppress
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# Configuration
LOCAL_VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")
GITHUB_RAW_VERSION_URL = "https://raw.githubusercontent.com/RonGarok/QSystem/Mendel/apps/version.txt"
GITHUB_REPO_URL = "https://github.com/RonGarok/QSystem.git"
GITHUB_BRANCH = "Mendel"
BOOT_SCRIPT = os.path.join("boot", "boot.py")

# Style
PANEL_STYLE = "QFrame { background-color: #2f2f2f; border-radius: 12px; }"
LABEL_STYLE = "color: white; font-size: 14px;"
BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: white;
    border: 1px solid #616161;
    padding: 6px 12px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #5c5c5c; }
QPushButton:pressed { background-color: #474747; }
"""

class ManagerTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ManagerTool")
        self.setStyleSheet("background-color: black;")
        self.setFixedSize(400, 220)

        # Petit logo M orange
        self.logo = QLabel("M", self)
        self.logo.setFont(QFont("Arial", 80, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.move(10, 10)

        # Panneau central
        self.panel = QFrame(self)
        self.panel.setStyleSheet(PANEL_STYLE)
        self.panel.setGeometry(100, 40, 280, 140)

        self.layout = QVBoxLayout(self.panel)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setSpacing(12)

        self.status_label = QLabel("Vérification de la version...")
        self.status_label.setStyleSheet(LABEL_STYLE)
        self.layout.addWidget(self.status_label)

        self.update_btn = QPushButton("Mettre à jour maintenant")
        self.update_btn.setStyleSheet(BUTTON_STYLE)
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self.perform_update)
        self.layout.addWidget(self.update_btn)

        QTimer.singleShot(100, self.check_version)

    def read_local_version(self):
        try:
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "0.0.0"

    def fetch_remote_version(self):
        with suppress(Exception):
            r = requests.get(GITHUB_RAW_VERSION_URL, timeout=5)
            if r.status_code == 200:
                return r.text.strip()
        return None

    def version_is_outdated(self, local, remote):
        def parse(v): return [int(x) for x in v.strip().split(".")]
        try:
            return parse(remote) > parse(local)
        except Exception:
            return False

    def check_version(self):
        local = self.read_local_version()
        remote = self.fetch_remote_version()
        if not remote:
            self.status_label.setText("Impossible de récupérer la version distante.")
            return
        if self.version_is_outdated(local, remote):
            self.status_label.setText(f"Version actuelle : {local}\nNouvelle version : {remote}")
            self.update_btn.setVisible(True)
        else:
            self.status_label.setText(f"Système à jour\nVersion : {local}")
            QTimer.singleShot(2000, self.launch_boot)

    def perform_update(self):
        self.status_label.setText("Téléchargement de la mise à jour...")
        QTimer.singleShot(100, self.download_and_replace)

    def download_and_replace(self):
        try:
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            temp_dir = os.path.join(root, "_update_temp")
            if os.path.exists(temp_dir):
                shutil.rmtree(temp_dir)

            subprocess.run(["git", "clone", "--branch", GITHUB_BRANCH, GITHUB_REPO_URL, temp_dir], check=True)

            # Supprimer tous les fichiers sauf le dossier temporaire
            for item in os.listdir(root):
                full = os.path.join(root, item)
                if item != "_update_temp":
                    if os.path.isdir(full):
                        shutil.rmtree(full)
                    else:
                        os.remove(full)

            # Déplacer les nouveaux fichiers
            for item in os.listdir(temp_dir):
                shutil.move(os.path.join(temp_dir, item), os.path.join(root, item))

            shutil.rmtree(temp_dir)
            self.status_label.setText("Mise à jour terminée. Redémarrage...")
            QTimer.singleShot(1000, self.launch_boot)
        except Exception as e:
            self.status_label.setText(f"Erreur : {e}")

    def launch_boot(self):
        try:
            root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
            boot_path = os.path.join(root, BOOT_SCRIPT)
            subprocess.Popen([sys.executable, boot_path], cwd=os.path.dirname(boot_path))
            QTimer.singleShot(300, lambda: QApplication.quit())
        except Exception as e:
            self.status_label.setText(f"Erreur lancement boot.py : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ManagerTool()
    w.show()
    sys.exit(app.exec_())
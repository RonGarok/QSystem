from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel, QVBoxLayout, QWidget
)
from PyQt5.QtCore import Qt
import subprocess
import sys
import os

class UpdateCenter(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UpdateCenter - QSystem")
        self.setGeometry(300, 200, 500, 300)

        self.status_label = QLabel("Version actuelle : inconnue")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("font-size: 16px;")

        self.check_btn = QPushButton("🔍 Vérifier si une mise à jour est présente")
        self.check_btn.setStyleSheet("font-size: 14px; padding: 10px;")
        self.check_btn.clicked.connect(self.lancer_verification)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.check_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def lancer_verification(self):
        self.check_btn.setEnabled(False)
        self.status_label.setText("⏳ Vérification en cours...")
        try:
            chemin = os.path.join(os.path.dirname(__file__), "Version.py")
            subprocess.call(["python", chemin])
        except Exception as e:
            self.status_label.setText(f"❌ Erreur : {e}")
        self.check_btn.setEnabled(True)

        # Recharge la version après exécution
        self.afficher_version()

    def afficher_version(self):
        version_path = os.path.join(os.path.dirname(__file__), "Version.txt")
        if os.path.exists(version_path):
            with open(version_path, "r", encoding="utf-8") as f:
                for line in f:
                    if line.startswith("Version="):
                        version = line.split("=")[1].strip()
                        self.status_label.setText(f"✅ Version actuelle : {version}")
                        return
        self.status_label.setText("⚠️ Version non détectée")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = UpdateCenter()
    window.afficher_version()
    window.show()
    sys.exit(app.exec_())
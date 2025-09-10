from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QLabel,
    QFileDialog, QVBoxLayout, QWidget
)
from PyQt5.QtCore import Qt
import os
import sys
import shutil
import subprocess

class ChangeBG(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Changer le fond d'écran QSystem")
        self.setGeometry(300, 200, 400, 200)

        self.status = QLabel("📁 Sélectionnez une image PNG ou JPG")
        self.status.setAlignment(Qt.AlignCenter)
        self.status.setStyleSheet("font-size: 14px;")

        self.select_btn = QPushButton("🖼️ Choisir une image")
        self.select_btn.clicked.connect(self.choisir_image)

        layout = QVBoxLayout()
        layout.addWidget(self.status)
        layout.addWidget(self.select_btn)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def choisir_image(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Sélectionner une image", "", "Images (*.png *.jpg *.jpeg)"
        )
        if not file_path:
            self.status.setText("⚠️ Aucune image sélectionnée")
            return

        try:
            # 📁 Dossier de System32.py
            system32_dir = os.path.dirname(__file__)
            bg_path = os.path.join(system32_dir, "BG.png")

            # 🛑 Supprimer l'ancien fond
            if os.path.exists(bg_path):
                os.remove(bg_path)

            # 🔄 Copier et renommer la nouvelle image
            shutil.copy(file_path, bg_path)
            self.status.setText("✅ Fond d'écran mis à jour")

            # 🛑 Fermer System32.py s’il est actif
            os.system("taskkill /f /im python.exe")

            # 🚀 Relancer System32.py
            system32_path = os.path.join(system32_dir, "System32.py")
            subprocess.Popen(["python", system32_path])

        except Exception as e:
            self.status.setText(f"❌ Erreur : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChangeBG()
    window.show()
    sys.exit(app.exec_())

import sys
import os
import subprocess
from PyQt5.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QHBoxLayout, QMessageBox
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

class BootWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet("background-color: black;")
        self.showFullScreen()

        # Layout principal vertical centré
        main_layout = QVBoxLayout()
        main_layout.setAlignment(Qt.AlignCenter)

        # Logo M stylisé orange, centré
        self.logo = QLabel("M")
        self.logo.setFont(QFont("Arial", 160, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.logo)

        # Spinner centré sous le M
        spinner_layout = QHBoxLayout()
        spinner_layout.setAlignment(Qt.AlignCenter)
        self.spinner = QLabel("")
        self.spinner.setFont(QFont("Arial", 40))
        self.spinner.setStyleSheet("color: white;")
        self.spinner.setAlignment(Qt.AlignCenter)
        spinner_layout.addWidget(self.spinner)
        main_layout.addLayout(spinner_layout)

        self.setLayout(main_layout)

        # Frames du spinner (unicodes « braille » pour effet circulaire)
        self.frames = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]
        self.index = 0

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_spinner)
        self.timer.start(100)

        # Après 15 secondes, on tente de lancer Mendelboot.py
        QTimer.singleShot(15000, self.launch_mendelboot)

    def update_spinner(self):
        self.spinner.setText(self.frames[self.index % len(self.frames)])
        self.index += 1

    def launch_mendelboot(self):
        self.timer.stop()
        # On ferme l'interface de boot visuelle
        self.close()

        # Résolution robuste des chemins à partir du fichier boot.py
        boot_dir = os.path.dirname(os.path.abspath(__file__))  # .../project_root/boot
        project_root = os.path.abspath(os.path.join(boot_dir, ".."))
        system_dir = os.path.join(project_root, "system")      # .../project_root/system
        mendel_path = os.path.join(system_dir, "Mendelboot.py")# .../project_root/system/Mendelboot.py

        # Vérifications simples
        if not os.path.isdir(system_dir):
            self.show_error(f"Dossier system introuvable:\n{system_dir}")
            return

        if not os.path.isfile(mendel_path):
            self.show_error(f"Fichier Mendelboot.py introuvable:\n{mendel_path}")
            return

        # Commande pour lancer Mendelboot.py avec le même interpréteur Python
        cmd = [sys.executable, mendel_path]

        try:
            # Lancer en subprocess en positionnant cwd=system_dir pour que __file__ et chemins relatifs fonctionnent
            proc = subprocess.run(
                cmd,
                cwd=system_dir,
                capture_output=True,
                text=True,
                check=False
            )
        except Exception as e:
            self.show_error(f"Erreur lors du lancement de Mendelboot.py:\n{e}")
            return

        # Si le script a renvoyé une erreur, afficher stdout/stderr pour débogage
        if proc.returncode != 0:
            msg = (
                f"Mendelboot.py a échoué (code {proc.returncode}).\n\n"
                f"STDOUT:\n{proc.stdout}\n\nSTDERR:\n{proc.stderr}"
            )
            print(msg)
            self.show_error(msg)
        else:
            # Succès: on peut afficher un bref message console ou rien
            if proc.stdout:
                print("Mendelboot STDOUT:", proc.stdout)
            if proc.stderr:
                print("Mendelboot STDERR:", proc.stderr)

    def show_error(self, text):
        dlg = QMessageBox(self)
        dlg.setWindowTitle("Erreur de lancement")
        dlg.setText(text)
        dlg.setIcon(QMessageBox.Critical)
        dlg.setStandardButtons(QMessageBox.Ok)
        dlg.exec_()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = BootWindow()
    window.show()
    sys.exit(app.exec_())
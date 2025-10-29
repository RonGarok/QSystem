import sys
import os
import time
import subprocess
import traceback
import shutil
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QMessageBox, QFrame
)
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QFont

APP_DIR = os.path.abspath(os.path.dirname(__file__))
USER_FILE = os.path.join(APP_DIR, "user.txt")
SYSTEM_DIR = os.path.join(APP_DIR, "system")
SYSTEM_SCRIPT = os.path.join(SYSTEM_DIR, "system32.py")
ERROR_LOG = os.path.join(APP_DIR, "mendel_error.log")
LAUNCH_LOG = os.path.join(APP_DIR, "mendel_launch.log")
COPIED_USER_IN_SYSTEM = os.path.join(SYSTEM_DIR, "user.txt")

# Styles
PANEL_STYLE_DARK = """
QFrame {
    background-color: #2f2f2f;
    border-radius: 12px;
}
"""

LINEEDIT_STYLE_DARK = """
QLineEdit {
    background-color: #3a3a3a;
    color: #ffffff;
    border: 1px solid #444444;
    padding: 8px;
    border-radius: 6px;
}
QLineEdit:focus {
    border: 1px solid #666666;
}
QLineEdit::placeholder {
    color: rgba(255,255,255,0.85);
}
"""

BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: #ffffff;
    border: 1px solid #616161;
    padding: 8px 14px;
    border-radius: 6px;
}
QPushButton:hover {
    background-color: #5c5c5c;
}
QPushButton:pressed {
    background-color: #474747;
}
"""

MSGBOX_STYLE = """
QMessageBox {
    background-color: #2f2f2f;
    color: #ffffff;
    border-radius: 8px;
}
QPushButton {
    background-color: #444444;
    color: #ffffff;
    padding: 6px 12px;
    border-radius: 6px;
}
QPushButton:hover {
    background-color: #555555;
}
"""

def write_error_log(msg):
    try:
        with open(ERROR_LOG, "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        print("Impossible d'écrire le log d'erreur:", msg)

class AuthWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Auth")
        self.setStyleSheet("background-color: black;")
        self._is_fullscreen = True

        # Logo
        self.logo = QLabel("M", self)
        self.logo.setFont(QFont("Arial", 160, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.logo.setFixedHeight(200)
        self.logo.setFixedWidth(220)
        self.logo.move(10, 10)
        self.logo.setAttribute(Qt.WA_TransparentForMouseEvents)

        # Panel
        self.panel = QFrame(self)
        self.panel.setStyleSheet(PANEL_STYLE_DARK)
        self.panel.setFrameShape(QFrame.NoFrame)
        self.panel.setFixedSize(600, 360)

        self.panel_layout = QVBoxLayout()
        self.panel_layout.setAlignment(Qt.AlignCenter)
        self.panel_layout.setSpacing(12)
        self.panel.setLayout(self.panel_layout)

        main_layout = QVBoxLayout()
        main_layout.addWidget(self.panel)
        self.setLayout(main_layout)

        self._last_attempt = 0.0
        self._min_delay = 1.0

        self.showFullScreen()

        if not os.path.exists(USER_FILE) or os.path.getsize(USER_FILE) == 0:
            self.show_create_user_page()
        else:
            self.show_login_page()

        QTimer.singleShot(0, self.center_panel)

    def center_panel(self):
        if not hasattr(self, "panel"):
            return
        screen_rect = QApplication.primaryScreen().availableGeometry()
        x = (screen_rect.width() - self.panel.width()) // 2
        y = (screen_rect.height() - self.panel.height()) // 2
        self.panel.move(x, y)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "panel"):
            self.center_panel()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_F11:
            self.toggle_fullscreen()
        elif event.key() == Qt.Key_Escape and not self._is_fullscreen:
            self.toggle_fullscreen()

    def toggle_fullscreen(self):
        if self._is_fullscreen:
            self.showNormal()
            self._is_fullscreen = False
        else:
            self.showFullScreen()
            self._is_fullscreen = True
            QTimer.singleShot(0, self.center_panel)

    def clear_panel(self):
        while self.panel_layout.count():
            item = self.panel_layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)

    def make_dark_messagebox(self, title, text, icon=QMessageBox.Information):
        mb = QMessageBox(self)
        mb.setWindowTitle(title)
        mb.setText(text)
        mb.setIcon(icon)
        mb.setStyleSheet(MSGBOX_STYLE)
        mb.setWindowFlag(Qt.Dialog)
        return mb

    def show_create_user_page(self):
        self.clear_panel()
        title = QLabel("Créer un utilisateur")
        title.setFont(QFont("Arial", 20))
        title.setStyleSheet("color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)

        user_input = QLineEdit()
        user_input.setPlaceholderText("Pseudo")
        user_input.setFixedWidth(360)
        user_input.setStyleSheet(LINEEDIT_STYLE_DARK)

        pass_input = QLineEdit()
        pass_input.setPlaceholderText("Mot de passe (laisser vide pour aucun)")
        pass_input.setEchoMode(QLineEdit.Password)
        pass_input.setFixedWidth(360)
        pass_input.setStyleSheet(LINEEDIT_STYLE_DARK)

        create_btn = QPushButton("Créer")
        create_btn.setFixedWidth(160)
        create_btn.setStyleSheet(BUTTON_STYLE)

        v = QVBoxLayout()
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(12)
        v.addWidget(title)
        v.addWidget(user_input, alignment=Qt.AlignCenter)
        v.addWidget(pass_input, alignment=Qt.AlignCenter)
        v.addWidget(create_btn, alignment=Qt.AlignCenter)

        container = QWidget()
        container.setLayout(v)
        self.panel_layout.addWidget(container)

        def on_create():
            username = user_input.text().strip()
            password = pass_input.text()
            if not username:
                mb = self.make_dark_messagebox("Erreur", "Le pseudo ne peut pas être vide.", QMessageBox.Warning)
                mb.exec_()
                return
            try:
                with open(USER_FILE, "w", encoding="utf-8") as f:
                    f.write(f"{username}:{password}")
            except Exception:
                mb = self.make_dark_messagebox("Erreur", "Impossible d'écrire le fichier utilisateur.", QMessageBox.Critical)
                mb.exec_()
                return
            mb = self.make_dark_messagebox("Créé", "Utilisateur créé. Connectez-vous maintenant.", QMessageBox.Information)
            mb.exec_()
            self.show_login_page()

        create_btn.clicked.connect(on_create)

    def show_login_page(self):
        self.clear_panel()
        title = QLabel("Connexion")
        title.setFont(QFont("Arial", 20))
        title.setStyleSheet("color: #ffffff;")
        title.setAlignment(Qt.AlignCenter)

        user_input = QLineEdit()
        user_input.setPlaceholderText("Pseudo")
        user_input.setFixedWidth(360)
        user_input.setStyleSheet(LINEEDIT_STYLE_DARK)

        pass_input = QLineEdit()
        pass_input.setPlaceholderText("Mot de passe")
        pass_input.setEchoMode(QLineEdit.Password)
        pass_input.setFixedWidth(360)
        pass_input.setStyleSheet(LINEEDIT_STYLE_DARK)

        login_btn = QPushButton("Se connecter")
        login_btn.setFixedWidth(160)
        login_btn.setStyleSheet(BUTTON_STYLE)

        v = QVBoxLayout()
        v.setAlignment(Qt.AlignCenter)
        v.setSpacing(12)
        v.addWidget(title)
        v.addWidget(user_input, alignment=Qt.AlignCenter)
        v.addWidget(pass_input, alignment=Qt.AlignCenter)
        v.addWidget(login_btn, alignment=Qt.AlignCenter)

        container = QWidget()
        container.setLayout(v)
        self.panel_layout.addWidget(container)

        def read_user_file():
            try:
                with open(USER_FILE, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if ":" in content:
                        username, password = content.split(":", 1)
                    else:
                        username, password = content, ""
                    return username, password
            except Exception:
                return None, None

        stored_user, stored_pass = read_user_file()

        def attempt_login():
            now = time.time()
            if now - self._last_attempt < self._min_delay:
                return
            self._last_attempt = now

            entered_user = user_input.text().strip()
            entered_pass = pass_input.text()

            if stored_user is None:
                mb = self.make_dark_messagebox("Erreur", "Fichier utilisateur manquant ou illisible.", QMessageBox.Critical)
                mb.exec_()
                return

            if entered_user == stored_user and entered_pass == stored_pass:
                success = self.launch_system32_and_copy_user()
                if not success:
                    mb = self.make_dark_messagebox("Erreur", "Impossible de lancer system32.py. Voir mendel_error.log", QMessageBox.Critical)
                    mb.exec_()
                else:
                    QTimer.singleShot(100, lambda: QApplication.quit())
                    QTimer.singleShot(1000, lambda: os._exit(0))
            else:
                self.shake_window()

        login_btn.clicked.connect(attempt_login)

    def shake_window(self):
        original = self.pos()
        offset = 10
        seq = [QPoint(offset, 0), QPoint(-offset, 0)] * 4 + [QPoint(0,0)]
        i = 0
        timer = QTimer(self)

        def step():
            nonlocal i
            if i < len(seq):
                self.move(original + seq[i])
                i += 1
            else:
                timer.stop()
                self.move(original)

        timer.timeout.connect(step)
        timer.start(30)

    def launch_system32_and_copy_user(self):
        """
        Copie user.txt dans le sous-dossier system (si présent),
        puis lance system32.py dans un processus séparé détaché.
        Retourne True si tout s'est bien passé, False sinon.
        """
        # 1) Vérifier script system
        if not os.path.exists(SYSTEM_SCRIPT):
            write_error_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] system32.py absent: {SYSTEM_SCRIPT}")
            return False

        # 2) S'assurer que le dossier system existe
        try:
            os.makedirs(SYSTEM_DIR, exist_ok=True)
        except Exception:
            write_error_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Impossible de créer SYSTEM_DIR: {SYSTEM_DIR}")
            return False

        # 3) Copier user.txt dans system si disponible
        try:
            if os.path.exists(USER_FILE):
                shutil.copy2(USER_FILE, COPIED_USER_IN_SYSTEM)
                with open(LAUNCH_LOG, "a", encoding="utf-8") as lf:
                    lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Copie OK: {USER_FILE} -> {COPIED_USER_IN_SYSTEM}\n")
            else:
                with open(LAUNCH_LOG, "a", encoding="utf-8") as lf:
                    lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Aucun user.txt à copier: {USER_FILE}\n")
        except Exception:
            tb = traceback.format_exc()
            write_error_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Erreur copie user.txt:\n{tb}")
            return False

        # 4) Lancer system32.py détaché en passant l'argument --mendel-fullscreen
        try:
            cmd = [sys.executable, SYSTEM_SCRIPT, "--mendel-fullscreen"]

            # ouvrir / préparer le fichier de log de lancement
            launch_log_f = None
            try:
                launch_log_f = open(LAUNCH_LOG, "a", encoding="utf-8")
                launch_log_f.write(f"\n[{time.strftime('%Y-%m-%d %H:%M:%S')}] Lancement: {cmd}\n")
                launch_log_f.flush()
            except Exception:
                launch_log_f = None

            if os.name == "nt":
                CREATE_NO_WINDOW = 0x08000000
                CREATE_NEW_PROCESS_GROUP = 0x00000200
                if launch_log_f:
                    subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP,
                                     stdout=launch_log_f, stderr=launch_log_f)
                else:
                    subprocess.Popen(cmd, creationflags=CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP)
            else:
                if launch_log_f:
                    subprocess.Popen(cmd, start_new_session=True, stdout=launch_log_f, stderr=launch_log_f)
                else:
                    subprocess.Popen(cmd, start_new_session=True)

            if launch_log_f:
                launch_log_f.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] subprocess.Popen ok\n")
                launch_log_f.close()

            return True
        except Exception:
            tb = traceback.format_exc()
            write_error_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Erreur lancement system32:\n{tb}")
            try:
                mb = self.make_dark_messagebox("Erreur", "Erreur au lancement. Voir mendel_error.log", QMessageBox.Critical)
                mb.exec_()
            except Exception:
                pass
            return False

if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        w = AuthWindow()
        w.show()
        exit_code = app.exec_()
        sys.exit(exit_code)
    except Exception:
        tb = traceback.format_exc()
        write_error_log(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Exception non gérée dans main:\n{tb}")
        try:
            if QApplication.instance() is None:
                tmp_app = QApplication(sys.argv)
            else:
                tmp_app = QApplication.instance()
            msg = QMessageBox()
            msg.setWindowTitle("Erreur critique")
            msg.setText("Une erreur critique est survenue. Voir mendel_error.log")
            msg.exec_()
        except Exception:
            pass
        sys.exit(1)
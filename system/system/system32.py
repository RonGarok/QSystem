# system32.py
import sys
import os
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu, QFrame, QAction, QGraphicsOpacityEffect
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QFont, QPixmap

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
APP_ROOT = os.path.normpath(os.path.join(THIS_DIR, "..", "..", "apps"))

# mapping friendly name -> filename (kept as hint; dynamic discovery will augment)
APPS = {
    "Fichier": "Fichier.py",
    "Calculatrice": "Calculator.py",
    "ManagerCenter": "ManagerTool.py",
    "Météo": "Wheater.py"
}

USER_FILE = os.path.join(THIS_DIR, "user.txt")


def read_username():
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content.split(":", 1)[0] if ":" in content else content or "Utilisateur"
    except Exception:
        return "Utilisateur"


def discover_apps(apps_dir):
    """
    Discover .py files in apps_dir and return dict display_name -> filename.
    Prefers names from APPS mapping, otherwise uses filename without extension.
    Ignores __init__.py and files starting with underscore.
    """
    results = {}
    try:
        for entry in sorted(os.listdir(apps_dir)):
            if not entry.endswith(".py"):
                continue
            if entry == "__init__.py" or entry.startswith("_"):
                continue
            friendly = None
            for k, v in APPS.items():
                if os.path.normcase(v) == os.path.normcase(entry):
                    friendly = k
                    break
            if not friendly:
                friendly = os.path.splitext(entry)[0]
            results[friendly] = entry
    except Exception:
        pass
    return results


class Splash(QWidget):
    def __init__(self, text, duration=2000, parent=None):
        super().__init__(parent)
        self.duration = duration
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.init_ui(text)

    def init_ui(self, text):
        self.resize(QApplication.primaryScreen().size())
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setAlignment(Qt.AlignCenter)

        container = QFrame(self)
        container.setStyleSheet("""
            QFrame {
                background-color: rgba(47,47,47,0.92);
                border-radius: 12px;
            }
        """)
        container.setFixedSize(600, 200)
        v = QVBoxLayout(container)
        v.setAlignment(Qt.AlignCenter)

        label = QLabel(text)
        label.setStyleSheet("color: white;")
        label.setFont(QFont("Arial", 24, QFont.Bold))
        label.setAlignment(Qt.AlignCenter)
        v.addWidget(label)
        layout.addWidget(container, alignment=Qt.AlignCenter)

        self.effect = QGraphicsOpacityEffect(self)
        self.setGraphicsEffect(self.effect)
        self.effect.setOpacity(0.0)

    def show_with_fade(self, finished_callback):
        self.showFullScreen()

        self.anim_in = QPropertyAnimation(self.effect, b"opacity")
        self.anim_in.setDuration(600)
        self.anim_in.setStartValue(0.0)
        self.anim_in.setEndValue(1.0)
        self.anim_in.setEasingCurve(QEasingCurve.InOutQuad)

        def start_fade_out():
            self.anim_out.start()

        self.anim_out = QPropertyAnimation(self.effect, b"opacity")
        self.anim_out.setDuration(600)
        self.anim_out.setStartValue(1.0)
        self.anim_out.setEndValue(0.0)
        self.anim_out.setEasingCurve(QEasingCurve.InOutQuad)
        self.anim_out.finished.connect(lambda: (self.close(), finished_callback()))

        self.anim_in.finished.connect(lambda: QTimer.singleShot(self.duration, start_fade_out))
        self.anim_in.start()


class MendelDesktop(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Mendel Desktop")
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setStyleSheet("background-color: black;")
        self.apps_dir = APP_ROOT

        self.logo_big = QLabel("M", self)
        self.logo_big.setFont(QFont("Arial", 160, QFont.Bold))
        self.logo_big.setStyleSheet("color: orange;")
        self.logo_big.setAttribute(Qt.WA_TranslucentBackground)
        self.logo_big.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.logo_big.resize(220, 200)
        self.logo_big.move(10, 10)

        self.init_ui()
        self.showFullScreen()

    def _create_layout(self, parent, spacing=0):
        layout = QVBoxLayout(parent)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(spacing)
        return layout

    def init_ui(self):
        main_layout = self._create_layout(self)

        content = QFrame(self)
        content_layout = self._create_layout(content)

        bg_label = QLabel(self)
        bg_label.setAlignment(Qt.AlignCenter)
        bg_path = os.path.join(THIS_DIR, "BG.png")
        pixmap = QPixmap(bg_path)
        if not pixmap.isNull():
            screen_size = QApplication.primaryScreen().size()
            bg_label.setPixmap(pixmap.scaled(screen_size, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation))
        content_layout.addWidget(bg_label)
        main_layout.addWidget(content)

        taskbar_height = 40
        taskbar_frame = QFrame(self)
        taskbar_frame.setObjectName("taskbar")
        taskbar_frame.setFixedHeight(taskbar_height)
        taskbar_frame.setStyleSheet("""
            QFrame#taskbar {
                background: rgba(30,30,30,0.95);
                border-top: 1px solid rgba(255,255,255,0.03);
            }
        """)
        taskbar_layout = QHBoxLayout(taskbar_frame)
        taskbar_layout.setContentsMargins(6, 2, 6, 2)
        taskbar_layout.setSpacing(6)

        start_btn = QPushButton("M")
        start_btn.setFixedSize(34, 34)
        start_btn.setFont(QFont("Arial", 14, QFont.Bold))
        start_btn.setStyleSheet("""
            QPushButton {
                background-color: orange;
                color: black;
                border-radius: 6px;
            }
            QPushButton:pressed { background-color: #ff8c00; }
        """)

        start_menu = QMenu(self)
        DARK_MENU_QSS = """
        QMenu { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3d3d3d; padding: 6px; }
        QMenu::item { padding: 6px 24px 6px 24px; background-color: transparent; }
        QMenu::item:selected { background-color: #3a3a3a; }
        QMenu::separator { height: 1px; background: #3d3d3d; margin: 4px 0; }
        """
        start_menu.setStyleSheet(DARK_MENU_QSS)

        # Populate start menu dynamically from apps folder
        discovered = discover_apps(self.apps_dir)
        for display_name, filename in discovered.items():
            action = QAction(display_name, self)
            action.triggered.connect(lambda checked=False, n=display_name: self.lancer_app(n))
            start_menu.addAction(action)

        start_menu.addSeparator()

        # Reboot action: replace current process with reboot.py using os.execv
        def action_reboot():
            # prefer _reboot.py, then ManagerTool.py, else quit
            preferred = ["_reboot.py", "ManagerTool.py"]
            candidate_path = None
            disc = discover_apps(self.apps_dir)
            for pref in preferred:
                for dname, fname in disc.items():
                    if os.path.normcase(fname) == os.path.normcase(pref) or dname.lower().startswith(os.path.splitext(pref)[0].lower()):
                        p = os.path.join(self.apps_dir, fname)
                        if os.path.exists(p):
                            candidate_path = os.path.abspath(p)
                            break
                if candidate_path:
                    break
            if candidate_path:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                except Exception:
                    pass
                try:
                    os.execv(sys.executable, [sys.executable, candidate_path])
                except Exception as e:
                    print("Reboot execv failed:", e)
                    QApplication.quit()
            else:
                QApplication.quit()

        start_menu.addAction(QAction("Reboot", self, triggered=action_reboot))
        start_menu.addAction(QAction("Quitter", self, triggered=lambda: QApplication.quit()))
        start_btn.setMenu(start_menu)
        taskbar_layout.addWidget(start_btn)

        # Taskbar quick launch buttons from discovered apps (limited width)
        for display_name in list(discovered.keys())[:6]:
            btn = QPushButton(display_name)
            btn.setFixedSize(110, 30)
            btn.setStyleSheet("""
                QPushButton {
                    background-color: transparent;
                    color: white;
                    border: 1px solid rgba(255,255,255,0.06);
                    border-radius: 4px;
                    padding: 2px 8px;
                }
                QPushButton:hover { background-color: rgba(255,255,255,0.04); }
                QPushButton:pressed { background-color: rgba(255,255,255,0.02); }
            """)
            btn.clicked.connect(lambda _, n=display_name: self.lancer_app(n))
            taskbar_layout.addWidget(btn)

        taskbar_layout.addStretch()

        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: white; font-size: 12px;")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        taskbar_layout.addWidget(self.clock_label, 0, Qt.AlignRight)

        main_layout.addWidget(taskbar_frame)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_desktop_menu)

    def show_desktop_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu{background:#2b2b2b;color:#fff;} QMenu::item:selected{background:#3a3a3a;}")
        discovered = discover_apps(self.apps_dir)
        for display_name in discovered.keys():
            menu.addAction(display_name, lambda checked=False, n=display_name: self.lancer_app(n))
        menu.addSeparator()

        def ctx_reboot():
            # same priority: _reboot.py then ManagerTool.py, else quit
            preferred = ["_reboot.py", "ManagerTool.py"]
            candidate = None
            disc = discover_apps(self.apps_dir)
            for pref in preferred:
                for dname, fname in disc.items():
                    if os.path.normcase(fname) == os.path.normcase(pref) or dname.lower().startswith(os.path.splitext(pref)[0].lower()):
                        p = os.path.join(self.apps_dir, fname)
                        if os.path.exists(p):
                            candidate = os.path.abspath(p)
                            break
                if candidate:
                    break
            if candidate:
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                except Exception:
                    pass
                try:
                    os.execv(sys.executable, [sys.executable, candidate])
                except Exception:
                    QApplication.quit()
            else:
                QApplication.quit()

        menu.addAction("Reboot", ctx_reboot)
        menu.exec_(self.mapToGlobal(pos))

    def lancer_app(self, name):
        discovered = discover_apps(self.apps_dir)
        if name not in discovered:
            print("Application non trouvée:", name)
            return
        rel = discovered[name]
        script_path = os.path.join(self.apps_dir, rel)
        if not os.path.exists(script_path):
            alt = os.path.join(THIS_DIR, rel)
            if os.path.exists(alt):
                script_path = alt
            else:
                print(f"Script introuvable pour {name}: {script_path}")
                return
        try:
            subprocess.Popen([sys.executable, script_path], cwd=self.apps_dir)
        except Exception as e:
            print("Erreur lancement:", e)

    def update_time(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("HH:mm  dd/MM/yyyy"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "logo_big"):
            self.logo_big.move(10, 10)


def main():
    app = QApplication(sys.argv)
    username = read_username()
    splash_text = f"Bienvenue {username}"
    splash = Splash(splash_text, duration=1400)

    desktop = MendelDesktop()

    def on_splash_done():
        desktop.showFullScreen()

    splash.show_with_fade(on_splash_done)
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()

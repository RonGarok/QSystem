# system32.py
import sys
import os
import json
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QVBoxLayout,
    QHBoxLayout, QMenu, QFrame, QAction, QGraphicsOpacityEffect, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer, QDateTime, QPropertyAnimation, QEasingCurve, QPoint
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
PINS_FILE = os.path.join(THIS_DIR, "pins.json")
APP_SCAN_INTERVAL_MS = 3000  # 3 seconds, light periodic scan

def read_username():
    try:
        with open(USER_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            return content.split(":", 1)[0] if ":" in content else content or "Utilisateur"
    except Exception:
        return "Utilisateur"

def load_pins():
    # persisted list of pinned display names; create defaults if missing
    try:
        if os.path.exists(PINS_FILE):
            with open(PINS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
    except Exception:
        pass
    # defaults: ensure Fichier and ManagerTool are pinned (display rename applied later)
    defaults = ["Fichier", "ManagerTool"]
    save_pins(defaults)
    return defaults

def save_pins(pins):
    try:
        with open(PINS_FILE, "w", encoding="utf-8") as f:
            json.dump(pins, f, ensure_ascii=False, indent=2)
    except Exception:
        pass

def discover_apps(apps_dir):
    """
    Discover .py files in apps_dir and return dict display_name -> filename.
    Prefers names from APPS mapping, otherwise uses filename without extension.
    Ignores __init__.py and files starting with underscore.
    """
    results = {}
    try:
        entries = sorted(os.listdir(apps_dir))
    except Exception:
        return results
    for entry in entries:
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

        # internal state
        self._discovered = {}
        self._pins = load_pins()  # list of display names
        self._taskbar_buttons = []
        self._start_menu = None

        self.logo_big = QLabel("M", self)
        self.logo_big.setFont(QFont("Arial", 160, QFont.Bold))
        self.logo_big.setStyleSheet("color: orange;")
        self.logo_big.setAttribute(Qt.WA_TranslucentBackground)
        self.logo_big.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.logo_big.resize(220, 200)
        self.logo_big.move(10, 10)

        self.init_ui()
        self.start_app_scanner()
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
        self.taskbar_frame = QFrame(self)
        self.taskbar_frame.setObjectName("taskbar")
        self.taskbar_frame.setFixedHeight(taskbar_height)
        self.taskbar_frame.setStyleSheet("""
            QFrame#taskbar {
                background: rgba(30,30,30,0.95);
                border-top: 1px solid rgba(255,255,255,0.03);
            }
        """)
        taskbar_layout = QHBoxLayout(self.taskbar_frame)
        taskbar_layout.setContentsMargins(6, 2, 6, 2)
        taskbar_layout.setSpacing(6)

        self.start_btn = QPushButton("M")
        self.start_btn.setFixedSize(34, 34)
        self.start_btn.setFont(QFont("Arial", 14, QFont.Bold))
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: orange;
                color: black;
                border-radius: 6px;
            }
            QPushButton:pressed { background-color: #ff8c00; }
        """)

        self.start_menu = QMenu(self)
        DARK_MENU_QSS = """
        QMenu { background-color: #2b2b2b; color: #ffffff; border: 1px solid #3d3d3d; padding: 6px; }
        QMenu::item { padding: 6px 24px 6px 24px; background-color: transparent; }
        QMenu::item:selected { background-color: #3a3a3a; }
        QMenu::separator { height: 1px; background: #3d3d3d; margin: 4px 0; }
        """
        self.start_menu.setStyleSheet(DARK_MENU_QSS)
        self.start_btn.setMenu(self.start_menu)
        taskbar_layout.addWidget(self.start_btn)

        # placeholder for quick-launch area (we'll populate later)
        self.quick_launch_container = QFrame(self.taskbar_frame)
        self.quick_launch_layout = QHBoxLayout(self.quick_launch_container)
        self.quick_launch_layout.setContentsMargins(0,0,0,0)
        self.quick_launch_layout.setSpacing(6)
        taskbar_layout.addWidget(self.quick_launch_container)

        taskbar_layout.addStretch()

        self.clock_label = QLabel()
        self.clock_label.setStyleSheet("color: white; font-size: 12px;")
        self.clock_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.update_time()
        timer = QTimer(self)
        timer.timeout.connect(self.update_time)
        timer.start(1000)
        taskbar_layout.addWidget(self.clock_label, 0, Qt.AlignRight)

        main_layout.addWidget(self.taskbar_frame)

        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_desktop_menu)

        # initial populate
        self.refresh_apps_ui()

    def start_app_scanner(self):
        # Periodic scan to detect added/removed apps and update UI.
        # Lightweight: only directory listing and comparing names.
        self.scan_timer = QTimer(self)
        self.scan_timer.timeout.connect(self._scan_and_refresh)
        self.scan_timer.start(APP_SCAN_INTERVAL_MS)

    def _scan_and_refresh(self):
        try:
            new_disc = discover_apps(self.apps_dir)
            if new_disc != self._discovered:
                self._discovered = new_disc
                self.refresh_apps_ui()
        except Exception:
            # swallow exceptions to avoid console spam and UI crash
            pass

    def refresh_apps_ui(self):
        # Rebuild start menu and quick-launch buttons based on current discovery and pins
        try:
            # keep a copy of discovered
            self._discovered = discover_apps(self.apps_dir)

            # rebuild start menu
            self.start_menu.clear()
            # Add app actions with right-click (context) for pin/unpin
            for display_name in sorted(self._discovered.keys()):
                act = QAction(self._display_name_for_menu(display_name), self)
                # left-click: launch
                act.triggered.connect(lambda checked=False, n=display_name: self.lancer_app(n))
                # attach custom context action via event filter isn't straightforward on QAction,
                # so add a submenu with Pin/Unpin for each entry to keep it simple and reliable
                submenu = QMenu(self.start_menu)
                launch_action = QAction("Ouvrir", submenu, triggered=lambda checked=False, n=display_name: self.lancer_app(n))
                submenu.addAction(launch_action)

                if display_name in self._pins:
                    pin_action = QAction("Désépingler de la barre des tâches", submenu, triggered=lambda checked=False, n=display_name: self.toggle_pin(n))
                else:
                    pin_action = QAction("Épingler à la barre des tâches", submenu, triggered=lambda checked=False, n=display_name: self.toggle_pin(n))
                submenu.addAction(pin_action)

                # For user clarity add an action that shows real script name
                script_name = self._discovered.get(display_name, "")
                info_action = QAction(f"Script: {script_name}", submenu)
                info_action.setEnabled(False)
                submenu.addAction(info_action)

                # add submenu as an action in main start menu to emulate right-click options
                parent_action = QWidgetAction(self.start_menu)
                # create a small widget to host label and open submenu on hover/click is complex,
                # so simply add the submenu as a menu item: QMenu.addMenu returns the menu object
                self.start_menu.addMenu(submenu).setTitle(self._display_name_for_menu(display_name))

            self.start_menu.addSeparator()

            # Reboot and Quit actions
            self.start_menu.addAction(QAction("Reboot", self, triggered=self._action_reboot))
            self.start_menu.addAction(QAction("Quitter", self, triggered=lambda: QApplication.quit()))

            # rebuild quick-launch / taskbar buttons
            # clear existing
            for i in reversed(range(self.quick_launch_layout.count())):
                w = self.quick_launch_layout.itemAt(i).widget()
                if w:
                    w.setParent(None)
            self._taskbar_buttons = []

            # Show pinned apps first (ensure they exist)
            pinned_existing = [p for p in self._pins if p in self._discovered]
            for display_name in pinned_existing:
                btn = self._make_taskbar_button(display_name)
                self.quick_launch_layout.addWidget(btn)
                self._taskbar_buttons.append((display_name, btn))

            # Then add first discovered apps up to a visual limit (to keep original behavior)
            limit = 6
            added = set(pinned_existing)
            for display_name in list(self._discovered.keys()):
                if len(self._taskbar_buttons) >= limit:
                    break
                if display_name in added:
                    continue
                btn = self._make_taskbar_button(display_name)
                self.quick_launch_layout.addWidget(btn)
                self._taskbar_buttons.append((display_name, btn))
                added.add(display_name)

        except Exception:
            pass

    def _display_name_for_menu(self, display_name):
        # Display rename: ManagerTool displayed as UpdateCenter, but execute original script
        if display_name.lower() in ("managertool", "managercenter", "managertool.py"):
            return "UpdateCenter"
        return display_name

    def _make_taskbar_button(self, display_name):
        btn = QPushButton(self._display_name_for_menu(display_name))
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
        # context menu on right click to pin/unpin
        btn.setContextMenuPolicy(Qt.CustomContextMenu)
        btn.customContextMenuRequested.connect(lambda pos, n=display_name, b=btn: self._taskbar_btn_context(pos, n, b))
        return btn

    def _taskbar_btn_context(self, pos: QPoint, display_name, button):
        menu = QMenu(self)
        if display_name in self._pins:
            menu.addAction("Désépingler", lambda: self.toggle_pin(display_name))
        else:
            menu.addAction("Épingler", lambda: self.toggle_pin(display_name))
        menu.exec_(button.mapToGlobal(pos))

    def toggle_pin(self, display_name):
        try:
            if display_name in self._pins:
                self._pins.remove(display_name)
            else:
                # ensure only existing apps can be pinned
                if display_name in self._discovered:
                    self._pins.append(display_name)
            save_pins(self._pins)
            # refresh UI to reflect pin changes
            self.refresh_apps_ui()
        except Exception:
            pass

    def show_desktop_menu(self, pos):
        menu = QMenu(self)
        menu.setStyleSheet("QMenu{background:#2b2b2b;color:#fff;} QMenu::item:selected{background:#3a3a3a;}")
        discovered = discover_apps(self.apps_dir)
        for display_name in discovered.keys():
            menu.addAction(self._display_name_for_menu(display_name), lambda checked=False, n=display_name: self.lancer_app(n))
        menu.addSeparator()
        menu.addAction("Reboot", self._action_reboot)
        menu.exec_(self.mapToGlobal(pos))

    def _action_reboot(self):
        # prefer _reboot.py, then ManagerTool.py (actual filename), else quit
        preferred = ["_reboot.py", "ManagerTool.py"]
        candidate_path = None
        disc = discover_apps(self.apps_dir)
        for pref in preferred:
            # match by filename or by mapped display name
            for dname, fname in disc.items():
                if os.path.normcase(fname) == os.path.normcase(pref) or os.path.splitext(pref)[0].lower() == dname.lower():
                    p = os.path.join(self.apps_dir, fname)
                    if os.path.exists(p):
                        candidate_path = os.path.abspath(p)
                        break
            if candidate_path:
                break
        if candidate_path:
            try:
                # flush and exec; if exec fails, quit cleanly
                try:
                    sys.stdout.flush()
                    sys.stderr.flush()
                except Exception:
                    pass
                os.execv(sys.executable, [sys.executable, candidate_path])
            except Exception:
                QApplication.quit()
        else:
            QApplication.quit()

    def lancer_app(self, name):
        discovered = discover_apps(self.apps_dir)
        if name not in discovered:
            # silent fail to avoid console spam
            return
        rel = discovered[name]
        script_path = os.path.join(self.apps_dir, rel)
        if not os.path.exists(script_path):
            alt = os.path.join(THIS_DIR, rel)
            if os.path.exists(alt):
                script_path = alt
            else:
                return
        try:
            subprocess.Popen([sys.executable, script_path], cwd=self.apps_dir)
        except Exception:
            pass

    def update_time(self):
        now = QDateTime.currentDateTime()
        self.clock_label.setText(now.toString("HH:mm  dd/MM/yyyy"))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if hasattr(self, "logo_big"):
            self.logo_big.move(10, 10)

# QWidgetAction is used inside refresh_apps_ui; import it safely
from PyQt5.QtWidgets import QWidgetAction

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

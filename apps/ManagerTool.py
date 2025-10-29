#!/usr/bin/env python3
import sys
import os
import shutil
import subprocess
import requests
import traceback
import stat
from contextlib import suppress
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QFrame
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# ---------- Configuration ----------
LOCAL_VERSION_FILE = os.path.join(os.path.dirname(__file__), "version.txt")
GITHUB_RAW_VERSION_URL = "https://raw.githubusercontent.com/RonGarok/QSystem/Mendel/apps/version.txt"
GITHUB_REPO_URL = "https://github.com/RonGarok/QSystem.git"
GITHUB_BRANCH = "Mendel"
BOOT_SCRIPT = os.path.join("boot", "boot.py")
UPDATE_TEMP_NAME = "_update_temp"
UPDATE_LOG = "update.log"  # placed in project root

# ---------- Style ----------
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

# ---------- Helpers ----------
def write_log(project_root, *lines):
    try:
        path = os.path.join(project_root, UPDATE_LOG)
        with open(path, "a", encoding="utf-8") as f:
            for line in lines:
                f.write(line + "\n")
    except Exception:
        pass

def parse_version(v):
    try:
        return [int(x) for x in v.strip().split(".")]
    except Exception:
        return [0, 0, 0]

def rmtree_onerror(func, path, exc_info):
    """
    Handler for shutil.rmtree: change permissions and retry.
    """
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception:
        pass

def safe_remove(path):
    """
    Remove file or directory with many fallbacks to handle permissions/locks.
    """
    try:
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, onerror=rmtree_onerror)
        else:
            if os.path.exists(path):
                os.chmod(path, 0o666)
                os.remove(path)
    except Exception:
        # best effort: try chmod recursively then retry
        try:
            if os.path.isdir(path):
                for dirpath, dirs, files in os.walk(path):
                    for name in files:
                        fp = os.path.join(dirpath, name)
                        with suppress(Exception):
                            os.chmod(fp, 0o666)
                with suppress(Exception):
                    shutil.rmtree(path, onerror=rmtree_onerror)
            else:
                with suppress(Exception):
                    os.chmod(path, 0o666)
                    os.remove(path)
        except Exception:
            pass

def attempt_kill_by_pid(pid):
    with suppress(Exception):
        if os.name == "nt":
            subprocess.run(["taskkill", "/PID", str(pid), "/F"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        else:
            os.kill(pid, 9)

def best_effort_stop_mendel(project_root):
    """
    Attempts to stop Mendel Desktop processes/windows.
    Tries in this order: PID file (apps/mendel.pid), taskkill by window title, pkill -f 'Mendel Desktop'
    """
    write_log(project_root, "Attempting to stop Mendel Desktop...")
    # 1) PID file in project root or apps
    candidates = [
        os.path.join(project_root, "mendel.pid"),
        os.path.join(project_root, "apps", "mendel.pid"),
    ]
    for c in candidates:
        try:
            if os.path.exists(c):
                with open(c, "r", encoding="utf-8") as f:
                    pid = int(f.read().strip())
                write_log(project_root, f"Found PID file {c} -> {pid}")
                attempt_kill_by_pid(pid)
                with suppress(Exception):
                    os.remove(c)
                write_log(project_root, f"Killed PID {pid} from {c}")
                return
        except Exception as e:
            write_log(project_root, f"PID kill error: {e}")

    # 2) Windows: try taskkill by window title
    if os.name == "nt":
        try:
            # Try to kill windows whose title equals or contains "Mendel Desktop"
            with suppress(Exception):
                subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq Mendel Desktop'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            # fallback: kill python processes with 'Mendel Desktop' in commandline (best-effort)
            with suppress(Exception):
                subprocess.run(['wmic', 'process', 'where', 'commandline like "%Mendel Desktop%"', 'call', 'terminate'],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, shell=False)
            write_log(project_root, "Attempted Windows taskkill/wmic for Mendel Desktop")
        except Exception as e:
            write_log(project_root, f"Windows kill error: {e}")
    else:
        # Unix: pkill by pattern
        try:
            with suppress(Exception):
                subprocess.run(['pkill', '-f', 'Mendel Desktop'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            write_log(project_root, "Attempted pkill -f 'Mendel Desktop'")
        except Exception as e:
            write_log(project_root, f"Unix pkill error: {e}")

def build_expected_map_from_tree(root_dir):
    """
    Build a mapping of filename -> list of relative paths where that filename exists in the tree.
    Used to find where an existing file (misplaced) should be moved according to the repo structure.
    """
    mapping = {}
    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        for name in filenames + dirnames:
            if name == UPDATE_TEMP_NAME:
                continue
            rel_path = os.path.normpath(os.path.join(rel_dir, name)) if rel_dir != "." else name
            mapping.setdefault(name, []).append(rel_path)
    return mapping

def relocate_misplaced_items(project_root, temp_dir):
    """
    Try to detect files/folders in project_root that are misplaced (same name exists in temp_dir tree)
    and move them into the corresponding location inside temp_dir so the final move will place them correctly.
    This helps preserve user files that reside in wrong locations compared to the repo layout.
    """
    try:
        write_log(project_root, "Relocating misplaced items based on repo structure...")
        expected = build_expected_map_from_tree(temp_dir)
        # list items at project_root (top-level only)
        for name in os.listdir(project_root):
            if name == UPDATE_TEMP_NAME:
                continue
            src = os.path.join(project_root, name)
            # if this name appears in expected with a non-top-level path, move it into temp_dir at expected path
            if name in expected:
                targets = expected[name]
                # prefer targets that are not in root (i.e., subdirs)
                chosen = None
                for t in targets:
                    if os.path.dirname(t) not in ("", "."):
                        chosen = t
                        break
                if chosen is None:
                    # all targets are top-level: leave as-is (will be replaced)
                    continue
                # destination inside temp_dir
                dst = os.path.join(temp_dir, chosen)
                dst_dir = os.path.dirname(dst)
                if not os.path.exists(dst_dir):
                    os.makedirs(dst_dir, exist_ok=True)
                try:
                    # if dst exists, we'll attempt to merge/overwrite carefully
                    if os.path.exists(dst):
                        # move into a subpath to avoid clobbering
                        dst = os.path.join(dst_dir, name)
                    shutil.move(src, dst)
                    write_log(project_root, f"Relocated misplaced {src} -> {dst}")
                except Exception as e:
                    write_log(project_root, f"Failed to relocate {src} -> {dst}: {e}")
    except Exception as e:
        write_log(project_root, f"relocate_misplaced_items error: {e}")

# ---------- Main GUI ----------
class ManagerTool(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ManagerTool")
        self.setStyleSheet("background-color: black;")
        # compact size per request
        self.setFixedSize(400, 220)

        # small logo M
        self.logo = QLabel("M", self)
        self.logo.setFont(QFont("Arial", 80, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.move(10, 10)

        # central panel
        self.panel = QFrame(self)
        self.panel.setStyleSheet(PANEL_STYLE)
        self.panel.setGeometry(100, 40, 280, 140)

        self.layout = QVBoxLayout(self.panel)
        self.layout.setAlignment(Qt.AlignCenter)
        self.layout.setSpacing(10)

        self.status_label = QLabel("Vérification de la version...")
        self.status_label.setStyleSheet(LABEL_STYLE)
        self.layout.addWidget(self.status_label)

        # update button (only visible if update available)
        self.update_btn = QPushButton("Mettre à jour maintenant")
        self.update_btn.setStyleSheet(BUTTON_STYLE)
        self.update_btn.setVisible(False)
        self.update_btn.clicked.connect(self.perform_update)
        self.layout.addWidget(self.update_btn)

        # close button for manual close when up-to-date or fetch failed
        self.close_btn = QPushButton("Fermer")
        self.close_btn.setStyleSheet(BUTTON_STYLE)
        self.close_btn.setVisible(False)
        self.close_btn.clicked.connect(self.close)
        self.layout.addWidget(self.close_btn)

        QTimer.singleShot(100, self.check_version)

    # ---------- version helpers ----------
    def read_local_version(self):
        try:
            with open(LOCAL_VERSION_FILE, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception:
            return "0.0.0"

    def fetch_remote_version(self):
        try:
            r = requests.get(GITHUB_RAW_VERSION_URL, timeout=6)
            if r.status_code == 200:
                return r.text.strip()
        except Exception:
            pass
        return None

    def version_is_outdated(self, local, remote):
        try:
            return parse_version(remote) > parse_version(local)
        except Exception:
            return False

    def check_version(self):
        local = self.read_local_version()
        remote = self.fetch_remote_version()
        if not remote:
            self.status_label.setText(f"Impossible de récupérer la version distante.\nVersion locale : {local}")
            self.close_btn.setVisible(True)
            return
        if self.version_is_outdated(local, remote):
            self.status_label.setText(f"Version actuelle : {local}\nNouvelle version : {remote}")
            self.update_btn.setVisible(True)
        else:
            self.status_label.setText(f"Système à jour\nVersion : {local}")
            self.close_btn.setVisible(True)

    # ---------- update flow ----------
    def perform_update(self):
        self.update_btn.setEnabled(False)
        self.status_label.setText("Préparation de la mise à jour...")
        QTimer.singleShot(100, self.download_and_replace)

    def download_and_replace(self):
        """
        1. Determine project_root (parent of apps)
        2. Change cwd to parent of project_root for safety
        3. Clone into temp_dir
        4. Relocate misplaced items (based on repo structure) into temp_dir
        5. Best-effort stop Mendel Desktop
        6. Delete project_root contents (except temp)
        7. Move new files, clean temp
        8. Launch boot.py and exit
        """
        project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        write_log(project_root, "=== update started ===")
        write_log(project_root, f"Project root: {project_root}")

        # Step 0: change working directory to avoid deleting cwd
        safe_cwd = os.path.abspath(os.path.join(project_root, ".."))
        try:
            os.chdir(safe_cwd)
        except Exception:
            pass
        write_log(project_root, f"Changed cwd to safe location: {safe_cwd}")

        temp_dir = os.path.join(project_root, UPDATE_TEMP_NAME)
        try:
            # cleanup old temp if exists
            if os.path.exists(temp_dir):
                write_log(project_root, "Removing existing temp_dir")
                safe_remove(temp_dir)

            # clone repository branch
            write_log(project_root, f"Cloning {GITHUB_REPO_URL} branch {GITHUB_BRANCH} into {temp_dir}")
            subprocess.run(["git", "clone", "--branch", GITHUB_BRANCH, GITHUB_REPO_URL, temp_dir], check=True)

            # relocate misplaced items (try to preserve user files placed in wrong locations)
            relocate_misplaced_items(project_root, temp_dir)

            # attempt to stop Mendel Desktop to release locks
            best_effort_stop_mendel(project_root)

            # remove everything in project_root except temp_dir
            write_log(project_root, "Removing old project files (best-effort)...")
            for item in os.listdir(project_root):
                if item == UPDATE_TEMP_NAME:
                    continue
                full = os.path.join(project_root, item)
                write_log(project_root, f"Removing {full}")
                safe_remove(full)

            # move contents from temp_dir to project_root
            write_log(project_root, "Moving new files into project root...")
            for item in os.listdir(temp_dir):
                src = os.path.join(temp_dir, item)
                dst = os.path.join(project_root, item)
                # use shutil.move which handles cross-device moves
                shutil.move(src, dst)
                write_log(project_root, f"Moved {src} -> {dst}")

            # cleanup temp_dir
            if os.path.exists(temp_dir):
                safe_remove(temp_dir)

            write_log(project_root, "Update completed successfully")
            self.status_label.setText("Mise à jour terminée. Démarrage du système...")
            QTimer.singleShot(800, lambda: self.launch_boot_and_close_mendel(project_root))

        except subprocess.CalledProcessError as e:
            write_log(project_root, f"Git clone failed: {e}")
            self.status_label.setText(f"Erreur git clone : {e}")
            self.update_btn.setEnabled(True)
        except Exception as e:
            tb = traceback.format_exc()
            write_log(project_root, f"Update error: {e}")
            write_log(project_root, tb)
            self.status_label.setText(f"Erreur : {e}")
            self.update_btn.setEnabled(True)

    # ---------- launch and finish ----------
    def launch_boot_and_close_mendel(self, project_root):
        try:
            boot_path = os.path.join(project_root, BOOT_SCRIPT)
            if not os.path.exists(boot_path):
                self.status_label.setText("boot.py introuvable après mise à jour.")
                write_log(project_root, "boot.py not found at: " + boot_path)
                return
            # start boot.py in its directory
            subprocess.Popen([sys.executable, boot_path], cwd=os.path.dirname(boot_path))
            write_log(project_root, f"Launched boot.py: {boot_path}")
        except Exception as e:
            write_log(project_root, f"Failed to launch boot.py: {e}")
            self.status_label.setText(f"Erreur lancement boot.py : {e}")
            return

        # attempt to close Mendel desktop
        best_effort_stop_mendel(project_root)

        # close ManagerTool
        QTimer.singleShot(300, lambda: QApplication.quit())

# ---------- Entry point ----------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = ManagerTool()
    w.show()
    sys.exit(app.exec_())

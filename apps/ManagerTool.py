#!/usr/bin/env python3
import sys
import os
import shutil
import subprocess
import requests
import traceback
import stat
import hashlib
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
            with suppress(Exception):
                subprocess.run(['taskkill', '/F', '/FI', 'WINDOWTITLE eq Mendel Desktop'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
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

def sha256_of_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def build_tree_info(root_dir):
    """
    Walk root_dir and return:
      - files_info: dict relative_path -> sha256 (files only)
      - dirs_set: set of relative_dir paths
    Relative paths use '/' as separator and are rooted at '' (top-level entries have name)
    """
    files_info = {}
    dirs_set = set()
    for dirpath, dirnames, filenames in os.walk(root_dir):
        rel_dir = os.path.relpath(dirpath, root_dir)
        if rel_dir == ".":
            rel_dir = ""
        else:
            rel_dir = rel_dir.replace(os.path.sep, "/")
            dirs_set.add(rel_dir)
        for d in dirnames:
            rel = os.path.join(rel_dir, d).lstrip("./").replace(os.path.sep, "/")
            dirs_set.add(rel)
        for fname in filenames:
            if fname == UPDATE_TEMP_NAME:
                continue
            rel = os.path.join(rel_dir, fname).lstrip("./").replace(os.path.sep, "/")
            full = os.path.join(dirpath, fname)
            try:
                files_info[rel] = sha256_of_file(full)
            except Exception:
                files_info[rel] = None
    return files_info, dirs_set

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
        Strict update process:
        - clone repo branch into temp_dir
        - build tree info (relative paths + hashes) from temp_dir
        - remove old content (everything except temp_dir)
        - move each file/dir from temp_dir to project_root one by one,
          verifying file hashes after move
        - if any verification fails, abort and log; temp_dir retained for debug
        - if all OK, cleanup temp_dir, launch boot.py and exit
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

            # build tree info from temp_dir
            write_log(project_root, "Building tree info from cloned repo...")
            temp_files, temp_dirs = build_tree_info(temp_dir)
            write_log(project_root, f"Cloned files: {len(temp_files)}, dirs: {len(temp_dirs)}")

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

            # now move contents from temp_dir to project_root ONE BY ONE with verification
            write_log(project_root, "Moving and verifying files one by one...")
            # First create all directories
            dirs_sorted = sorted(temp_dirs, key=lambda x: x.count("/"))  # parents first
            for drel in dirs_sorted:
                dst_dir = os.path.join(project_root, drel.replace("/", os.path.sep))
                if not os.path.exists(dst_dir):
                    try:
                        os.makedirs(dst_dir, exist_ok=True)
                        write_log(project_root, f"Created dir {dst_dir}")
                    except Exception as e:
                        write_log(project_root, f"Failed to create dir {dst_dir}: {e}")
                        raise

            # Then move files
            for rel_path, original_hash in temp_files.items():
                src = os.path.join(temp_dir, rel_path.replace("/", os.path.sep))
                dst = os.path.join(project_root, rel_path.replace("/", os.path.sep))
                dst_dir = os.path.dirname(dst)
                if not os.path.exists(dst_dir):
                    try:
                        os.makedirs(dst_dir, exist_ok=True)
                    except Exception as e:
                        write_log(project_root, f"Failed to create parent dir {dst_dir} for {dst}: {e}")
                        raise
                try:
                    # move file
                    shutil.move(src, dst)
                    write_log(project_root, f"Moved file {src} -> {dst}")
                except Exception as e:
                    write_log(project_root, f"Failed to move {src} -> {dst}: {e}")
                    raise

                # verify hash
                try:
                    moved_hash = sha256_of_file(dst)
                except Exception as e:
                    write_log(project_root, f"Failed to hash moved file {dst}: {e}")
                    raise
                if original_hash is None:
                    write_log(project_root, f"Warning: original hash missing for {rel_path}, cannot verify precisely")
                elif moved_hash != original_hash:
                    write_log(project_root, f"Hash mismatch for {rel_path}: original {original_hash} vs moved {moved_hash}")
                    raise RuntimeError(f"Hash mismatch for {rel_path}")

            # After all moves, ensure no leftover files under temp_dir (should be empty)
            remaining = []
            for root, dirs, files in os.walk(temp_dir):
                for f in files:
                    remaining.append(os.path.join(root, f))
                for d in dirs:
                    remaining.append(os.path.join(root, d))
            if remaining:
                write_log(project_root, f"Warning: leftover items in temp_dir: {remaining}")

            # cleanup temp_dir
            if os.path.exists(temp_dir):
                safe_remove(temp_dir)

            write_log(project_root, "Update completed successfully and verified")
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
            # keep temp_dir for inspection, do not remove it if verification failed
            self.status_label.setText(f"Erreur : {e}\nConsulte update.log")
            self.update_btn.setEnabled(True)
            return

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

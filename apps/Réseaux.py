#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Réseaux - Application PyQt5 (Wi‑Fi + Bluetooth)
- Multi-plateforme : Windows / macOS / Linux
- Exécutions système robustes : lecture en bytes + décodage sécurisé (errors="replace")
- Tâches en arrière-plan pour éviter de bloquer l'UI
- Affiche réseaux connus / disponibles / connecté et appareils Bluetooth appairés / disponibles
"""

import sys
import os
import shlex
import subprocess
import locale
import logging
from dataclasses import dataclass
from typing import List, Optional, Set, Dict

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QListWidget, QListWidgetItem, QTabWidget, QMessageBox, QProgressBar,
    QInputDialog
)
from PyQt5.QtCore import Qt, QTimer, QObject, pyqtSignal, QRunnable, QThreadPool
from PyQt5.QtGui import QFont

# ---------------- logging ----------------
LOGFILE = "reseaux_safe.log"
logging.basicConfig(level=logging.INFO, filename=LOGFILE, encoding="utf-8",
                    format="%(asctime)s [%(levelname)s] %(message)s")
logging.info("Démarrage application Réseaux (safe)")

# ---------------- styles ----------------
PANEL_STYLE = "QFrame { background-color: #2f2f2f; border-radius: 10px; }"
TITLE_STYLE = "color: white; font-size: 16px; font-weight: bold;"
SUB_STYLE = "color: #cccccc; font-size: 12px;"
BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: white;
    border: 1px solid #616161;
    padding: 6px 10px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #5c5c5c; }
QPushButton:pressed { background-color: #474747; }
"""
LIST_STYLE = """
QListWidget {
    background-color: #1f1f1f;
    color: #eaeaea;
    border: 1px solid #3d3d3d;
    border-radius: 6px;
}
QListWidget::item:selected { background: #3a3a3a; }
"""

# ---------------- background worker infra ----------------
class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)

class RunnableTask(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(res)
        except Exception as e:
            logging.exception("Erreur tâche background")
            self.signals.error.emit(str(e))

# ---------------- utilitaire exécution commande (safe decode) ----------------
def _safe_decode(b: bytes) -> str:
    """Décoder bytes en texte en essayant l'encodage système, fallback utf-8, puis replace."""
    if b is None:
        return ""
    enc = locale.getpreferredencoding(False) or "utf-8"
    try:
        return b.decode(enc)
    except Exception:
        try:
            return b.decode("utf-8")
        except Exception:
            return b.decode(enc, errors="replace")

def run_cmd(cmd, shell=False, timeout=8):
    """
    Execute a command and return (stdout_text, stderr_text).
    Always returns strings; never raises UnicodeDecodeError.
    """
    try:
        if isinstance(cmd, str) and not shell:
            cmd_list = shlex.split(cmd)
        else:
            cmd_list = cmd
        proc = subprocess.run(
            cmd_list,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
            shell=shell
        )
        stdout_bytes = proc.stdout or b""
        stderr_bytes = proc.stderr or b""
        stdout = _safe_decode(stdout_bytes)
        stderr = _safe_decode(stderr_bytes)
        return stdout, stderr
    except subprocess.TimeoutExpired:
        return "", "timeout"
    except FileNotFoundError:
        return "", "not_found"
    except Exception as e:
        return "", str(e)

# ---------------- modèle Wi‑Fi ----------------
@dataclass
class WifiNetwork:
    ssid: str
    signal: Optional[int] = None
    security: Optional[str] = None

# ---------------- backend Wi‑Fi (robuste) ----------------
class WifiBackend:
    def __init__(self):
        self.platform = sys.platform
        logging.info(f"WifiBackend initialisé pour: {self.platform}")

    def _run(self, cmd, shell=False, timeout=8) -> str:
        out, err = run_cmd(cmd, shell=shell, timeout=timeout)
        if err and err not in ("", "timeout", "not_found"):
            logging.debug(f"stderr for '{cmd}': {err.strip()}")
        return out

    def current_connection(self) -> Optional[str]:
        try:
            if self.platform.startswith("win"):
                out = self._run("netsh wlan show interfaces", shell=True)
                for line in out.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(":", 1)[-1].strip()
                        return ssid or None
                return None
            elif self.platform.startswith("darwin"):
                out = self._run("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I")
                for line in out.splitlines():
                    if " SSID:" in line:
                        return line.split("SSID:")[-1].strip() or None
                return None
            else:
                out = self._run("nmcli -t -f ACTIVE,SSID dev wifi")
                for line in out.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[0] == "yes":
                        return parts[1]
                return None
        except Exception:
            logging.exception("current_connection")
            return None

    def scan_networks(self) -> List[WifiNetwork]:
        nets: List[WifiNetwork] = []
        try:
            if self.platform.startswith("win"):
                out = self._run("netsh wlan show networks mode=Bssid", shell=True)
                ssid = None; signal = None; security = None
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("SSID"):
                        ssid = line.split(":", 1)[-1].strip()
                        signal = None; security = None
                    elif line.startswith("Signal"):
                        val = line.split(":", 1)[-1].strip().replace("%", "")
                        signal = int(val) if val.isdigit() else None
                    elif line.lower().startswith("authentication") or "Type de sécurité" in line:
                        security = line.split(":", 1)[-1].strip()
                    elif ssid and line == "":
                        nets.append(WifiNetwork(ssid=ssid, signal=signal, security=security))
                        ssid = None
                if ssid:
                    nets.append(WifiNetwork(ssid=ssid, signal=signal, security=security))
            elif self.platform.startswith("darwin"):
                out = self._run("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -s")
                for i, line in enumerate(out.splitlines()):
                    if i == 0 or not line.strip():
                        continue
                    parts = line.split()
                    if len(parts) >= 1:
                        ssid = parts[0]
                        signal = None
                        try:
                            rssi = int(parts[2])
                            signal = max(0, min(100, int((rssi + 90) * (100 / 60))))
                        except Exception:
                            pass
                        security = " ".join(parts[7:]) if len(parts) >= 8 else None
                        nets.append(WifiNetwork(ssid=ssid, signal=signal, security=security))
            else:
                out = self._run("nmcli -t -f SSID,SIGNAL,SECURITY dev wifi")
                for line in out.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 3:
                        ssid = parts[0].strip() or "(hidden)"
                        sig = parts[1].strip()
                        sec = parts[2].strip()
                        signal = int(sig) if sig.isdigit() else None
                        nets.append(WifiNetwork(ssid=ssid, signal=signal, security=sec))
            logging.info(f"scan_networks trouvé {len(nets)} réseaux")
            return nets
        except Exception:
            logging.exception("scan_networks")
            return nets

    def known_profiles(self) -> Set[str]:
        known = set()
        try:
            if self.platform.startswith("win"):
                out = self._run("netsh wlan show profiles", shell=True)
                for line in out.splitlines():
                    if "Profil Tous les utilisateurs" in line or "All User Profile" in line:
                        parts = line.split(":", 1)
                        if len(parts) == 2:
                            known.add(parts[1].strip())
            elif self.platform.startswith("darwin"):
                out = self._run("/usr/sbin/networksetup -listpreferredwirelessnetworks en0")
                for i, line in enumerate(out.splitlines()):
                    if i == 0:
                        continue
                    name = line.strip()
                    if name:
                        known.add(name)
            else:
                out = self._run("nmcli -t -f NAME connection show")
                for line in out.splitlines():
                    name = line.strip()
                    if name:
                        known.add(name)
        except Exception:
            logging.exception("known_profiles")
        return known

    def connect(self, ssid: str, password: Optional[str]) -> bool:
        try:
            logging.info(f"Tentative connexion à {ssid}")
            if self.platform.startswith("win"):
                out = self._run(f'netsh wlan connect name="{ssid}" ssid="{ssid}"', shell=True)
                ok = ("completed successfully" in out.lower()) or ("connect request was completed" in out.lower())
                return ok
            elif self.platform.startswith("darwin"):
                ports = self._run("networksetup -listallhardwareports")
                device = None; current_port = None
                for line in ports.splitlines():
                    if line.startswith("Hardware Port: Wi-Fi") or line.startswith("Hardware Port: AirPort"):
                        current_port = "Wi-Fi"
                    if line.startswith("Device:") and current_port:
                        device = line.split(":", 1)[-1].strip()
                        break
                if not device:
                    logging.warning("Interface Wi‑Fi non trouvée (mac)")
                    return False
                if password:
                    out = self._run(f'networksetup -setairportnetwork {device} "{ssid}" "{password}"')
                else:
                    out = self._run(f'networksetup -setairportnetwork {device} "{ssid}"')
                return out.strip() == ""
            else:
                if password:
                    out = self._run(f'nmcli dev wifi connect "{ssid}" password "{password}"')
                else:
                    out = self._run(f'nmcli dev wifi connect "{ssid}"')
                ok = ("successfully activated" in out.lower()) or ("success" in out.lower())
                return ok
        except Exception:
            logging.exception("connect")
            return False

    def disconnect(self) -> bool:
        try:
            logging.info("Déconnexion Wi‑Fi demandée")
            if self.platform.startswith("win"):
                out = self._run("netsh wlan disconnect", shell=True)
                return "disconnected" in out.lower()
            elif self.platform.startswith("darwin"):
                ports = self._run("networksetup -listallhardwareports")
                device = None; current_port = None
                for line in ports.splitlines():
                    if line.startswith("Hardware Port: Wi-Fi") or line.startswith("Hardware Port: AirPort"):
                        current_port = "Wi-Fi"
                    if line.startswith("Device:") and current_port:
                        device = line.split(":", 1)[-1].strip()
                        break
                if not device:
                    return False
                out1 = self._run(f'networksetup -setairportpower {device} off')
                out2 = self._run(f'networksetup -setairportpower {device} on')
                return True if (out1 is not None and out2 is not None) else False
            else:
                out = self._run("nmcli con show --active")
                ssids = []
                for line in out.splitlines():
                    parts = line.split()
                    if parts:
                        ssids.append(parts[0])
                ok_all = True
                for name in ssids:
                    o = self._run(f"nmcli con down id {shlex.quote(name)}")
                    ok_one = ("success" in o.lower()) or ("deactivated" in o.lower())
                    ok_all = ok_all and ok_one
                return ok_all
        except Exception:
            logging.exception("disconnect")
            return False

# ---------------- Bluetooth scan (best-effort) ----------------
def scan_bluetooth() -> Dict[str, Set[str]]:
    devices = {"paired": set(), "available": set()}
    try:
        if sys.platform.startswith("win"):
            ps_cmd = 'powershell -Command "Get-PnpDevice -Class Bluetooth | Where-Object { $_.Status -eq \'OK\' } | Select-Object -ExpandProperty FriendlyName"'
            out, err = run_cmd(ps_cmd, shell=True)
            if out:
                for line in out.splitlines():
                    name = line.strip()
                    if name:
                        devices["paired"].add(name)
        elif sys.platform.startswith("darwin"):
            out, err = run_cmd(["system_profiler", "SPBluetoothDataType"], timeout=8)
            if out:
                for line in out.splitlines():
                    if ":" in line and not line.startswith(" "):
                        name = line.split(":", 1)[0].strip()
                        if name and len(name) < 60:
                            devices["paired"].add(name)
        else:
            out, err = run_cmd(["bluetoothctl", "paired-devices"])
            if out:
                for line in out.splitlines():
                    if line.startswith("Device"):
                        parts = line.split(" ", 2)
                        if len(parts) >= 3:
                            devices["paired"].add(parts[2].strip())
            run_cmd(["bluetoothctl", "scan", "on"], timeout=3)
            out2, err2 = run_cmd(["bluetoothctl", "devices"])
            if out2:
                for line in out2.splitlines():
                    if line.startswith("Device"):
                        parts = line.split(" ", 2)
                        if len(parts) >= 3:
                            devices["available"].add(parts[2].strip())
            run_cmd(["bluetoothctl", "scan", "off"], timeout=2)
    except Exception:
        logging.exception("scan_bluetooth")
    return devices

# ---------------- UI principale ----------------
class ReseauxApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Réseaux")
        self.setStyleSheet("background-color: #0f0f0f;")
        self.setMinimumSize(900, 600)
        self.threadpool = QThreadPool.globalInstance()
        self.backend = WifiBackend()

        main = QVBoxLayout(self)
        main.setContentsMargins(14, 14, 14, 14)
        main.setSpacing(10)

        header = QFrame()
        header.setStyleSheet(PANEL_STYLE)
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(12, 8, 12, 8)

        title = QLabel("Réseaux")
        title.setStyleSheet(TITLE_STYLE)
        header_layout.addWidget(title)
        header_layout.addStretch()
        self.os_label = QLabel(self._platform_label())
        self.os_label.setStyleSheet(SUB_STYLE)
        header_layout.addWidget(self.os_label)
        main.addWidget(header)

        # Tabs
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet("QTabWidget::pane { border: none; } QTabBar::tab { background:#2f2f2f; color:white; padding:8px; } QTabBar::tab:selected { background:#3a3a3a; }")
        main.addWidget(self.tabs, 1)

        # Wi‑Fi tab
        wifi_frame = QFrame()
        wifi_frame.setStyleSheet(PANEL_STYLE)
        wifi_layout = QVBoxLayout(wifi_frame)
        wifi_layout.setContentsMargins(12, 12, 12, 12)
        wifi_layout.setSpacing(8)

        wifi_title = QLabel("Wi‑Fi")
        wifi_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        wifi_layout.addWidget(wifi_title)

        self.wifi_list = QListWidget()
        self.wifi_list.setStyleSheet(LIST_STYLE)
        wifi_layout.addWidget(self.wifi_list, 1)

        wifi_controls = QHBoxLayout()
        self.wifi_refresh_btn = QPushButton("Rafraîchir")
        self.wifi_refresh_btn.setStyleSheet(BUTTON_STYLE)
        self.wifi_refresh_btn.clicked.connect(self.refresh_wifi)
        wifi_controls.addWidget(self.wifi_refresh_btn)

        self.connect_selected_btn = QPushButton("Se connecter au réseau sélectionné")
        self.connect_selected_btn.setStyleSheet(BUTTON_STYLE)
        self.connect_selected_btn.clicked.connect(self.connect_selected)
        wifi_controls.addWidget(self.connect_selected_btn)

        self.disconnect_btn = QPushButton("Se déconnecter")
        self.disconnect_btn.setStyleSheet(BUTTON_STYLE)
        self.disconnect_btn.clicked.connect(self.disconnect)
        wifi_controls.addWidget(self.disconnect_btn)

        self.wifi_progress = QProgressBar()
        self.wifi_progress.setMaximum(0)
        self.wifi_progress.setVisible(False)
        self.wifi_progress.setFixedHeight(14)
        wifi_controls.addWidget(self.wifi_progress, 1)

        wifi_layout.addLayout(wifi_controls)
        self.tabs.addTab(wifi_frame, "Wi‑Fi")

        # Bluetooth tab
        bt_frame = QFrame()
        bt_frame.setStyleSheet(PANEL_STYLE)
        bt_layout = QVBoxLayout(bt_frame)
        bt_layout.setContentsMargins(12, 12, 12, 12)
        bt_layout.setSpacing(8)

        bt_title = QLabel("Bluetooth")
        bt_title.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        bt_layout.addWidget(bt_title)

        self.bt_list = QListWidget()
        self.bt_list.setStyleSheet(LIST_STYLE)
        bt_layout.addWidget(self.bt_list, 1)

        bt_controls = QHBoxLayout()
        self.bt_refresh_btn = QPushButton("Rafraîchir")
        self.bt_refresh_btn.setStyleSheet(BUTTON_STYLE)
        self.bt_refresh_btn.clicked.connect(self.refresh_bt)
        bt_controls.addWidget(self.bt_refresh_btn)

        self.bt_progress = QProgressBar()
        self.bt_progress.setMaximum(0)
        self.bt_progress.setVisible(False)
        self.bt_progress.setFixedHeight(14)
        bt_controls.addWidget(self.bt_progress, 1)

        bt_layout.addLayout(bt_controls)
        self.tabs.addTab(bt_frame, "Bluetooth")

        # Footer
        footer = QFrame()
        footer.setStyleSheet(PANEL_STYLE)
        footer_layout = QHBoxLayout(footer)
        footer_layout.setContentsMargins(12, 8, 12, 8)
        self.status = QLabel("Prêt")
        self.status.setStyleSheet(SUB_STYLE)
        footer_layout.addWidget(self.status)
        footer_layout.addStretch()
        self.auto_refresh_btn = QPushButton("Auto refresh 10s")
        self.auto_refresh_btn.setStyleSheet(BUTTON_STYLE)
        self.auto_refresh_btn.setCheckable(True)
        self.auto_refresh_btn.toggled.connect(self.toggle_auto_refresh)
        footer_layout.addWidget(self.auto_refresh_btn)
        main.addWidget(footer)

        # timers
        self.auto_timer = QTimer()
        self.auto_timer.setInterval(10000)
        self.auto_timer.timeout.connect(self._auto_refresh)

        # initial load
        QTimer.singleShot(200, self.refresh_all)

    def _platform_label(self):
        if sys.platform.startswith("win"):
            return "Windows"
        if sys.platform.startswith("darwin"):
            return "macOS"
        return "Linux/Unix"

    def toggle_auto_refresh(self, checked):
        if checked:
            self.auto_timer.start()
            self.auto_refresh_btn.setText("Auto refresh ON")
            self.status.setText("Auto refresh activé")
        else:
            self.auto_timer.stop()
            self.auto_refresh_btn.setText("Auto refresh 10s")
            self.status.setText("Auto refresh désactivé")

    def _auto_refresh(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.refresh_wifi()
        else:
            self.refresh_bt()

    def refresh_all(self):
        self.refresh_wifi()
        self.refresh_bt()

    # ---------- Wi‑Fi ----------
    def refresh_wifi(self):
        self.wifi_list.clear()
        self.wifi_progress.setVisible(True)
        task = RunnableTask(self._task_scan_wifi)
        task.signals.finished.connect(self._on_wifi_result)
        task.signals.error.connect(self._on_worker_error)
        self.threadpool.start(task)
        self.status.setText("Scan Wi‑Fi en cours...")

    def _task_scan_wifi(self):
        nets = self.backend.scan_networks()
        known = self.backend.known_profiles()
        connected = self.backend.current_connection()
        return {"nets": nets, "known": known, "connected": connected}

    def _on_wifi_result(self, res):
        self.wifi_progress.setVisible(False)
        if not isinstance(res, dict):
            self.wifi_list.addItem("Erreur: format inattendu")
            self.status.setText("Erreur Wi‑Fi")
            return
        nets: List[WifiNetwork] = res.get("nets", [])
        known: Set[str] = res.get("known", set())
        connected: Optional[str] = res.get("connected", None)

        seen = set()
        if connected:
            item = QListWidgetItem(f"🔵 {connected} — Connecté")
            item.setData(Qt.UserRole, connected)
            item.setToolTip("Réseau actuellement connecté")
            self.wifi_list.addItem(item)
            seen.add(connected)

        for k in sorted(known):
            if k in seen:
                continue
            item = QListWidgetItem(f"🟢 {k} — Enregistré")
            item.setData(Qt.UserRole, k)
            item.setToolTip("Profil enregistré (mot de passe connu)")
            self.wifi_list.addItem(item)
            seen.add(k)

        for net in sorted(nets, key=lambda n: (n.ssid or "").lower()):
            ssid = net.ssid
            if ssid in seen:
                continue
            label = f"⚪ {ssid} — Disponible"
            if ssid in known:
                label = f"🟢 {ssid} — Disponible et Enregistré"
            if net.signal is not None:
                label += f" | Signal: {net.signal}%"
            if net.security:
                label += f" | {net.security}"
            item = QListWidgetItem(label)
            item.setData(Qt.UserRole, ssid)
            self.wifi_list.addItem(item)
            seen.add(ssid)

        self.status.setText(f"Wi‑Fi: {len(seen)} réseau(x) listé(s)")

    def connect_selected(self):
        item = self.wifi_list.currentItem()
        if not item:
            QMessageBox.information(self, "Wi‑Fi", "Sélectionne un réseau dans la liste.")
            return
        ssid = item.data(Qt.UserRole)
        if not ssid:
            QMessageBox.warning(self, "Wi‑Fi", "Impossible de déterminer le SSID sélectionné.")
            return
        pwd, ok = QInputDialog.getText(self, "Mot de passe", f"Mot de passe pour {ssid} (laisser vide si ouvert):")
        if not ok:
            return
        password = pwd.strip() or None
        self.wifi_progress.setVisible(True)
        task = RunnableTask(self._task_connect, ssid, password)
        task.signals.finished.connect(self._on_connect_result)
        task.signals.error.connect(self._on_worker_error)
        self.threadpool.start(task)
        self.status.setText(f"Tentative de connexion à {ssid}...")

    def _task_connect(self, ssid, password):
        ok = self.backend.connect(ssid, password)
        return {"ssid": ssid, "ok": ok}

    def _on_connect_result(self, res):
        self.wifi_progress.setVisible(False)
        ssid = res.get("ssid")
        ok = res.get("ok", False)
        if ok:
            QMessageBox.information(self, "Wi‑Fi", f"Connecté à {ssid}.")
            logging.info(f"Connecté à {ssid}")
        else:
            QMessageBox.warning(self, "Wi‑Fi", f"Échec de connexion à {ssid}.")
            logging.warning(f"Échec connexion à {ssid}")
        self.refresh_wifi()

    def disconnect(self):
        self.wifi_progress.setVisible(True)
        task = RunnableTask(self._task_disconnect)
        task.signals.finished.connect(self._on_disconnect_result)
        task.signals.error.connect(self._on_worker_error)
        self.threadpool.start(task)
        self.status.setText("Déconnexion en cours...")

    def _task_disconnect(self):
        ok = self.backend.disconnect()
        return {"ok": ok}

    def _on_disconnect_result(self, res):
        self.wifi_progress.setVisible(False)
        ok = res.get("ok", False)
        if ok:
            QMessageBox.information(self, "Wi‑Fi", "Déconnecté.")
        else:
            QMessageBox.warning(self, "Wi‑Fi", "Échec de la déconnexion.")
        self.refresh_wifi()

    # ---------- Bluetooth ----------
    def refresh_bt(self):
        self.bt_list.clear()
        self.bt_progress.setVisible(True)
        task = RunnableTask(scan_bluetooth)
        task.signals.finished.connect(self._on_bt_result)
        task.signals.error.connect(self._on_worker_error)
        self.threadpool.start(task)
        self.status.setText("Scan Bluetooth en cours...")

    def _on_bt_result(self, res):
        self.bt_progress.setVisible(False)
        if not isinstance(res, dict):
            self.bt_list.addItem("Erreur: format inattendu")
            self.status.setText("Erreur Bluetooth")
            return
        paired = res.get("paired", set())
        available = res.get("available", set())
        seen = set()
        for p in sorted(paired):
            item = QListWidgetItem(f"🔒 {p} — Appairé")
            self.bt_list.addItem(item)
            seen.add(p)
        for a in sorted(available):
            if a in seen:
                continue
            item = QListWidgetItem(f"⚪ {a} — Disponible")
            self.bt_list.addItem(item)
            seen.add(a)
        self.status.setText(f"Bluetooth: {len(seen)} appareil(s) listé(s)")

    def _on_worker_error(self, err):
        logging.error(f"Tâche background erreur: {err}")
        QMessageBox.warning(self, "Erreur tâche", f"Une erreur est survenue :\n{err}")
        self.status.setText("Erreur tâche en arrière-plan")
        self.wifi_progress.setVisible(False)
        self.bt_progress.setVisible(False)

# ---------------- main ----------------
def main():
    app = QApplication(sys.argv)
    app.setStyleSheet("QToolTip { color: #ffffff; background-color: #2f2f2f; border: 1px solid #3d3d3d; }")
    w = ReseauxApp()
    w.show()
    logging.info("Interface lancée")
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()

import sys
import subprocess
import shlex
import logging
from dataclasses import dataclass
from typing import List, Optional

from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout,
    QListWidget, QPushButton, QLabel, QLineEdit, QInputDialog, QMessageBox
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# --------------------------------- LOGGING ---------------------------------
logging.basicConfig(
    filename="INT.log",
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(message)s",
    encoding="utf-8"
)
logging.info("=== Démarrage de l'application Internet (Wi‑Fi) — Mendel ===")

# --------------------------------- STYLE MENDEL ---------------------------------
APP_STYLE = """
QMainWindow, QWidget { background-color: #0b0b0b; color: #fff; }
QPushButton, QLineEdit {
    background-color: #2f2f2f;
    color: #fff;
    border: 1px solid #444;
    padding: 6px 10px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #3a3a3a; }
QPushButton:pressed { background-color: #1f1f1f; }
QLabel { color: #ddd; }
QListWidget {
    background: transparent;
    color: #ffffff;
    border: 1px solid #444;
    padding: 6px;
    border-radius: 6px;
}
QListWidget::item { padding: 6px 8px; }
QListWidget::item:selected { background: rgba(255,255,255,0.08); }
"""

# --------------------------------- MODELES ---------------------------------
@dataclass
class WifiNetwork:
    ssid: str
    signal: Optional[int] = None     # 0-100
    security: Optional[str] = None   # WPA2, Open, etc.

# --------------------------------- BACKEND ---------------------------------
class WifiBackend:
    def __init__(self):
        self.platform = sys.platform
        logging.info(f"Backend initialisé pour plateforme: {self.platform}")

    # --- Helpers ---
    def _run(self, cmd: str) -> str:
        logging.debug(f"Exécution commande: {cmd}")
        try:
            if self.platform.startswith("win"):
                result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            else:
                result = subprocess.run(shlex.split(cmd), capture_output=True, text=True)
            stdout = result.stdout or ""
            stderr = result.stderr or ""
            if stderr.strip():
                logging.warning(f"stderr: {stderr.strip()}")
            logging.debug(f"stdout: {stdout.strip()[:500]}")
            return stdout
        except Exception as e:
            logging.error(f"Erreur d'exécution '{cmd}': {e}")
            return f"ERROR: {e}"

    # --- Current connection ---
    def current_connection(self) -> Optional[str]:
        logging.debug("Récupération de la connexion Wi‑Fi actuelle")
        try:
            if self.platform.startswith("win"):
                out = self._run("netsh wlan show interfaces")
                for line in out.splitlines():
                    if "SSID" in line and "BSSID" not in line:
                        ssid = line.split(":", 1)[-1].strip()
                        logging.info(f"Connexion actuelle (win): {ssid}")
                        return ssid or None
                return None
            elif self.platform.startswith("darwin"):
                out = self._run("/System/Library/PrivateFrameworks/Apple80211.framework/Versions/Current/Resources/airport -I")
                for line in out.splitlines():
                    if " SSID:" in line:
                        ssid = line.split("SSID:")[-1].strip()
                        logging.info(f"Connexion actuelle (mac): {ssid}")
                        return ssid or None
                return None
            else:
                out = self._run("nmcli -t -f ACTIVE,SSID dev wifi")
                for line in out.splitlines():
                    parts = line.split(":")
                    if len(parts) >= 2 and parts[0] == "yes":
                        ssid = parts[1]
                        logging.info(f"Connexion actuelle (linux): {ssid}")
                        return ssid
                return None
        except Exception as e:
            logging.error(f"Erreur current_connection: {e}")
            return None

    # --- Scan networks ---
    def scan_networks(self) -> List[WifiNetwork]:
        logging.debug("Scan des réseaux Wi‑Fi disponibles")
        nets: List[WifiNetwork] = []
        try:
            if self.platform.startswith("win"):
                out = self._run("netsh wlan show networks mode=Bssid")
                ssid = None
                signal = None
                security = None
                for line in out.splitlines():
                    line = line.strip()
                    if line.startswith("SSID"):
                        ssid = line.split(":", 1)[-1].strip()
                        signal = None
                        security = None
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
                        except:
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
            logging.info(f"Scan: {len(nets)} réseau(x) trouvé(s)")
            return nets
        except Exception as e:
            logging.error(f"Erreur scan_networks: {e}")
            return nets

    # --- Connect ---
    def connect(self, ssid: str, password: Optional[str]) -> bool:
        logging.info(f"Tentative de connexion à '{ssid}' (mot de passe {'fourni' if password else 'non'})")
        try:
            if self.platform.startswith("win"):
                # Windows: tentative simple avec netsh (peut nécessiter un profil existant)
                out = self._run(f'netsh wlan connect name="{ssid}" ssid="{ssid}"')
                ok = ("completed successfully" in out.lower()) or ("connect request was completed" in out.lower())
                logging.info(f"Résultat connexion (win): {ok}")
                return ok
            elif self.platform.startswith("darwin"):
                ports = self._run("networksetup -listallhardwareports")
                device = None
                current_port = None
                for line in ports.splitlines():
                    if line.startswith("Hardware Port: Wi-Fi") or line.startswith("Hardware Port: AirPort"):
                        current_port = "Wi-Fi"
                    if line.startswith("Device:") and current_port:
                        device = line.split(":", 1)[-1].strip()
                        break
                if not device:
                    logging.error("Interface Wi‑Fi non trouvée sur macOS")
                    return False
                if password:
                    out = self._run(f'networksetup -setairportnetwork {device} "{ssid}" "{password}"')
                else:
                    out = self._run(f'networksetup -setairportnetwork {device} "{ssid}"')
                ok = out.strip() == ""  # souvent vide si succès
                logging.info(f"Résultat connexion (mac): {ok}")
                return ok
            else:
                if password:
                    out = self._run(f'nmcli dev wifi connect "{ssid}" password "{password}"')
                else:
                    out = self._run(f'nmcli dev wifi connect "{ssid}"')
                ok = ("successfully activated" in out.lower()) or ("success" in out.lower())
                logging.info(f"Résultat connexion (linux): {ok}")
                return ok
        except Exception as e:
            logging.error(f"Erreur connect: {e}")
            return False

    # --- Disconnect ---
    def disconnect(self) -> bool:
        logging.info("Déconnexion du Wi‑Fi")
        try:
            if self.platform.startswith("win"):
                out = self._run("netsh wlan disconnect")
                ok = "disconnected" in out.lower()
                logging.info(f"Résultat déconnexion (win): {ok}")
                return ok
            elif self.platform.startswith("darwin"):
                ports = self._run("networksetup -listallhardwareports")
                device = None
                current_port = None
                for line in ports.splitlines():
                    if line.startswith("Hardware Port: Wi-Fi") or line.startswith("Hardware Port: AirPort"):
                        current_port = "Wi-Fi"
                    if line.startswith("Device:") and current_port:
                        device = line.split(":", 1)[-1].strip()
                        break
                if not device:
                    logging.error("Interface Wi‑Fi non trouvée pour déconnexion sur macOS")
                    return False
                out1 = self._run(f'networksetup -setairportpower {device} off')
                out2 = self._run(f'networksetup -setairportpower {device} on')
                ok = True if (out1 is not None and out2 is not None) else False
                logging.info(f"Résultat déconnexion (mac): {ok}")
                return ok
            else:
                # Linux: couper toutes les connexions actives
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
                logging.info(f"Résultat déconnexion (linux): {ok_all}")
                return ok_all
        except Exception as e:
            logging.error(f"Erreur disconnect: {e}")
            return False

# --------------------------------- UI ---------------------------------
class WifiApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Internet (Wi‑Fi) — Mendel")
        self.setMinimumSize(900, 600)

        self.backend = WifiBackend()

        root = QVBoxLayout(self)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        # Header
        header = QHBoxLayout()
        self.title = QLabel("📶 Gestion Wi‑Fi")
        self.title.setFont(QFont("Arial", 12))
        header.addWidget(self.title, 1)

        self.refresh_btn = QPushButton("Rafraîchir")
        self.refresh_btn.clicked.connect(self.refresh)
        header.addWidget(self.refresh_btn)

        self.disconnect_btn = QPushButton("Se déconnecter")
        self.disconnect_btn.clicked.connect(self.do_disconnect)
        header.addWidget(self.disconnect_btn)

        root.addLayout(header)

        # État actuel
        self.status = QLabel("État : inconnu")
        root.addWidget(self.status)

        # Liste réseaux
        self.list = QListWidget()
        self.list.setSelectionMode(self.list.SingleSelection)
        root.addWidget(self.list, 1)

        # Connexion manuelle
        manual = QHBoxLayout()
        self.ssid_input = QLineEdit()
        self.ssid_input.setPlaceholderText("SSID")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        self.pass_input.setPlaceholderText("Mot de passe (laisser vide si réseau ouvert)")
        self.connect_btn = QPushButton("Se connecter")
        self.connect_btn.clicked.connect(self.do_connect_manual)

        manual.addWidget(self.ssid_input, 2)
        manual.addWidget(self.pass_input, 2)
        manual.addWidget(self.connect_btn, 1)
        root.addLayout(manual)

        # Connexion depuis la liste
        actions = QHBoxLayout()
        self.connect_selected_btn = QPushButton("Connecter le réseau sélectionné")
        self.connect_selected_btn.clicked.connect(self.do_connect_selected)
        actions.addWidget(self.connect_selected_btn)
        root.addLayout(actions)

        # Auto-refresh toutes les 15 secondes (désactivable si tu veux)
        self.timer = QTimer(self)
        self.timer.setInterval(15000)
        self.timer.timeout.connect(self.refresh)
        self.timer.start()

        # Initial load
        self.refresh()

    def refresh(self):
        logging.info("Action UI: refresh")
        current = self.backend.current_connection()
        self.status.setText(f"État : {'connecté à ' + current if current else 'non connecté'}")

        nets = self.backend.scan_networks()
        self.list.clear()
        for net in nets:
            sig = f"{net.signal}%" if net.signal is not None else "?"
            sec = net.security or "?"
            self.list.addItem(f"{net.ssid}    | Signal: {sig} | Sécurité: {sec}")
        logging.info(f"UI: liste mise à jour ({len(nets)} réseaux)")

    def do_disconnect(self):
        logging.info("Action UI: déconnexion demandée")
        ok = self.backend.disconnect()
        if ok:
            logging.info("UI: déconnexion réussie")
            QMessageBox.information(self, "Wi‑Fi", "Déconnexion effectuée.")
        else:
            logging.warning("UI: déconnexion échouée")
            QMessageBox.warning(self, "Wi‑Fi", "Échec de la déconnexion.")
        self.refresh()

    def do_connect_manual(self):
        ssid = self.ssid_input.text().strip()
        password = self.pass_input.text().strip() or None
        logging.info(f"Action UI: connexion manuelle à '{ssid}' (pwd={'oui' if password else 'non'})")
        if not ssid:
            logging.warning("UI: connexion annulée — SSID vide")
            QMessageBox.information(self, "Wi‑Fi", "Renseigne le SSID.")
            return
        ok = self.backend.connect(ssid, password)
        if ok:
            logging.info(f"UI: connexion réussie à {ssid}")
            QMessageBox.information(self, "Wi‑Fi", f"Connecté à {ssid}.")
        else:
            logging.error(f"UI: échec de connexion à {ssid}")
            QMessageBox.warning(self, "Wi‑Fi", f"Échec de connexion à {ssid}.")
        self.refresh()

    def do_connect_selected(self):
        item = self.list.currentItem()
        logging.info("Action UI: connexion depuis la liste")
        if not item:
            logging.warning("UI: aucun réseau sélectionné")
            QMessageBox.information(self, "Wi‑Fi", "Sélectionne un réseau dans la liste.")
            return
        text = item.text()
        ssid = text.split("|")[0].strip()
        pwd, ok = QInputDialog.getText(self, "Mot de passe", f"Mot de passe pour {ssid} (laisser vide si ouvert):")
        if not ok:
            logging.info("UI: saisie mot de passe annulée")
            return
        password = pwd.strip() or None
        ok2 = self.backend.connect(ssid, password)
        if ok2:
            logging.info(f"UI: connexion réussie à {ssid}")
            QMessageBox.information(self, "Wi‑Fi", f"Connecté à {ssid}.")
        else:
            logging.error(f"UI: échec de connexion à {ssid}")
            QMessageBox.warning(self, "Wi‑Fi", f"Échec de connexion à {ssid}.")
        self.refresh()

# --------------------------------- MAIN ---------------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(APP_STYLE)
    w = WifiApp()
    w.show()
    ret = app.exec_()
    logging.info(f"=== Fermeture de l'application (code {ret}) ===")
    sys.exit(ret)
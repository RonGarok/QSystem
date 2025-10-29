# apps/Weather.py
import sys
import os
import requests
from contextlib import suppress
from PyQt5.QtWidgets import (
    QApplication, QWidget, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QFrame, QHBoxLayout
)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont

# Remplace la valeur par ta clé si besoin
API_KEY = "c903658554525a8658baaabafd38d990"

# Styles Mendel
PANEL_STYLE = "QFrame { background-color: #2f2f2f; border-radius: 12px; }"
INPUT_STYLE = """
QLineEdit {
    background-color: #3a3a3a;
    color: #ffffff;
    border: 1px solid #444444;
    padding: 8px;
    border-radius: 6px;
}
QLineEdit::placeholder { color: rgba(255,255,255,0.65); }
"""
BUTTON_STYLE = """
QPushButton {
    background-color: #505050;
    color: #ffffff;
    border: 1px solid #616161;
    padding: 8px 12px;
    border-radius: 6px;
}
QPushButton:hover { background-color: #5c5c5c; }
QPushButton:pressed { background-color: #474747; }
"""
LABEL_STYLE = "color: white; font-size: 14px;"

class WeatherApp(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Mendel Météo")
        # taille compacte (s'intègre aux apps)
        self.setFixedSize(420, 260)
        self.setStyleSheet("background-color: black;")

        # Petit logo M orange (taille réduite) — initial placement, sera repositionné dans resizeEvent
        self.logo = QLabel("M", self)
        self.logo_font_size = 36
        self.logo.setFont(QFont("Arial", self.logo_font_size, QFont.Bold))
        self.logo.setStyleSheet("color: orange;")
        self.logo.setAttribute(Qt.WA_TransparentForMouseEvents)
        self.logo.adjustSize()

        # Panneau central (sera centré dans resizeEvent)
        self.panel = QFrame(self)
        self.panel.setStyleSheet(PANEL_STYLE)
        self.panel_fixed_w = 320
        self.panel_fixed_h = 200
        self.panel.setFixedSize(self.panel_fixed_w, self.panel_fixed_h)

        # Layout interne
        v = QVBoxLayout(self.panel)
        v.setAlignment(Qt.AlignTop | Qt.AlignHCenter)
        v.setSpacing(10)

        # Input + bouton sur une ligne
        h = QHBoxLayout()
        h.setSpacing(8)

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("Entrez une ville")
        self.city_input.setFixedWidth(180)
        self.city_input.setStyleSheet(INPUT_STYLE)
        h.addWidget(self.city_input)

        self.refresh_btn = QPushButton("Actualiser")
        self.refresh_btn.setStyleSheet(BUTTON_STYLE)
        self.refresh_btn.clicked.connect(self.get_weather)
        h.addWidget(self.refresh_btn)

        v.addLayout(h)

        # Résultat
        self.result_label = QLabel("Aucune donnée")
        self.result_label.setStyleSheet(LABEL_STYLE)
        self.result_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        self.result_label.setWordWrap(True)
        v.addWidget(self.result_label)

        # Boutons utilitaires (ex : local sample)
        bottom_h = QHBoxLayout()
        bottom_h.setAlignment(Qt.AlignRight)
        self.clear_btn = QPushButton("Effacer")
        self.clear_btn.setStyleSheet(BUTTON_STYLE)
        self.clear_btn.clicked.connect(self.clear)
        bottom_h.addWidget(self.clear_btn)
        v.addLayout(bottom_h)

        # raccourci Enter pour récupérer la météo
        self.city_input.returnPressed.connect(self.get_weather)

        # focus input
        QTimer.singleShot(50, lambda: self.city_input.setFocus())

        # position initiale
        self._position_elements()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._position_elements()

    def _position_elements(self):
        # centrer le panneau
        w = self.width()
        h = self.height()
        px = (w - self.panel_fixed_w) // 2
        py = (h - self.panel_fixed_h) // 2
        self.panel.move(px, py)

        # placer le petit M en bas à droite, avec un léger padding
        padding = 8
        # ajuster la taille du M si la fenêtre change (garder petit)
        font_size = max(24, min(48, self.logo_font_size))
        self.logo.setFont(QFont("Arial", font_size, QFont.Bold))
        self.logo.adjustSize()
        lx = w - self.logo.width() - padding
        ly = h - self.logo.height() - padding
        self.logo.move(lx, ly)
        self.logo.raise_()

    def clear(self):
        self.city_input.clear()
        self.result_label.setText("Aucune donnée")

    def get_weather(self):
        city = self.city_input.text().strip()
        if not city:
            self.result_label.setText("⚠️ Entrez une ville valide")
            return

        self.result_label.setText("⏳ Recherche…")
        QTimer.singleShot(10, lambda: self._fetch_weather(city))

    def _fetch_weather(self, city):
        url = f"http://api.openweathermap.org/data/2.5/weather"
        params = {"q": city, "appid": API_KEY, "units": "metric", "lang": "fr"}

        try:
            r = requests.get(url, params=params, timeout=6)
            data = r.json()
        except Exception as e:
            self.result_label.setText(f"❌ Erreur réseau : {e}")
            return

        if not isinstance(data, dict):
            self.result_label.setText("❌ Réponse inattendue du serveur")
            return

        code = data.get("cod")
        # OpenWeather renvoie cod as str or int
        if str(code) != "200":
            message = data.get("message", "")
            self.result_label.setText(f"❌ Ville introuvable : {city}\n{message}")
            return

        try:
            temp = data["main"]["temp"]
            feels = data["main"].get("feels_like")
            desc = data["weather"][0]["description"].capitalize()
            humidity = data["main"]["humidity"]
            wind = data.get("wind", {}).get("speed")
            # formatage propre
            lines = [
                f"📍 {city}",
                f"🌡️ Température : {temp} °C" + (f" (ressenti {feels} °C)" if feels is not None else ""),
                f"🌤️ Météo : {desc}",
                f"💧 Humidité : {humidity}%",
            ]
            if wind is not None:
                lines.append(f"💨 Vent : {wind} m/s")
            self.result_label.setText("\n".join(lines))
        except Exception as e:
            self.result_label.setText(f"❌ Erreur traitement données : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    w = WeatherApp()
    w.show()
    sys.exit(app.exec_())

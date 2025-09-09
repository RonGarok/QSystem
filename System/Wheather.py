from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QLabel, QLineEdit, QPushButton,
    QVBoxLayout, QWidget
)
from PyQt5.QtCore import Qt
import requests
import sys

# 🔐 Ton token OpenWeather ici
API_KEY = "c903658554525a8658baaabafd38d990"

class WeatherApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Météo - QSystem")
        self.setGeometry(300, 200, 400, 300)

        self.city_input = QLineEdit()
        self.city_input.setPlaceholderText("🌍 Entrez une ville")
        self.city_input.setStyleSheet("font-size: 14px; padding: 5px;")

        self.result_label = QLabel("🌦️ Aucune donnée")
        self.result_label.setAlignment(Qt.AlignCenter)
        self.result_label.setStyleSheet("font-size: 16px;")

        self.refresh_btn = QPushButton("🔄 Actualiser")
        self.refresh_btn.clicked.connect(self.get_weather)

        layout = QVBoxLayout()
        layout.addWidget(self.city_input)
        layout.addWidget(self.refresh_btn)
        layout.addWidget(self.result_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def get_weather(self):
        city = self.city_input.text().strip()
        if not city:
            self.result_label.setText("⚠️ Entrez une ville valide")
            return

        url = f"http://api.openweathermap.org/data/2.5/weather?q={city}&appid={API_KEY}&units=metric&lang=fr"
        try:
            r = requests.get(url)
            data = r.json()
            if data.get("cod") != 200:
                self.result_label.setText(f"❌ Ville introuvable : {city}")
                return

            temp = data["main"]["temp"]
            desc = data["weather"][0]["description"]
            humidity = data["main"]["humidity"]
            self.result_label.setText(
                f"📍 {city}\n🌡️ Température : {temp}°C\n🌥️ Météo : {desc}\n💧 Humidité : {humidity}%"
            )
        except Exception as e:
            self.result_label.setText(f"❌ Erreur : {e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = WeatherApp()
    window.show()
    sys.exit(app.exec_())

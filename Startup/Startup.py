import time
import os
import subprocess
import sys
from art import tprint

def afficher_ascii():
    os.system("cls" if os.name == "nt" else "clear")
    tprint("QSYSTEM")
    print("\nChargement du système...\n")

def barre_de_chargement(duree=25, pas=10):
    total_steps = 100 // pas
    interval = duree / total_steps

    print("[", end="", flush=True)
    for i in range(total_steps):
        time.sleep(interval)
        print("#", end="", flush=True)
    print("] 100%")

def lancer_system_relay():
    chemin = os.path.join(os.path.dirname(__file__), "SystemRelay.py")
    subprocess.Popen(["python", chemin])
    sys.exit()

if __name__ == "__main__":
    afficher_ascii()
    barre_de_chargement()
    lancer_system_relay()
import os
import subprocess
import sys
from art import tprint

def afficher_ascii():
    os.system("cls" if os.name == "nt" else "clear")
    tprint("SYSTEM START")
    print("\n🚀 Initialisation finale du système...\n")

def lancer_system32():
    dossier_mere = os.path.dirname(os.path.dirname(__file__))  # remonte d'un niveau
    chemin_system32 = os.path.join(dossier_mere, "System", "System32.py")
    subprocess.Popen(["python", chemin_system32])
    sys.exit()

if __name__ == "__main__":
    afficher_ascii()
    lancer_system32()
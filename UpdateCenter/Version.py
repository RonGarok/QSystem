import os
import requests
import shutil
import sys

# 📁 Base directory of UpdateCenter
BASE_DIR = os.path.dirname(__file__)

# URLs
RAW_BASE_URL = "https://raw.githubusercontent.com/RonGarok/QSystem/main/"
GITHUB_TREE_API = "https://api.github.com/repos/RonGarok/QSystem/git/trees/main?recursive=1"
VERSION_CHECK_FILE = "VersionCheck.txt"
VERSION_FILE       = "Version.txt"

def lire_version(chemin):
    """Lit la version dans Version.txt donné."""
    if not os.path.exists(chemin):
        return None
    with open(chemin, "r", encoding="utf-8") as f:
        for line in f:
            if line.startswith("Version="):
                return line.split("=", 1)[1].strip()
    return None

def ecrire_version(chemin, version):
    """Écrit la nouvelle version dans Version.txt."""
    with open(chemin, "w", encoding="utf-8") as f:
        f.write(f"Version={version}\n")

def telecharger_fichier(path):
    url = RAW_BASE_URL + path
    # ✅ Corriger ici pour viser le dossier racine
    racine = os.path.dirname(BASE_DIR)
    local_path = os.path.join(racine, path.replace("/", os.sep))
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    resp = requests.get(url, stream=True)
    resp.raise_for_status()
    with open(local_path, "wb") as f:
        for chunk in resp.iter_content(4096):
            f.write(chunk)
    print(f"✅ Téléchargé : {path}")

def recuperer_liste_distante():
    """Récupère l'arborescence GitHub via API, retourne la liste des blobs pertinents."""
    resp = requests.get(GITHUB_TREE_API)
    resp.raise_for_status()
    tree = resp.json().get("tree", [])
    paths = []
    for item in tree:
        if item.get("type") != "blob":
            continue
        path = item.get("path", "")
        # Ignorer VersionCheck.txt
        if path == VERSION_CHECK_FILE:
            continue
        # Conserver les .py racine et tous les fichiers dans Startup, System, DEP, UpdateCenter
        if path.endswith(".py") and "/" not in path:
            paths.append(path)
        elif any(path.startswith(d + "/") for d in ("Startup", "System", "DEP", "UpdateCenter")):
            paths.append(path)
    return paths

def cleanup_local(paths_distants):
    """Supprime les fichiers locaux absents de la liste distante, pour chaque dossier ciblé."""
    for dossier in ("Startup", "System", "DEP", "UpdateCenter"):
        dossier_local = os.path.join(BASE_DIR, dossier)
        if not os.path.isdir(dossier_local):
            continue
        for root, _, files in os.walk(dossier_local):
            for name in files:
                full = os.path.join(root, name)
                rel  = os.path.relpath(full, BASE_DIR).replace(os.sep, "/")
                if rel not in paths_distants:
                    os.remove(full)
                    print(f"🗑️ Supprimé local : {rel}")

def main():
    try:
        print("🔍 Lecture de la version locale…")
        version_local = lire_version(os.path.join(BASE_DIR, VERSION_FILE))
        if not version_local:
            print("⚠️ Version locale introuvable.")
            return

        print(f"📄 Version locale : {version_local}")
        print("🌐 Téléchargement de la version distante…")
        # Récupérer VersionCheck.txt
        telecharger_fichier(VERSION_CHECK_FILE)
        version_dist = lire_version(os.path.join(BASE_DIR, VERSION_CHECK_FILE))
        if not version_dist:
            print("⚠️ Version distante introuvable.")
            return

        print(f"📄 Version distante : {version_dist}")
        # Comparer
        def to_tuple(v): return tuple(map(int, v.split(".")))
        if to_tuple(version_dist) <= to_tuple(version_local):
            print("\n✅ Aucune mise à jour disponible.")
            # Cleanup temporaire
            os.remove(os.path.join(BASE_DIR, VERSION_CHECK_FILE))
            return

        # Mise à jour disponible
        print("\n🚨 Mise à jour disponible !")
        print("Merci de ne pas éteindre QSystem ou fermer UpdateCenter.\n")

        # Récupérer liste distante
        print("🔗 Récupération de l’arborescence distante…")
        paths = recuperer_liste_distante()

        # Synchronisation
        print("\n📥 Téléchargement et mise à jour des fichiers…")
        for p in paths:
            telecharger_fichier(p)

        # Suppression des fichiers supprimés dans le repo
        print("\n🧹 Nettoyage des fichiers obsolètes…")
        cleanup_local(paths)

        # Mettre à jour la version locale
        ecrire_version(os.path.join(BASE_DIR, VERSION_FILE), version_dist)

        # Supprimer VersionCheck.txt
        os.remove(os.path.join(BASE_DIR, VERSION_CHECK_FILE))

        print("\n✅ Mise à jour effectuée avec succès !")
        print("Veuillez redémarrer QSystem pour appliquer les modifications.")

    except Exception as e:
        print(f"\n❌ Erreur lors de la mise à jour : {e}")

if __name__ == "__main__":
    main()

import keyboard

# Liste complète des touches à débloquer
touches = [
    'alt', 'ctrl', 'win', 'esc', 'tab', 'f4',
    'left alt', 'right alt', 'left ctrl', 'right ctrl',
    'left windows', 'right windows'
]

for t in touches:
    try:
        keyboard.unblock_key(t)
        print(f"✅ Touche débloquée : {t}")
    except Exception as e:
        print(f"❌ Erreur pour {t} : {e}")

print("\n✅ Toutes les touches ont été débloquées.")
input("Appuie sur Entrée pour fermer...")

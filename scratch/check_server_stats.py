import requests
try:
    # On essaye de récupérer le nombre de matchs via la page d'accueil (ou l'API)
    # L'API n'a pas de /count public mais on peut parser la page d'accueil ou demander au health
    # On va juste tester un upload d'un fichier existant pour voir si ça répond
    response = requests.get("https://notre-club-rl.fr/", timeout=5)
    if response.status_code == 200:
        print(f"Connexion au serveur : OK")
        # On pourrait extraire le texte "449 MATCHS ENREGISTRÉS"
        import re
        matches = re.findall(r'(\d+)\s+MATCHS ENREGISTRÉS', response.text)
        if matches:
            print(f"Matchs sur le serveur : {matches[0]}")
        else:
            print("Impossible de trouver le compteur sur la page d'accueil.")
    else:
        print(f"Erreur serveur : {response.status_code}")
except Exception as e:
    print(f"Erreur de connexion : {e}")

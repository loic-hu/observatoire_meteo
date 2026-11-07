"""Script d'alimentation : crée la base, ajoute des villes et leur météo actuelle.

Lancer :  python main.py
"""
# Session = la "conversation" avec la base (add, commit, select...).
from sqlmodel import Session

# engine : la connexion à SQLite. init_db : crée les tables si elles manquent.
# Importer ce module exécute database.py (création du dossier db/ et de l'engine).
from app.database import engine, init_db

# Modèle de VALIDATION d'une ville (virgule, plages de lat/long, nom nettoyé).
from app.ville import VilleCreate

# La logique métier : chercher/créer une ville, importer un relevé,
# et l'erreur personnalisée levée quand l'API météo pose problème.
from app.services import MeteoApiError, creer_ville, importer_releve, trouver_ville


# Villes de départ : (nom, latitude, longitude).
VILLES = [
    ("Saint-Quentin", 49.85, 3.29),
    ("Paris", 48.85, 2.35),
    ("Lyon", 45.76, 4.84),
]


def main() -> None:
    """Pour chaque ville : la créer si besoin, puis enregistrer son relevé actuel."""
    init_db() # 1. Tables créées si absentes, sans toucher aux existantes.
    with Session(engine) as session: # 2. Une session pour tout le script, fermée automatiquement.
        for nom, lat, lon in VILLES: # 3. Pour chaque ville de la liste :
            # Cherche la ville en base. Si elle n'existe pas (None), la valide avec VilleCreate puis l'insère.
            ville = trouver_ville(session, nom) or creer_ville(session, VilleCreate(nom=nom, latitude=lat, longitude=lon)
            )
            # Appelle Open-Meteo, valide la réponse, insère le relevé
            # (ou renvoie celui déjà présent pour ce créneau horaire).
            try:
                releve = importer_releve(session, ville)
                print(f"{ville.nom} : {releve.temperature} °C, {releve.vitesse_vent} km/h ({releve.date_heure})")
            # API indisponible : on signale et on passe à la ville suivante.
            except MeteoApiError as e:
                print(f"{ville.nom} : échec ({e})")


# Lance main() seulement si on exécute ce fichier directement, pas si un autre fichier l'importe.
# Bloc ignoré si un import main est réalisé
if __name__ == "__main__":
    main()

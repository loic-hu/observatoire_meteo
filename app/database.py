"""Connexion à la base SQLite et initialisation des tables.

Ce module crée l'objet 'engine' (la connexion à la base) utilisé par tout
le reste du projet, et fournit deux fonctions : 'init_db' et 'get_session'.
"""
import os
from pathlib import Path

from sqlalchemy import event
from sqlmodel import Session, SQLModel, create_engine

# __file__ = ce fichier ; .parent = app/ ; .parent.parent = racine du projet.
# Le chemin de la base ne dépend donc plus du dossier depuis lequel tu lances Python
ROOT = Path(__file__).resolve().parent.parent

# Variable d'environnement METEO_DB si elle existe, sinon db/meteo.db à la racine.
DB_PATH = Path(os.getenv("METEO_DB", ROOT / "db" / "meteo.db"))

# Crée le dossier db/ s'il manque (SQLite crée le fichier, jamais le dossier).
DB_PATH.parent.mkdir(parents=True, exist_ok=True)

# Aucun fichier n'est créé tant qu'on ne se connecte pas.
engine = create_engine(f"sqlite:///{DB_PATH}")

@event.listens_for(engine, "connect")
def _activer_cles_etrangeres(dbapi_conn, _record):
    """Active les clés étrangères à chaque nouvelle connexion.

    SQLite les ignore par défaut : sans cette commande, on pourrait insérer
    un relevé qui référence une ville inexistante.
    Le '_' devant '_record' indique un paramètre imposé mais non utilisé.
    """    
    cur = dbapi_conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    cur.close()


def init_db() -> None:
    """Crée les tables manquantes (CREATE TABLE IF NOT EXISTS).

    Sans effet sur les tables qui existent déjà : les données sont conservées.
    Attention : une table existante n'est jamais modifiée. Si on change un modèle,
    il faut supprimer db/meteo.db.
    """
    # Importer 'models' enregistre les classes Villes et Releves dans SQLModel.
    # Sans cet import, create_all ne verrait aucune table à créer.
    from app import models  # noqa: F401
    SQLModel.metadata.create_all(engine)


def get_session():
    """Fournit une session à une route FastAPI (via 'Depends').

    Le 'yield' prête la session à la route, puis le 'with' la ferme
    automatiquement à la fin de la requête, même en cas d'erreur.
    """
    with Session(engine) as session:
        yield session

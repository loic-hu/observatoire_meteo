"""Logique métier : gérer les villes et importer les relevés.

Ces fonctions sont utilisées à la fois par le script 'main.py' et par l'API
('api.py') : la logique est écrite une seule fois.
"""
from sqlmodel import Session, select, or_

# MeteoApiError est réexportée ici pour que main.py et api.py l'importent depuis un seul endroit (services).
from app.client import MeteoApiError, fetch_meteo
from app.models import Releves, Villes
from app.ville import VilleCreate, normaliser_nom

def trouver_ville(session: Session, nom: str) -> Villes | None:
    """Cherche une ville par son nom (SELECT ... WHERE nom = ? LIMIT 1).

    Le nom est normalisé comme à l'insertion : "paris" retrouve "Paris".

    Returns:
        L'objet 'Villes', ou 'None' si elle n'existe pas.
    """
    return session.exec(select(Villes).where(Villes.nom == normaliser_nom(nom))).first()

def trouver_doublon(session: Session, ville: VilleCreate) -> Villes | None:
    """Cherche des coodronnées déjà enregistrée."""
    return session.exec(
        select(Villes).where(
            or_(Villes.nom == ville.nom,
               (Villes.latitude == ville.latitude) & (Villes.longitude == ville.longitude),
            )
        )
    ).first()

# Permet de créer une ville
def creer_ville(session: Session, ville: VilleCreate) -> Villes:
    """Insère une ville déjà validée et renvoie la ligne créée (avec son 'id')."""
    # On valide d'abord (VilleCreate), puis on convertit vers la classe de table.
    obj = Villes.model_validate(ville)
    session.add(obj)
    session.commit()
    session.refresh(obj)
    return obj

# Permet de supprimer une ville
def supprimer_ville(session: Session, ville: Villes) -> None:
    """Supprime une ville ET tous ses relevés.

    Les relevés doivent partir en premier : ils référencent la ville par une clé étrangère,
    la base refuserait de supprimer la ville sinon.
    """
    for releve in session.exec(select(Releves).where(Releves.ville_id == ville.id)).all():
        session.delete(releve)
    session.delete(ville)
    session.commit()

#Permet d'importer les relevès d'une ville
def importer_releve(session: Session, ville: Villes) -> Releves:
    """Récupère la météo actuelle d'une ville et l'enregistre en base.

    Étapes : appel de l'API, validation Pydantic, vérification de doublon, insertion.

    Raises:
        MeteoApiError: si l'API externe échoue (l'appelant décide quoi faire).

    Returns:
        Le relevé créé, ou celui déjà en base pour ce créneau horaire.
    """
    # 1. Appel API + validation de la réponse.
    meteo = fetch_meteo(ville.latitude, ville.longitude)

    # 2. Existe-t-il déjà un relevé pour cette ville et cet horodatage ?
    existant = session.exec(
        select(Releves).where(
            Releves.ville_id == ville.id, Releves.date_heure == meteo.current.time
        )
    ).first()
    if existant:
        return existant

    # 3. Sinon, on crée la ligne (noms de l'API -> noms de nos colonnes).
    releve = Releves(
        ville_id=ville.id,
        temperature=meteo.current.temperature_2m,
        vitesse_vent=meteo.current.wind_speed_10m,
        date_heure=meteo.current.time,
    )
    session.add(releve)
    session.commit()
    session.refresh(releve)
    return releve

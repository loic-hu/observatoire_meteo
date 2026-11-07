"""Schémas Pydantic / SQLModel du projet (aucune table ici, voir models.py).

Ce fichier regroupe trois familles de classes :
  1. les données qui ENTRENT dans l'API (VilleCreate) : validées et nettoyées ;
  2. la forme de la réponse d'Open-Meteo (WeatherResponseModel) : vérifiée avant usage ;
  3. les données que NOTRE API renvoie (VilleRead, ReleveRead).

Aucune de ces classes n'a 'table=True' : leurs validators s'exécutent donc bien
à la création d'un objet (ce n'est pas le cas des modèles de tables).
"""
import datetime as dt
import re   # Pour les expressions régulières
import unicodedata  # Sert à unifier les accents

import pydantic as pyd
from sqlmodel import Field, SQLModel

# Fonction à part pour que la validation
def normaliser_nom(nom: str) -> str:
    """Écrit un nom de ville toujours de la même façon.

    Exemple : "  saint-quentin " devient "Saint-Quentin".
    Utilisée à l'insertion ET à la recherche, pour que "paris" retrouve "Paris".
    """
    # NFC recompose les accents en un seul caractère (un "é" = 1 caractère, pas 2),
    # et l'apostrophe typographique ’ devient l'apostrophe simple '.
    nom = unicodedata.normalize("NFC", nom).replace("’", "'")
    # strip() retire les espaces aux deux bouts ; title() met une majuscule à chaque mot.
    return nom.strip().title()

# ---------- Validation des données en entrée ---------- #
class VilleCreate(SQLModel):
    """Corps JSON attendu pour créer une ville, avec toutes ses validations."""
    nom: str            = Field(description="Nom de la ville")
    latitude: float     = Field(description="Latitude (-90 à 90)")
    longitude: float    = Field(description="Longitude (-180 à 180)")

    @pyd.field_validator("nom")
    @classmethod
    def verifier_nom(cls, att: str) -> str:
        att = normaliser_nom(att)
        if not 2 <= len(att) <= 100:
            raise ValueError("Nom : 2 à 100 caractères")
        if not re.fullmatch(r"[A-Za-zÀ-ÖØ-öø-ÿŒœ.' -]+", att):
            raise ValueError("Caractères non autorisés")
        return att

    @pyd.field_validator("latitude", "longitude", mode="before")
    @classmethod
    def convertir_(cls, att) -> float:
        """Convertit en nombre avant la validation de type ("48,85" -> 48.85).

        mode="before" : ce validator s'exécute AVANT la conversion automatique
        de Pydantic. Le résultat est arrondi à 2 décimales (environ 1 km).
        """
        return round(float(str(att).replace(",", ".")),2)

    @pyd.field_validator("latitude")
    @classmethod
    def verifier_latitude(cls, att: float) -> float:
        """Refuse une latitude hors de l'intervalle [-90, 90]."""
        if not -90 <= att <= 90:
            raise ValueError("Latitude hors limites")
        return att

    @pyd.field_validator("longitude")
    @classmethod
    def verifier_longitude(cls, att: float) -> float:
        """Refuse une longitude hors de l'intervalle [-180, 180]."""
        if not -180 <= att <= 180:
            raise ValueError("Longitude hors limites")
        return att


# ---------- Forme de ce que retourne Open-Meteo ---------- #
class CurrentWeather(pyd.BaseModel):
    """Bloc 'current' de la réponse d'Open-Meteo : les mesures du moment."""

    time: dt.datetime       # "2026-11-03T07:30" est converti en datetime
    interval: int           # durée entre deux mesures, en secondes
    temperature_2m: float   # température à 2 m du sol, en °C
    wind_speed_10m: float   # vitesse du vent à 10 m, en km/h

    @pyd.field_validator("time")
    @classmethod
    def heure_utc(cls, att: dt.datetime) -> dt.datetime:
        """Déclare l'heure en UTC si l'API n'a pas donné de fuseau (GMT par défaut)."""
        return att if att.tzinfo else att.replace(tzinfo=dt.timezone.utc)


# modèle imbriqué : reflète le dict dans le dict du JSON
class WeatherResponseModel(pyd.BaseModel):
    """Réponse complète d'Open-Meteo (seules les clés utiles sont déclarées).

    Modèle imbriqué : il reflète le JSON (un dict dans un dict). Les clés non
    déclarées (elevation, current_units...) sont simplement ignorées.
    """
    latitude: float
    longitude: float
    current: CurrentWeather


# ---------- Formats de ce que NOTRE API renvoie ---------- #
class VilleRead(SQLModel):
    """Format d'une ville dans les réponses de l'API (décrit aussi Swagger)."""
    id: int
    nom: str
    latitude: float
    longitude: float
    
class ReleveRead(SQLModel):
    """Format d'un relevé météo dans les réponses de l'API."""
    id: int
    ville_id: int
    temperature: float
    vitesse_vent: float
    date_heure: dt.datetime

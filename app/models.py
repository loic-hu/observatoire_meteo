"""Tables de la base de données (SQLModel).

Ces classes décrivent UNIQUEMENT le stockage. 
La validation des données est faite ailleurs (ville.py et meteo.py),
car un modèle avec 'table=True' ne valide pas les valeurs à la création d'un objet.
"""
import datetime as dt

from sqlalchemy import UniqueConstraint
from sqlmodel import Field, SQLModel


class Villes(SQLModel, table=True):
    """Table 'villes' : une ligne par ville suivie."""

    # 'None' à la création : c'est la base qui attribue l'identifiant (autoincrément).
    id: int | None   = Field(default=None, primary_key=True)
    # unique=True : deux villes ne peuvent pas porter le même nom.
    # index=True : accélère les recherches par nom.
    nom: str            = Field(unique=True, index=True, description="Nom de la ville")
    latitude: float     = Field(description="Latitude")
    longitude: float    = Field(description="Longitude")


class Releves(SQLModel, table=True):
    """Table 'releves' : une ligne par mesure météo d'une ville (1 ville -> N relevés)."""

    # Contrainte sur le COUPLE de colonnes : une ville peut avoir plusieurs relevés,
    # mais jamais deux pour le même horodatage.
    __table_args__ = (UniqueConstraint("ville_id", "date_heure"),)

    id: int | None          = Field(default=None, primary_key=True)
    # Clé étrangère : la valeur doit exister dans villes.id ("table.colonne").
    ville_id: int           = Field(foreign_key="villes.id", index=True)
    temperature: float      = Field(description="Température en °C")
    vitesse_vent: float     = Field(description="Vitesse du vent en km/h")
    date_heure: dt.datetime = Field(description="Horodatage du relevé")

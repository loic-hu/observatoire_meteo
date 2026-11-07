"""Client de l'API externe Open-Meteo : requête HTTP et validation de la réponse."""
import requests
from pydantic import ValidationError

from app.ville import WeatherResponseModel

# Constantes : valeurs fixes du module.
URL = "https://api.open-meteo.com/v1/forecast"
CURRENT = "temperature_2m,wind_speed_10m"      # variables météo demandées

# Exception personnalisée : le reste du code attrape UNE seule erreur métier,
# sans connaître les détails de requests ou de Pydantic.
class MeteoApiError(Exception):
    """API externe injoignable, en erreur, ou réponse inattendue.

    Une exception personnalisée permet au reste du code d'attraper UNE seule
    erreur métier, sans connaître les détails de 'requests' ou de Pydantic.
    """

def fetch_meteo(latitude: float, longitude: float) -> WeatherResponseModel:
    """Interroge Open-Meteo pour une position et renvoie la réponse validée.

    Args:
        latitude: latitude du point (degrés).
        longitude: longitude du point (degrés).

    Returns:
        La réponse d'Open-Meteo, vérifiée par 'WeatherResponseModel'.

    Raises:
        MeteoApiError: si l'API est injoignable, répond en erreur (4xx/5xx),
        ou renvoie des données qui n'ont pas la forme attendue.
    """
    params = {"latitude": latitude, "longitude": longitude, "current": CURRENT}
    try:
        # timeout : sans lui, la requête pourrait attendre indéfiniment.
        response = requests.get(URL, params=params, timeout=10)
        # Transforme une réponse 4xx/5xx en exception (ex. le 503 du Jour 1).
        response.raise_for_status()
        # JSON -> dict -> objet validé : les types sont vérifiés AVANT toute utilisation.
        return WeatherResponseModel.model_validate(response.json())
    except requests.RequestException as e:
        # RequestException est la classe parente de HTTPError, Timeout, ConnectionError...
        raise MeteoApiError(f"Open-Meteo indisponible : {e}") from e
    except (ValidationError, ValueError) as e:
        # La réponse est arrivée, mais n'a pas la forme attendue (ou n'est pas du JSON).
        raise MeteoApiError(f"Réponse Open-Meteo inattendue : {e}") from e

"""API FastAPI de l'Observatoire Météo.

Lancer :  uvicorn app.api:app --reload
Puis ouvrir http://127.0.0.1:8000/docs (documentation Swagger interactive).

Codes de statut HTTP utilisés (2xx = succès, 4xx = erreur du client, 5xx = erreur du serveur) :
    200 OK                    lecture réussie                    GET /villes, GET /meteo/{ville}
    201 Created               ressource créée                    POST /villes, POST .../actualiser
    204 No Content            succès, rien à renvoyer            DELETE /villes/{ville}
    404 Not Found             ressource inconnue                 ville inconnue
    409 Conflict              conflit avec l'état de la base     ville déjà enregistrée
    422 Unprocessable Entity  corps invalide                     produit par FastAPI (validators)
    502 Bad Gateway           le service en amont a échoué       Open-Meteo en échec
"""
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, status
from sqlmodel import Session, select

from app import services
from app.database import get_session, init_db
from app.models import Releves, Villes
from app.ville import VilleCreate, ReleveRead, VilleRead


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Code exécuté au démarrage (avant le 'yield') et à l'arrêt (après) du serveur."""
    init_db()   # tables créées si absentes, une seule fois au démarrage
    yield       # le serveur tourne pendant ce yield

# L'objet central. 'title' apparaît en haut de Swagger.
# uvicorn app.api:app = "dans le module app/api.py, prends l'objet nommé app".
app = FastAPI(title="Observatoire Météo", lifespan=lifespan)

def _ville_ou_404(session: Session, nom: str) -> Villes:
    """Renvoie la ville demandée, ou interrompt la route avec une erreur 404.

    Le '_' initial signale une fonction interne à ce fichier. HTTPException
    arrête la route : FastAPI fabrique lui-même la réponse d'erreur.
    """
    ville = services.trouver_ville(session, nom)
    if ville is None:
        raise HTTPException(status_code=404, detail="Ville inconnue")
    return ville

# "@app.get(...)" : quand un GET arrive sur /villes, FastAPI appelle cette fonction.
# Depends(get_session) : FastAPI crée la session, la passe, puis la ferme.
# response_model : la réponse est filtrée et validée par VilleRead (et décrite dans Swagger).
@app.get("/villes", response_model=list[VilleRead])
def lister_villes(session: Session = Depends(get_session)):
    """Liste toutes les villes enregistrées."""
    return session.exec(select(Villes)).all()

# 'ville: VilleCreate' : un paramètre typé par un modèle Pydantic est lu comme le CORPS JSON de la requête.
# FastAPI le valide AVANT d'appeler la fonction : si une# règle échoue (latitude à 120...),
# il répond 422 sans que cette fonction s'exécute.
@app.post("/villes", response_model=VilleRead, status_code=201)
def ajouter_ville(ville: VilleCreate, session: Session = Depends(get_session)):
    """Ajoute une ville. Erreurs : 409 si elle existe déjà, 422 si les données sont invalides."""
    existante = services.trouver_doublon(session, ville)
    if existante:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Conflit avec la ville déjà enregistrée : {existante.nom}",
    )
    return services.creer_ville(session, ville)

# {ville} dans le chemin devient le paramètre 'ville' de la fonction.
# Un 204 (No Content) n'a pas de corps de réponse : on ne met donc AUCUN response_model.
@app.delete("/villes/{ville}", status_code=201) # Code 204 ne foncitonne pas, problème de lib ou d'installation meme avec la maj
def supprimer_ville(ville: str, session: Session = Depends(get_session)):
    """Supprime une ville et ses relevés. Erreur : 404 si la ville est inconnue."""
    v = _ville_ou_404(session, ville)
    services.supprimer_ville(session, v)

@app.get("/meteo/{ville}", response_model=list[ReleveRead])
def releves_ville(ville: str, session: Session = Depends(get_session)):
    """Liste les relevés d'une ville, du plus ancien au plus récent.

    404 si la ville est inconnue ; 200 avec une liste vide si elle n'a pas encore de relevé.
    """
    v = _ville_ou_404(session, ville)
    return session.exec(
        select(Releves).where(Releves.ville_id == v.id).order_by(Releves.date_heure)
    ).all()

# POST (et non GET) car cette route ÉCRIT en base : elle déclenche une action.
@app.post("/meteo/{ville}/actualiser", response_model=ReleveRead, status_code=201)
def actualiser(ville: str, session: Session = Depends(get_session)):
    """Récupère la météo actuelle d'une ville via Open-Meteo et l'enregistre.

    Erreurs : 404 si la ville est inconnue, 502 si Open-Meteo est en échec.
    """
    v = _ville_ou_404(session, ville)
    try:
        return services.importer_releve(session, v)
    # 502 Bad Gateway : notre serveur fonctionne, mais le service en amont a échoué.
    except services.MeteoApiError as e:
        raise HTTPException(status_code=502, detail=str(e))

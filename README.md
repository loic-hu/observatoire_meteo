# Observatoire Météo

Application Python qui récupère la météo actuelle de plusieurs villes via l'API
**Open-Meteo**, valide les données avec **Pydantic**, les stocke dans **SQLite**
(via **SQLModel**) et les expose avec sa propre API **FastAPI**, documentée
automatiquement par **Swagger**.

## Ce que fait le projet

- Appelle Open-Meteo (requête HTTP avec délai maximal et gestion d'erreurs).
- Vérifie la réponse avec Pydantic avant de s'en servir.
- Enregistre villes et relevés dans une base SQLite, sans doublon.
- Expose une API pour gérer les villes et consulter ou déclencher les relevés.
- Documente et permet de tester l'API depuis le navigateur (`/docs`).

## Structure du projet

```
observatoire/
├── main.py              # script d'alimentation (python main.py)
├── requirements.txt     # dépendances
├── README.md
├── db/                  # contient meteo.db, créé automatiquement
└── app/
    ├── __init__.py      # marque le dossier comme package Python
    ├── database.py      # connexion SQLite, création des tables, sessions
    ├── models.py        # tables : Villes, Releves
    ├── ville.py         # schémas : validation des entrées, réponse d'Open-Meteo, sorties de l'API
    ├── client.py        # appel à Open-Meteo (requests + validation)
    ├── services.py      # logique métier : créer, chercher, supprimer, importer
    └── api.py           # routes FastAPI
```

| Fichier | Rôle en une phrase |
|---|---|
| `models.py` | décrit **comment on stocke** les données (tables) |
| `ville.py` | décrit **ce qu'on accepte et ce qu'on renvoie** (validation, formats) |
| `client.py` | va **chercher** la météo chez Open-Meteo |
| `services.py` | **orchestre** : cherche, crée, supprime, importe |
| `api.py` / `main.py` | **points d'entrée** : l'API web et le script |

## Parcours d'une donnée

```
Open-Meteo  ->  client.py  ->  services.py  ->  models.py (SQLite)  ->  api.py  ->  JSON
 (API externe)   requête +      vérifie le        stockage             route +     réponse
                 validation     doublon, insère                        format
```

## Installation

Prérequis : Python 3.14 ou plus récent.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows : .venv\Scripts\activate
pip install -r requirements.txt
```

## Utilisation

**1. Alimenter la base** (crée `db/meteo.db`, ajoute 3 villes et leur météo actuelle) :

```bash
python main.py
```

**2. Lancer l'API** (depuis la racine du projet) :

```bash
uvicorn app.api:app --reload
```

Puis ouvrir <http://127.0.0.1:8000/docs> : chaque route peut être testée avec **Try it out**, puis **Execute**.

> La base est créée une seule fois : relancer le script ou le serveur conserve les données existantes.

## Routes de l'API

| Méthode | Route | Rôle | Codes de réponse |
|---|---|---|---|
| GET | `/villes` | liste les villes | 200 |
| POST | `/villes` | ajoute une ville | 201, 409 (doublon), 422 (données invalides) |
| DELETE | `/villes/{ville}` | supprime une ville et ses relevés | 204, 404 |
| GET | `/meteo/{ville}` | liste les relevés d'une ville | 200, 404 |
| POST | `/meteo/{ville}/actualiser` | importe le relevé actuel depuis Open-Meteo | 201, 404, 502 |

Exemple de corps pour `POST /villes` :

```json
{"nom": "Lille", "latitude": "50,63", "longitude": 3.06}
```

## Codes de statut HTTP

- **2xx** : succès (200 OK, 201 Created, 204 No Content)
- **4xx** : erreur du client (404 ressource inconnue, 409 conflit, 422 corps invalide)
- **5xx** : erreur du serveur (502 : Open-Meteo a échoué, notre API fonctionne)

## Modèle de données

```
villes                         releves
------                         -------
id (clé primaire)  <---------  ville_id (clé étrangère -> villes.id)
nom (unique)                   id (clé primaire)
latitude                       temperature (°C)
longitude                      vitesse_vent (km/h)
                               date_heure (UTC)
                               unique (ville_id, date_heure)
```

Une ville a plusieurs relevés. Deux relevés de la même ville ne peuvent pas avoir le même horodatage.

## Règles de validation (ville)

- Nom : nettoyé (espaces retirés, majuscules), de 2 à 100 caractères, lettres, accents, point, apostrophe, tiret et espace uniquement.
- Latitude entre -90 et 90, longitude entre -180 et 180 ; la virgule décimale est acceptée (`"48,85"`) et les valeurs sont arrondies à 2 décimales.
- Une ville déjà enregistrée est refusée (409), la recherche ignore la casse (`paris` retrouve `Paris`).

## Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `503` ou `502` à l'import | Open-Meteo temporairement indisponible | réessayer plus tard |
| `ModuleNotFoundError: app...` | commande lancée hors de la racine du projet | se placer à la racine, environnement `.venv` activé |
| `no such table` / colonne absente | la base date d'une ancienne version du modèle | supprimer `db/meteo.db` et relancer |
| `404` sur `/` | aucune route n'est définie sur `/` | ouvrir `/docs` |
| 500 après un `DELETE` | `response_model` ou annotation de retour déclaré sur une route 204 | retirer le `response_model` |

## Pistes d'amélioration

- Migrations de schéma avec Alembic (aujourd'hui, un modèle modifié impose de recréer la base).
- Mise à jour périodique automatique des relevés.
- Tests automatisés (pytest avec `TestClient` de FastAPI).
- Historique et statistiques par ville (moyenne, minimum, maximum).

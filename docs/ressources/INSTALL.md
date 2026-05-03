
## Geocaptcha

**installation avec les jeux de données test:**

INITIAL_DATA=true docker compose -f compose-local.yaml up -d

**attendre que tout soit opérationnel :**

docker compose -f compose-local.yaml ps

**arrêter le portail démo car il utilise l'un des ports de service superset :**

docker compose -f compose-local.yaml stop demo

**suivre l'activité de l'API :**

docker compose -f compose-local.yaml logs api -f


# superset & Shillelagh & geocaptcha adapter

git clone superset

**paramétrage demandé par Shillelagh :**

cd ~/sources/superset/docker/pythonpath_dev/

superset_config.py
```
...

PREVENT_UNSAFE_DB_CONNECTIONS = False
```

git clone https://ledav-perso@github.com/ledav-perso/geocaptcha-shillelagh.git

cd ~/sources/superset

docker compose up --build

docker compose exec -it superset bash

docker compose logs superset

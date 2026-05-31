# RETEX driver Shillelagh avec le connecteur Generic JSON API

configuration (nécessaire ?) pour autoriser les extensions qui ont besoin d'accéder au système de fichier et à la base de données de configuration
./docker/pythonpath_dev/superset_config.py
```python
...

# évite de bloquer le driver SHillelagh pour les connecteurs qui ont besoin d'accéder au système de fichier
# nécessaire sauf si :
# on place shillelagh+safe:// dans l'URI de connexion
# le connecteur déclare qu'il est safe dans la déclaration de la classe :
#    # adapter doesn’t read or write from the filesystem we can mark it as safe.
#    safe = True
PREVENT_UNSAFE_DB_CONNECTIONS = False

...
```

et ajout package geocaptcha-shillelagh


après lancement de l'instance superset, ajouter une base de données (Settings -> Database connections)

choisir database Shillelagh

paramètres standards :

![paramètres standards](./ressources/parametres-standards.png)

paramètres avancés :

![paramètres avancés](./ressources/parametres-avances.png)

placer dans Engine parameters :

```json
{
  "connect_args":
  {
    "adapters":["geocaptcha"],
    "adapter_kwargs":
    {
      "geocaptcha":
      {
        "app_id":"admin",
        "api_key":"****************************",
        "cache_password": "**************************"
      }
    }
  }
}
```

paramètre        | valeur par défaut                      | description
-----            | -----                                  | ----------
base_url         | https://geocaptcha.ign.fr/api/v1/admin | Endpoint API Geocaptcha
app_id           | NA                                     | compte admin
api_key          | NA                                     | mdp admin
log_level        | ERROR                                  | log level du composant
page_size        | 1000                                   | nombre de documents extraits par page
limit_size       | 100000                                 | nb maximum de documents téléchargés
cache_expiration | 14400                                  | durée du cache en secondes
cache_server     | locahost                               | hostname du serveur Valkey / Redis
cache_port       | 6379                                   | port du serveur Valkey / Redis
cache_db         | 1                                      | numéro de la base de données
cache_username   | geocaptcha                             | Valkey username
cache_password   | geocaptcha                             | Valkey password

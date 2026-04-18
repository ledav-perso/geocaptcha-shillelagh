# geocaptcha-shillelagh

## Contexte 

besoin d'un rapport d'exploitation pour le service Geocaptcha, utilisation de la solution [Apache Superset](https://superset.apache.org/)

tests du connecteur genericjsonapi du driver [Shillelagh](https://github.com/betodealmeida/shillelagh)) pour connecter l'API admin Geocaptcha

RETEX : [test connecteur generic JSON API](./docs/RETEX_genericjsonapi.md)

Besoin de développer un connecteur dédié pour profiter des fonctionalitées suivantes :
- pagination
- formatage des champs (en particulier les horodatages)
- gestion des nested objects (en particulier le champ captcha de l'objet session)
- création de champs calculés (résultats de jointures entre sessions et captchas puis entre sessions et cusers)


## Objectif

fournir un connecteur dédié à l'API Geocaptcha pour Apache superset (https://superset.apache.org/) basé sur l'utilisation du driver Shillelagh (https://github.com/betodealmeida/shillelagh)

Construire un rapport d'exploitation sous forme d'un tableau de bord Apache superset


## API admin Geocaptcha

[Spécifications de l'API admin Geocaptcha](https://github.com/IGNF/GeoCaptchaAPI/blob/main/src/spec/geocaptcha-openapi.yaml)


| Resource  | Description                                    |
|-----------|------------------------------------------------|
| `session` | sessions de captchas tentées  |
| `cuser`   | applications clientes enregistrées          |
| `kingpin` | captchas préenregistrés |

This package provides two Shillelagh adapters — one per resource — so you can query
them with standard SQL:

```sql
-- Success rate per challenge
SELECT challenge_name,
       COUNT(*)                                           AS total,
       SUM(CASE WHEN success THEN 1 ELSE 0 END)          AS successes,
       AVG(duration)                                      AS avg_duration_s
FROM   "https://geocaptcha.example.com/api/v1/admin/session"
GROUP  BY challenge_name;

-- List all API users
SELECT app_id, email, role
FROM   "https://geocaptcha.example.com/api/v1/admin/cuser";
```


## Installation

```bash
pip install geocaptcha-shillelagh
```

### Requirements

- Python ≥ 3.9
- `shillelagh >= 1.4`
- `python-dateutil >= 2.8`
- `requests-cache >= 1.0`


## Usage

### Python DB-API

```python
from shillelagh.backends.apsw.db import connect

conn = connect(
    ":memory:",
    adapter_kwargs={
        "geocaptchasessionadapter": {
            "api_key": "YOUR_API_KEY",
            "app_id":  "YOUR_APP_ID",
        },
        "geocaptchacuseradapter": {
            "api_key": "YOUR_API_KEY",
            "app_id":  "YOUR_APP_ID",
        },
    },
)

cursor = conn.cursor()
cursor.execute(
    'SELECT * FROM "https://geocaptcha.example.com/api/v1/admin/session"'
)
for row in cursor:
    print(row)
```

### SQLAlchemy

```python
from sqlalchemy import create_engine, text

engine = create_engine(
    "shillelagh://",
    connect_args={
        "adapter_kwargs": {
            "geocaptchasessionadapter": {
                "api_key": "YOUR_API_KEY",
                "app_id":  "YOUR_APP_ID",
            },
        }
    },
)

with engine.connect() as con:
    result = con.execute(
        text('SELECT * FROM "https://geocaptcha.example.com/api/v1/admin/session"')
    )
    for row in result:
        print(row)
```

### Apache Superset

1. Add a new database connection in Superset with the SQLAlchemy URI:
   ```
   shillelagh://
   ```
2. Under **Advanced → Other → Engine Parameters**, add:
   ```json
   {
     "connect_args": {
       "adapter_kwargs": {
         "geocaptchasessionadapter": {
           "api_key": "YOUR_API_KEY",
           "app_id":  "YOUR_APP_ID"
         },
         "geocaptchacuseradapter": {
           "api_key": "YOUR_API_KEY",
           "app_id":  "YOUR_APP_ID"
         }
       }
     }
   }
   ```
3. Use the full API URL as the table name in SQL Lab:
   ```sql
   SELECT *
   FROM "https://geocaptcha.example.com/api/v1/admin/session"
   LIMIT 100;
   ```


## Virtual table columns

### `session` table

| Column           | Type     | Description                                          |
|------------------|----------|------------------------------------------------------|
| `session_id`     | String   | Unique session identifier                            |
| `success`        | Boolean  | `true` if the user solved the captcha                |
| `begin`          | DateTime | Session start time                                   |
| `end`            | DateTime | Session end time                                     |
| `duration`       | Float    | Duration in seconds (`NULL` if timestamps missing)   |
| `challenge_name` | String   | Name of the geographic challenge presented           |

### `cuser` table

| Column    | Type   | Description                              |
|-----------|--------|------------------------------------------|
| `app_id`  | String | Unique application identifier / key name |
| `email`   | String | Contact e-mail address                   |
| `referer` | String | Allowed HTTP `Referer` domain            |
| `role`    | String | Role (`user`, `admin`, …)                |


## Authentication

Credentials are **never** embedded in the URI.  Pass them as adapter connection
arguments (`api_key` and `app_id`) as shown in the examples above.


## Project structure

```
.
├── src/
│   └── geocaptcha_shillelagh/
│       ├── __init__.py
│       └── adapter.py      # GeoCaptchaSessionAdapter & GeoCaptchaCUserAdapter
├── tests/
│   └── test_adapter.py
├── pyproject.toml
└── README.md
```


## Development

```bash
# Clone & install in editable mode with dev extras
git clone https://github.com/ledav-perso/geocaptcha-shillelagh.git
cd geocaptcha-shillelagh
pip install -e ".[dev]"

# Run tests
pytest
```

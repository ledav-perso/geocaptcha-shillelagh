# FAQ

## Lister les plugins disponibles dans shillelagh

référence :
- https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/

```python
from importlib_metadata import entry_points
discovered_plugins = entry_points(group='shillelagh.adapter')
print(discovered_plugins)
```

```bash
docker compose exec -it superset bash

root@1bd14783353a:/app# python
Python 3.11.14 (main, Feb 24 2026, 19:44:43) [GCC 14.2.0] on linux
Type "help", "copyright", "credits" or "license" for more information.
>>> from importlib_metadata import entry_points
>>> discovered_plugins = entry_points(group='shillelagh.adapter')
>>> print(discovered_plugins)
EntryPoints((EntryPoint(name='superset', value='superset.extensions.metadb:SupersetShillelaghAdapter', group='shillelagh.adapter'), EntryPoint(na
me='csvfile', value='shillelagh.adapters.file.csvfile:CSVFile', group='shillelagh.adapter'), EntryPoint(name='datasetteapi', value='shillelagh.ad
apters.api.datasette:DatasetteAPI', group='shillelagh.adapter'), EntryPoint(name='dbtmetricflowapi', value='shillelagh.adapters.api.dbt_metricflo
w:DbtMetricFlowAPI', group='shillelagh.adapter'), EntryPoint(name='genericjsonapi', value='shillelagh.adapters.api.generic_json:GenericJSONAPI',
group='shillelagh.adapter'), EntryPoint(name='genericxmlapi', value='shillelagh.adapters.api.generic_xml:GenericXMLAPI', group='shillelagh.adapte
r'), EntryPoint(name='githubapi', value='shillelagh.adapters.api.github:GitHubAPI', group='shillelagh.adapter'), EntryPoint(name='gsheetsapi', va
lue='shillelagh.adapters.api.gsheets.adapter:GSheetsAPI', group='shillelagh.adapter'), EntryPoint(name='holidaysmemory', value='shillelagh.adapte
rs.memory.holidays:HolidaysMemory', group='shillelagh.adapter'), EntryPoint(name='htmltableapi', value='shillelagh.adapters.api.html_table:HTMLTa
bleAPI', group='shillelagh.adapter'), EntryPoint(name='pandasmemory', value='shillelagh.adapters.memory.pandas:PandasMemory', group='shillelagh.a
dapter'), EntryPoint(name='presetapi', value='shillelagh.adapters.api.preset:PresetAPI', group='shillelagh.adapter'), EntryPoint(name='presetwork
spaceapi', value='shillelagh.adapters.api.preset:PresetWorkspaceAPI', group='shillelagh.adapter'), EntryPoint(name='s3selectapi', value='shillela
gh.adapters.api.s3select:S3SelectAPI', group='shillelagh.adapter'), EntryPoint(name='socrataapi', value='shillelagh.adapters.api.socrata:SocrataA
PI', group='shillelagh.adapter'), EntryPoint(name='systemapi', value='shillelagh.adapters.api.system:SystemAPI', group='shillelagh.adapter'), Ent
ryPoint(name='virtualmemory', value='shillelagh.adapters.memory.virtual:VirtualMemory', group='shillelagh.adapter'), EntryPoint(name='weatherapi'
, value='shillelagh.adapters.api.weatherapi:WeatherAPI', group='shillelagh.adapter')))
>>> exit()
```

ou

```python
from importlib.metadata import entry_points
eps = entry_points(group='shillelagh.adapter')
for entry in eps:
    print(f"Nom: {entry.name}, Valeur: {entry.value}")
```

## Injecter collection récupérée dans l'env. de développement

**optionnel : supprimer la collection sessions de la base Mongo :**

```bash
docker run -it --rm --net developpement_geocaptcha-dev alpine/mongosh mongosh mongodb://geocaptcha:[redacted]@172.19.0.3:27017/geocaptcha

Current Mongosh Log ID: 6a04cde05a5c2540aba637b1
Connecting to:          mongodb://<credentials>@172.19.0.3:27017/geocaptcha?directConnection=true&appName=mongosh+2.0.2
Using MongoDB:          7.0.28
Using Mongosh:          2.0.2

For mongosh info see: https://docs.mongodb.com/mongodb-shell/


To help improve our products, anonymous usage data is collected and sent to MongoDB periodically (https://www.mongodb.com/legal/privacy-policy).
You can opt-out by running the disableTelemetry() command.


Deprecation warnings:
  - Using mongosh with Node.js versions lower than 20.0.0 is deprecated, and support may be removed in a future release.
See https://www.mongodb.com/docs/mongodb-shell/install/#supported-operating-systems for documentation on supported platforms.

geocaptcha> db.sessions.drop()
true
geocaptcha> exit()
```

**importer les sessions :**

```bash
docker run -it --rm --net developpement_geocaptcha-dev -v ./api:/jeu alpine/mongosh bash

b457617cd309:/# mongoimport -v --collection=sessions --db=geocaptcha --uri 'mongodb://geocaptcha:pAssw0rd@172.19.0.3:27017/' --file=jeu/sessions.json --jsonArray
2026-05-13T19:16:11.627+0000    using write concern: &{majority false 0}
2026-05-13T19:16:11.639+0000    filesize: 1108413 bytes
2026-05-13T19:16:11.639+0000    using fields:
2026-05-13T19:16:11.639+0000    connected to: mongodb://[**REDACTED**]@172.19.0.3:27017/
2026-05-13T19:16:11.639+0000    ns: geocaptcha.sessions
2026-05-13T19:16:11.639+0000    connected to node type: standalone
2026-05-13T19:16:11.737+0000    1000 document(s) imported successfully. 0 document(s) failed to import.
```

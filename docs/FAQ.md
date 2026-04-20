Lister les plugins disponibles dans shillelagh

référence : 
- https://packaging.python.org/en/latest/guides/creating-and-discovering-plugins/

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
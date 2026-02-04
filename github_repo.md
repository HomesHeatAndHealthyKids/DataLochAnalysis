## Homes, Heat and Healthy Kids - DataLoch Git Repo

The DataLoch Git Repo is a code repository for sharing code between members of the team on DataLoch. It should also be used for version control. The code is based around a shared DuckDB database that can be accessed by all members of the team from a shared folder.

The code consists of the following:
* create_db.py - python code to import all data in to a centralised DuckDB databases. The data import routine uses the file "config.ini" to determine which files should be imported
* hhhk_data_transform/ folder - dbt project to transform data in imported DuckDB. This cleans the data - deduping, validation and error removal
* notebooks/ folder - jupyter notebooks for descriptive analysis and code management
* examples/ folder - canonical examples showing how to query a DuckDB database in Python and R
* query_runner.py - python app to allow users to run ad-hoc SQL queries against the DuckDB database features autocomplete and lexical parsing
* data_viz.py - short python routine to quickly/automatically create data visualisations of the raw input tables

Project members should not usually need to create the database or run the transform process. Most of their work should be focused on the final database and using that for reporting.

## Getting Started

To get started:

* Clone the report to your local user area
```
cd Documents
git config --global --add safe.directory ~/Desktop/lot-23-023/hhk_repo
git clone ~/Desktop/lot-23-023/hhk_repo
cd hhk_repo
ls
```

This should result in a set of python files and folders being created in the directory hhk_repo. hhk_repo is under git management and you can see the status of any of your files by typing "git status"

* install the requirements from PyPI if you are using Python
```
pip install -r requirements.txt
```

* run query_runner as a test
```
python query_runner.py
```
This code allows you to use autocomplete to put together SQL queries easily and save the results in a CSV file. The resultant CSV file can be analysed easily in OpenOffice.

## R Users
* please install the following package to use DuckDB
```
# WARNING: this takes over an hour to
# compile first time so please run it in the background

install.packages("duckdb")
```
* example code to access the DuckDB database is available in the examples folder in a Quarto Markdown file
* data can be easily exported from the DuckDB database to a CSV file if you wish to go that route

## Questions
* Please direct questions to Tim Wilding
* If you require new extracts of data or further cleaning of data, please contact Tim and he will try to provide a cleaned view
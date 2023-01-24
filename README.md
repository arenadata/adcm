[![Total alerts](https://img.shields.io/lgtm/alerts/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/alerts/)
[![Language grade: JavaScript](https://img.shields.io/lgtm/grade/javascript/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/context:javascript)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/context:python)

# Arenadata Cluster Manager

That is Arenadata Cluster Manager Project (aka Chapelnik)

# Documentation

[ArenaData ADCM Documentation](http://docs.arenadata.io/adcm/)

# Develop

All standard Django commands are available.

Run dev server for the first time with these commands:
1. `manage.py migrate`
2. `init_db.py`
3. `manage.py upgraderole`
4. `manage.py runserver --insecure`

Re-run them when needed/applicable.

# Sources

## Dirs

* assemble - information about the way we build product
* python - core django modules and python functions
* docs 
* go - golang part of application. There is a status server here now.
* test 
* spec - specification in form of Sphinx RST 
* web - UI source

# Build logic

There is a Makefile in repo. It could be used for building application.

## Fast start with make

You have to have GNU Make on your host and Docker daemon accessible for a user. Also, you have to have access to ci.arenadata.io

```sh
# Clone repo
git clone https://github.com/arenadata/adcm

cd adcm

# Run build process
make build
```

That will be an image hub.adsw.io/adcm/adcm:<branch_name> as a result of the operation above.

## Makefile description

Makefile has self-documented help message. Just type.

```sh
$ make
buildbaseimage                 Build base image for ADCM's container. That is alpine with all packages.
build                          Build final docker image and all depended targets except baseimage.
buildjs                        Build client side js/html/css in directory wwwroot
buildss                        Build status server
clean                          Cleanup. Just a cleanup.
describe                       Create .version file with output of describe
help                           Shows that help
```

And check out the description for every operation available.

## Pre-commit hook

We are using black, pylint and pre-commit to care about code formatting and linting.

So you have to install pre-commit hook before you do something with code.

``` sh
pip install pre-commit # Or do it with your preffered way to install pip packages
pre-commit install
```

After this you will see invocation of black and pylint on every commit.

## Link ADWP_UI packages

If you need to debug packages from ADWP_UI, you should do next:

In ADWP_UI repository:
```sh
delete dist folder
yarn run watch:widgets
cd dist/widgets
yarn link
```

In ADCM repository:
```sh
cd web
sudo rm -rf ./node_modules OR rmdir -force ./node_modules(WIN)
yarn link "@adwp-ui/widgets"
yarn install
```

## Running ADCM using SQLite

1. Start container:

    ```shell
    docker run -d --restart=always -p 8000:8000 -v /opt/adcm:/adcm/data --name adcm hub.arenadata.io/adcm/adcm:latest
    ```

    Use `-v /opt/adcm:/adcm/data:Z` for SELinux

## Running ADCM using client PostgreSQL DB

1. Start container:
   ```shell
   docker run -d --restart=always -p 8000:8000 -v /opt/adcm:/adcm/data 
   -e DB_HOST="DATABASE_HOSTNAME_OR_IP_ADDRESS" -e DB_PORT="DATABASE_TCP_PORT" 
   -e DB_USER="DATABASE_USERNAME" -e DB_NAME="DATABASE_NAME" 
   -e POSTGRES_ADCM_PASS="DATABASE_USER_PASSWORD" --name adcm hub.arenadata.io/adcm/adcm:latest
   ```
   Use `-v /opt/adcm:/adcm/data:Z` for SELinux
   Target PostgreSQL DB must not have DB with name `DATABASE_NAME`

## Running ADCM using docker-compose PostgreSQL DB
1. Create env file `.env` containing:

   ```shell
   POSTGRES_ADCM_PASS="SOME_STRONG_SECRET_PASS"
   DATA_DIR="./data"
   DB_DIR="./db_dir"
   POSTGRES_PASSWORD="SOME_ANOTHER_STRONG_SECRET_PASS"
   ```
   where
   - `POSTGRES_ADCM_PASS` - password which will be used to create `adcm` PostgreSQL role
   - `DATA_DIR` - path to directory which will contain all ADCM data
   - `DB_DIR` - path to directory which will contain PostgreSQL DB data to keep it persistent 
   across containers restart, it must be empty beforehand
   - `POSTGRES_PASSWORD` - password for `postgres` PostgreSQL role

## Migrate SQLite -> docker-compose PostgreSQL

1. Create env file `.env` containing:

   ```shell
   POSTGRES_ADCM_PASS=""
   DATA_DIR="./data"
   DB_DIR="./db_dir"
   POSTGRES_PASSWORD="ANY_STRING"
   ```
   where
   - `POSTGRES_ADCM_PASS` - password which will be used to create `adcm` PostgreSQL role
   - `DATA_DIR` - path to directory which now contains all ADCM data, including SQLite DB file
   - `DB_DIR` - path to directory which will contain PostgreSQL DB data to keep it persistent
   across containers restart, it must be empty beforehand
   - `POSTGRES_PASSWORD` - password for `postgres` PostgreSQL role (it will be changed later)

2. `docker-compose up -d`
3. `docker exec adcm_adcm_1 /adcm/python/manage.py dumpdata -o /adcm/data/var/data.json`
4. `docker-compose down`
5. Edit `.env` file and fill `POSTGRES_ADCM_PASS="SOME_STRONG_SECRET_PASS"`
   `POSTGRES_PASSWORD="SOME_ANOTHER_STRONG_SECRET_PASS"`
6. `rm -rf db_dir`
7. `docker-compose up -d`
8. `docker exec adcm_adcm_1 /adcm/python/manage.py loaddata /adcm/data/var/data.json`

## Migrate SQLite -> client PostgreSQL
1. Dump SQLite DB to file:
   ```shell
   docker run -it --rm -p 8000:8000 -v /opt/adcm:/adcm/data --name adcm hub.arenadata.io/adcm/adcm:latest /adcm/python/manage.py dumpdata -o /adcm/data/var/data.json
   ```
2. Start container:
   ```shell
   docker run -d --restart=always -p 8000:8000 -v /opt/adcm:/adcm/data 
   -e DB_HOST="DATABASE_HOSTNAME_OR_IP_ADDRESS" -e DB_PORT="DATABASE_TCP_PORT" 
   -e DB_USER="DATABASE_USERNAME" -e DB_NAME="DATABASE_NAME" 
   -e POSTGRES_ADCM_PASS="DATABASE_USER_PASSWORD" --name adcm hub.arenadata.io/adcm/adcm:latest
   ```
   Use `-v /opt/adcm:/adcm/data:Z` for SELinux
   Target PostgreSQL DB must not have DB with name `DATABASE_NAME`
3. Load dumped SQLite DB data to PostgreSQL
   ```shell
   docker exec -it adcm /adcm/python/manage.py loaddata /adcm/data/var/data.json
   ```

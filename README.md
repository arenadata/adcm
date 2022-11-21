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

## Migrate SQLite -> PostgreSQL, PostgreSQL -> Custom PostgreSQL

1. PostgreSQL DB must be empty during first start
2. `export POSTGRES_ADCM_PASS=`
3. `docker-compose up -d`
4. `docker exec adcm_adcm_1 /adcm/python/manage.py dumpdata > /adcm/data/var/data.json`
5. `docker-compose down`
6. `export POSTGRES_ADCM_PASS="SOME_STRONG_SECRET_PASS"`
7. `docker-compose up -d`
8. `docker exec adcm_adcm_1 /adcm/python/manage.py loaddata /adcm/data/var/data.json`

## Using custom Postgres DB

1. Environment variables should be exported before `docker-compose up` after data dump:
   `POSTGRES_ADCM_PASS`, `DB_NAME`, `DB_USER`, `DB_HOST`, `DB_PORT`

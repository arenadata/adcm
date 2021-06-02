[![Total alerts](https://img.shields.io/lgtm/alerts/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/alerts/)
[![Language grade: JavaScript](https://img.shields.io/lgtm/grade/javascript/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/context:javascript)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/context:python)

# Arenadata Cluster Manager

That is Areandata Cluster Manager Project (aka Chapelnik)

# Documentation

[ArenaData ADCM Documentation](http://docs.arenadata.io/adcm/)


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

You have to have GNU Make on your host and Docker daemon accessable for a user. Besides you have to have access to ci.arenadata.io

```sh
# Clone repo
git clone https://github.com/arenadata/adcm

cd adcm

# Run build process
make build
```

That will be image ci.arenadata.io/adcm:<branch_name> as a result of the operation above.

## Makefile description

Makefile has selfdocumented help message. Just type.

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

We are using black, pylint and pre-commit to care about code formating and linting.

So you have to install pre-commit hook before you do something with code.

``` sh
pip install pre-commit # Or do it with your preffered way to install pip packages
pre-commit install
```

After this you will see invocation of black and pylint on every commit.

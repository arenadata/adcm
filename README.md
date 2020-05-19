[![Total alerts](https://img.shields.io/lgtm/alerts/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/alerts/)
[![Language grade: JavaScript](https://img.shields.io/lgtm/grade/javascript/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/context:javascript)
[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/arenadata/adcm.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/arenadata/adcm/context:python)

# Arenadata Cluster Manager

That is Areandata Cluster Manager Project (aka Chapelnik)

# Documentation

[ArenaData ADCM Documentation](http://docs.arenadata.io/adcm/)


# Sources

## Dirs

* adcm - django projects root dir
* api - python module with django REST
* cm - core django modules and python functions
* docs 
* go - golang part of application. There is a status server here now.
* test 
* web - UI source
* wwwroot - static root for frontend files

## Files

* inventory.py - dinamic inventory for ansible
* job_runner.py - run plabook script

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

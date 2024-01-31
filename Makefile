BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))
SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444
ADCM_VERSION = "2.0.0"

.PHONY: help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

buildss:
	@docker run -i --rm -v $(CURDIR)/go:/code -w /code golang sh -c "make"

buildjs:
	@docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/adcm-web/app:/code -e ADCM_VERSION=$(ADCM_VERSION) -w /code node:18.16-alpine ./build.sh

build_base:
	@docker build . -t $(APP_IMAGE):$(APP_TAG) --build-arg ADCM_VERSION=$(ADCM_VERSION)

# build ADCM_v2
build: buildss buildjs build_base

unittests_sqlite:
	poetry install --no-root --with unittests
	poetry run python/manage.py test python -v 2 --parallel

unittests_postgresql:
	docker run -d --rm -e POSTGRES_PASSWORD="postgres" --name postgres -p 5500:5432 postgres:14
	export DB_HOST="localhost" DB_PORT="5500" DB_NAME="postgres" DB_PASS="postgres" DB_USER="postgres"
	poetry install --no-root --with unittests
	poetry run python/manage.py test python -v 2 --parallel
	docker stop postgres

pretty:
	poetry install --no-root --with lint
	poetry run python license_checker.py --fix --folders python go
	poetry run ruff format license_checker.py python
	poetry run ruff check --fix license_checker.py python
	poetry run ruff format license_checker.py python

lint:
	poetry install --no-root --with lint
	poetry run python license_checker.py --folders python go
	poetry run ruff check license_checker.py python
	poetry run ruff format --check python

version:
	@echo $(ADCM_VERSION)

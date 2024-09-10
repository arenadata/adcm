BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))
SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444
ADCM_VERSION = "2.3.0-dev"
PY_FILES = python dev/linters conf/adcm/python_scripts

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
	poetry run ruff format $(PY_FILES)
	poetry run ruff check --fix $(PY_FILES)
	poetry run ruff format $(PY_FILES)
	poetry run python dev/linters/license_checker.py --fix --folders $(PY_FILES) go

lint:
	poetry install --no-root --with lint
	poetry run ruff check $(PY_FILES)
	poetry run ruff format --check $(PY_FILES)
	poetry run pyright --project pyproject.toml
	poetry run python dev/linters/license_checker.py --folders $(PY_FILES) go
	poetry run python dev/linters/migrations_checker.py python

version:
	@echo $(ADCM_VERSION)

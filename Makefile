BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))
SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444
ADCM_VERSION = "2.5.1"
PY_FILES = python dev/linters conf/adcm/python_scripts

.PHONY: build unittests_sqlite unittests_postgresql pretty lint version

build:
	@docker build . -t $(APP_IMAGE):$(APP_TAG) --build-arg ADCM_VERSION=$(ADCM_VERSION)

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

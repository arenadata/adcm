BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))
SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444

.PHONY: help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

describe:
	@echo '{"version": "$(shell date '+%Y.%m.%d.%H')","commit_id": "$(shell git log --pretty=format:'%h' -n 1)"}' > config.json
	cp config.json web/src/assets/config.json

buildss:
	@docker run -i --rm -v $(CURDIR)/go:/code -w /code golang sh -c "make"

buildjs:
	@docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:16-alpine ./build.sh

build_base:
	@docker build . -t $(APP_IMAGE):$(APP_TAG)

build: describe buildss buildjs build_base

unittests_sqlite: describe
	poetry install --no-root --with unittests
	poetry run python/manage.py test python -v 2 --parallel

unittests_postgresql: describe
	docker run -d --rm -e POSTGRES_PASSWORD="postgres" --name postgres -p 5500:5432 postgres:14
	export DB_HOST="localhost" DB_PORT="5500" DB_NAME="postgres" DB_PASS="postgres" DB_USER="postgres"
	poetry install --no-root --with unittests
	poetry run python/manage.py test python -v 2 --parallel
	docker stop postgres

ng_tests:
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster_node16-x64
	docker run -i --rm -v $(CURDIR)/:/adcm -w /adcm/web hub.adsw.io/library/functest:3.8.6.slim.buster_node16-x64 ./ng_test.sh

pretty:
	poetry install --no-root --with lint
	black license_checker.py python
	autoflake -r -i --remove-all-unused-imports --exclude apps.py,python/ansible/plugins,python/init_db.py,python/task_runner.py,python/backupdb.py,python/job_runner.py,python/drf_docs.py license_checker.py python
	isort license_checker.py python
	python license_checker.py --fix --folders python go

lint:
	poetry install --no-root --with lint
	poetry run black --check license_checker.py python
	poetry run autoflake --check --quiet -r --remove-all-unused-imports --exclude apps.py,python/ansible/plugins,python/init_db.py,python/task_runner.py,python/backupdb.py,python/job_runner.py,python/drf_docs.py license_checker.py python
	poetry run isort --check license_checker.py python
	python license_checker.py --folders python go
	poetry run pylint --rcfile pyproject.toml --recursive y python

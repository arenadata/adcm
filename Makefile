BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))
SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444
ADCM_VERSION = "3.1.0-dev"
PY_FILES = python dev/linters conf/adcm/python_scripts

.PHONY: build unittests test-integrations pretty lint version

define uv_sync
uv sync --inexact --group $(1)
endef

define pg_start
docker run -d --rm -e POSTGRES_PASSWORD="postgres" --name postgres -p 5500:5432 postgres:14
i=0; until docker exec postgres pg_isready -U postgres > /dev/null 2>&1; do \
	i=$$((i+1)); \
	if [ $$i -ge 30 ]; then \
		echo "Postgres did not become ready within 30s" >&2; \
		docker stop postgres; \
		exit 1; \
	fi; \
	sleep 1; \
done
endef

define pg_stop
docker stop postgres
endef

TEST_ENV = DJANGO_SETTINGS_MODULE=adcm.settings_setups.test \
	DB_HOST="localhost" DB_USER="postgres" DB_PORT="5500" DB_NAME="postgres" DB_PASS="postgres"

# $(1): arguments of `manage.py test` (labels and options)
define run_tests
$(call uv_sync,unittests)
$(pg_start)
$(TEST_ENV) uv run python/manage.py test -v 2 --keepdb $(1); \
TEST_EXIT=$$?; \
$(pg_stop); \
exit $$TEST_EXIT
endef

build:
	@docker build --platform=linux/amd64 . -t $(APP_IMAGE):$(APP_TAG) --build-arg ADCM_VERSION=$(ADCM_VERSION)

unittests:
	# celery_worker exclude is ignored, but it's a failsafe in case discovery is changed,
	# since these tests may flak/fail in parallel run
	$(call run_tests,python --parallel --exclude-tag celery_worker)

test-integrations:
	# `tests.integrations` has no `__init__.py`, so its test packages have to be pointed at directly
	$(call run_tests,tests.integrations.celery)

pretty:
	$(call uv_sync,lint)
	uv run ruff format $(PY_FILES)
	uv run ruff check --fix $(PY_FILES)
	uv run ruff format $(PY_FILES)
	uv run python dev/linters/license_checker.py --fix --folders $(PY_FILES) go

lint:
	$(call uv_sync,lint)
	uv run ruff check $(PY_FILES)
	uv run ruff format --check $(PY_FILES)
	uv run pyright --project pyproject.toml
	env PYTHONPATH=python uv run lint-imports --verbose
	uv run python dev/linters/license_checker.py --folders $(PY_FILES) go
	uv run python dev/linters/migrations_checker.py python

version:
	@echo $(ADCM_VERSION)

# Set number of threads
BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)

ADCMBASE_IMAGE ?= hub.arenadata.io/adcm/base
ADCMBASE_TAG ?= 20210927130343

APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))

SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444


# Default target
.PHONY: help

help: ## Shows that help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

clean: ## Cleanup. Just a cleanup.
	@docker run -i --rm  -v $(CURDIR):/code -w /code  busybox:latest /bin/sh -c "rm -rf /code/web/node_modules/ /code/web/package-lock.json /code/wwwroot /code/.version /code/go/bin /code/go/pkg /code/go/src/github.com"

##################################################
#                 B U I L D
##################################################

describe: ## Create .version file with output of describe
	./gues_version.sh

buildss: ## Build status server
	@docker run -i --rm -v $(CURDIR)/go:/code -w /code  golang:1.15-alpine3.13 sh -c "apk --update add make git && make && rm -f /code/adcm/go.sum"

buildjs: ## Build client side js/html/css in directory wwwroot
	@docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:12-alpine ./build.sh

buildbase: ## Build base image for ADCM's container. That is alpine with all packages.
	cd assemble/base && docker build --pull=true --no-cache=true \
	-t $(ADCMBASE_IMAGE):$$(date '+%Y%m%d%H%M%S') -t $(ADCMBASE_IMAGE):latest \
	.

build: describe buildss buildjs ## Build final docker image and all depended targets except baseimage.
	@docker build --no-cache=true \
	-f assemble/app/Dockerfile \
	-t $(APP_IMAGE):$(APP_TAG) \
	--build-arg  ADCMBASE_IMAGE=$(ADCMBASE_IMAGE) --build-arg  ADCMBASE_TAG=$(ADCMBASE_TAG) \
	.

##################################################
#                 T E S T S
##################################################

testpyreqs: ## Install test prereqs into user's pip target dir
	pip install --user -r requirements-test.txt

unittests: ## Run unittests
	docker pull $(ADCMBASE_IMAGE):$(ADCMBASE_TAG)
	docker run -i --rm -v $(CURDIR)/:/adcm -w /adcm/tests/base $(ADCMBASE_IMAGE):$(ADCMBASE_TAG) /bin/sh -e ./run_test.sh

pytest: ## Run functional tests
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster-x64
	docker run -i --rm --shm-size=4g -v /var/run/docker.sock:/var/run/docker.sock --network=host -v $(CURDIR)/:/adcm -w /adcm/ \
	-e BUILD_TAG=${BUILD_TAG} -e ADCMPATH=/adcm/ -e PYTHONPATH=${PYTHONPATH}:python/ \
	-e SELENOID_HOST="${SELENOID_HOST}" -e SELENOID_PORT="${SELENOID_PORT}" \
	hub.adsw.io/library/functest:3.8.6.slim.buster-x64 /bin/sh -e \
	./pytest.sh -m "not full" --adcm-image='hub.adsw.io/adcm/adcm:$(subst /,_,$(BRANCH_NAME))'


pytest_release: ## Run functional tests on release
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster.firefox-x64
	docker run -i --rm --shm-size=4g -v /var/run/docker.sock:/var/run/docker.sock --network=host -v $(CURDIR)/:/adcm -w /adcm/ \
	-e BUILD_TAG=${BUILD_TAG} -e ADCMPATH=/adcm/ -e PYTHONPATH=${PYTHONPATH}:python/ \
	-e SELENOID_HOST="${SELENOID_HOST}" -e SELENOID_PORT="${SELENOID_PORT}" \
	hub.adsw.io/library/functest:3.8.6.slim.buster.firefox-x64 /bin/sh -e \
	./pytest.sh --adcm-image='hub.adsw.io/adcm/adcm:$(subst /,_,$(BRANCH_NAME))'

ng_tests: ## Run Angular tests
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster-x64
	docker run -i --rm -v $(CURDIR)/:/adcm -w /adcm/web hub.adsw.io/library/functest:3.8.6.slim.buster-x64 ./ng_test.sh

linters : ## Run linters
	docker pull hub.adsw.io/library/pr-builder:3-x64
	docker run -i --rm -v $(CURDIR)/:/source -w /source hub.adsw.io/library/pr-builder:3-x64 \
        /bin/bash -xeo pipefail -c "/linters.sh shellcheck pylint pep8 && \
        /linters.sh -b ./tests -f ../tests pylint && \
        /linters.sh -f ./tests black && \
        /linters.sh -f ./tests/functional flake8_pytest_style && \
        /linters.sh -f ./tests/ui_tests flake8_pytest_style"

npm_check: ## Run npm-check
	docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:12-alpine ./npm_check.sh

django_tests : ## Run django tests.
	docker pull $(ADCMBASE_IMAGE):$(ADCMBASE_TAG)
	docker run -e DJANGO_SETTINGS_MODULE=adcm.test -i --rm -v $(CURDIR)/:/adcm -w /adcm/ $(ADCMBASE_IMAGE):$(ADCMBASE_TAG) python python/manage.py test cm

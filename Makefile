# Set number of threads
# EPIC ADCM-1524
BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)

ADCMBASE_IMAGE ?= hub.arenadata.io/adcm/base
ADCMTEST_IMAGE ?= hub.arenadata.io/adcm/test
ADCMBASE_TAG ?= 20220630133845
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
	@docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:16-alpine ./build.sh

build: describe buildss buildjs ## Build final docker image and all depended targets except baseimage.
	@docker pull $(ADCMBASE_IMAGE):$(ADCMBASE_TAG)
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

test_image:
	docker pull $(ADCMBASE_IMAGE):$(ADCMBASE_TAG)

unittests: test_image ## Run unittests
		docker run -e DJANGO_SETTINGS_MODULE=adcm.settings -i --rm -v $(CURDIR)/python:/adcm/python -v $(CURDIR)/data:/adcm/data -v $(CURDIR)/requirements.txt:/adcm/requirements.txt -w /adcm/ $(ADCMBASE_IMAGE):$(ADCMBASE_TAG) /venv.sh reqs_and_run default /adcm/requirements.txt python python/manage.py test python -v 2


pytest: ## Run functional tests on release
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster.firefox-x64
	docker run -i --rm --shm-size=4g -v /var/run/docker.sock:/var/run/docker.sock --network=host \
	-v $(CURDIR)/:/adcm -v ${LDAP_CONF_FILE}:${LDAP_CONF_FILE} -w /adcm/ \
	-e BUILD_TAG=${BUILD_TAG} -e ADCMPATH=/adcm/ -e PYTHONPATH=${PYTHONPATH}:python/ \
	-e SELENOID_HOST="${SELENOID_HOST}" -e SELENOID_PORT="${SELENOID_PORT}" \
	hub.adsw.io/library/functest:3.8.6.slim.buster.firefox-x64 /bin/sh -e \
	./pytest.sh --adcm-image='hub.adsw.io/adcm/adcm:$(subst /,_,$(BRANCH_NAME))' \
	--ldap-conf ${LDAP_CONF_FILE}

ng_tests: ## Run Angular tests
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster_node16-x64
	docker run -i --rm -v $(CURDIR)/:/adcm -w /adcm/web hub.adsw.io/library/functest:3.8.6.slim.buster_node16-x64 ./ng_test.sh

linters: test_image ## Run linters
	docker run -i --rm -e PYTHONPATH="/source/tests" -v $(CURDIR)/:/source -w /source $(ADCMTEST_IMAGE):$(ADCMBASE_TAG) \
        /bin/sh -eol pipefail -c "/linters.sh shellcheck && \
			/venv.sh run default pip install -U -r requirements.txt -r requirements-test.txt && \
			/venv.sh run default pylint --rcfile pyproject.toml --recursive y python && \
			/linters.sh -b ./tests -f ../tests pylint && \
			/linters.sh -f ./tests black && \
			/linters.sh -f ./tests/functional flake8_pytest_style && \
			/linters.sh -f ./tests/ui_tests flake8_pytest_style"

npm_check: ## Run npm-check
	docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:16-alpine ./npm_check.sh

##################################################
#                 U T I L S
##################################################

base_shell: ## Just mount a dir to base image and run bash on it over docker run
	docker run -e DJANGO_SETTINGS_MODULE=adcm.settings -it --rm -v $(CURDIR)/python:/adcm/python -v $(CURDIR)/data:/adcm/data -w /adcm/ $(ADCMBASE_IMAGE):$(ADCMBASE_TAG) /bin/bash -l

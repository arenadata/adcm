BRANCH_NAME ?= $(shell git rev-parse --abbrev-ref HEAD)
ADCMBASE_IMAGE ?= hub.arenadata.io/adcm/base
ADCMTEST_IMAGE ?= hub.arenadata.io/adcm/test
ADCMBASE_TAG ?= 20220630133845
APP_IMAGE ?= hub.adsw.io/adcm/adcm
APP_TAG ?= $(subst /,_,$(BRANCH_NAME))

SELENOID_HOST ?= 10.92.2.65
SELENOID_PORT ?= 4444


.PHONY: help

help:
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

clean:
	@docker run -i --rm  -v $(CURDIR):/code -w /code  busybox:latest /bin/sh -c "rm -rf /code/web/node_modules/ /code/web/package-lock.json /code/wwwroot /code/.version /code/go/bin /code/go/pkg /code/go/src/github.com"

describe:
	./gues_version.sh

buildss:
	@docker run -i --rm -v $(CURDIR)/go:/code -w /code golang sh -c "make"

buildjs:
	@docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:16-alpine ./build.sh

build: describe buildss buildjs
	@docker build --no-cache=true -t $(APP_IMAGE):$(APP_TAG) .

testpyreqs:
	pip install --user -r requirements-test.txt

test_image:
	docker pull $(ADCMBASE_IMAGE):$(ADCMBASE_TAG)

unittests: test_image
		docker run -e DJANGO_SETTINGS_MODULE=adcm.settings -i --rm -v $(CURDIR)/python:/adcm/python -v $(CURDIR)/data:/adcm/data -v $(CURDIR)/requirements.txt:/adcm/requirements.txt -w /adcm/ $(ADCMBASE_IMAGE):$(ADCMBASE_TAG) /venv.sh reqs_and_run default /adcm/requirements.txt python python/manage.py test python -v 2

pytest:
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster-x64
	docker run -i --rm --shm-size=4g -v /var/run/docker.sock:/var/run/docker.sock --network=host \
	-v $(CURDIR)/:/adcm -w /adcm/ \
	-e BUILD_TAG=${BUILD_TAG} -e ADCMPATH=/adcm/ -e PYTHONPATH=${PYTHONPATH}:python/ \
	-e SELENOID_HOST="${SELENOID_HOST}" -e SELENOID_PORT="${SELENOID_PORT}" \
	hub.adsw.io/library/functest:3.8.6.slim.buster-x64 /bin/sh -e \
	./pytest.sh -m "not full and not extra_rbac and not ldap" \
	--adcm-image='hub.adsw.io/adcm/adcm:$(subst /,_,$(BRANCH_NAME))'

pytest_release:
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster.firefox-x64
	docker run -i --rm --shm-size=4g -v /var/run/docker.sock:/var/run/docker.sock --network=host \
	-v $(CURDIR)/:/adcm -v ${LDAP_CONF_FILE}:${LDAP_CONF_FILE} -w /adcm/ \
	-e BUILD_TAG=${BUILD_TAG} -e ADCMPATH=/adcm/ -e PYTHONPATH=${PYTHONPATH}:python/ \
	-e SELENOID_HOST="${SELENOID_HOST}" -e SELENOID_PORT="${SELENOID_PORT}" \
	hub.adsw.io/library/functest:3.8.6.slim.buster.firefox-x64 /bin/sh -e \
	./pytest.sh --adcm-image='hub.adsw.io/adcm/adcm:$(subst /,_,$(BRANCH_NAME))' \
	--ldap-conf ${LDAP_CONF_FILE}

ng_tests:
	docker pull hub.adsw.io/library/functest:3.8.6.slim.buster_node16-x64
	docker run -i --rm -v $(CURDIR)/:/adcm -w /adcm/web hub.adsw.io/library/functest:3.8.6.slim.buster_node16-x64 ./ng_test.sh

linters: test_image
	docker run -i --rm -e PYTHONPATH="/source/tests" -v $(CURDIR)/:/source -w /source $(ADCMTEST_IMAGE):$(ADCMBASE_TAG) \
        /bin/sh -eol pipefail -c "/linters.sh shellcheck && \
			/venv.sh run default pip install -U -r requirements.txt -r requirements-test.txt && \
			/venv.sh run default pylint --rcfile pyproject.toml --recursive y python && \
			/linters.sh -b ./tests -f ../tests pylint && \
			/linters.sh -f ./tests black && \
			/linters.sh -f ./tests/functional flake8_pytest_style && \
			/linters.sh -f ./tests/ui_tests flake8_pytest_style"

npm_check:
	docker run -i --rm -v $(CURDIR)/wwwroot:/wwwroot -v $(CURDIR)/web:/code -w /code  node:16-alpine ./npm_check.sh

base_shell:
	docker run -e DJANGO_SETTINGS_MODULE=adcm.settings -it --rm -v $(CURDIR)/python:/adcm/python -v $(CURDIR)/data:/adcm/data -w /adcm/ $(ADCMBASE_IMAGE):$(ADCMBASE_TAG) /bin/bash -l

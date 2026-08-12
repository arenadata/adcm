# Arenadata Cluster Manager

This repository holds `ADCM`'s source code and build tooling.

Installation and usage docs can be found in [documentation](https://docs.arenadata.io/adcm/).

## Quickstart

1. Clone the repository:
   ```shell
   git clone https://github.com/arenadata/adcm
   cd adcm
   ```
2. Build the image for your architecture:
   ```shell
   make build
   ```
   You'll get an image tagged `hub.adsw.io/adcm/adcm:<BRANCH_NAME>`.
3. Run ADCM as a docker container (you will need running `PostgreSQL` 14+ instance):
   ```shell
   docker run -d -p 8000:8000 -v /opt/adcm:/adcm/data --name adcm \
   -e DB_HOST="<DATABASE_HOSTNAME_OR_IP_ADDRESS>" \
   -e DB_USER="<DATABASE_USERNAME>" -e DB_NAME="<DATABASE_NAME>" \
   -e DB_PASS="<DATABASE_USER_PASSWORD>" \
   hub.arenadata.io/adcm/adcm:<TAG>
   ```

A few things to know before you run it:
* Replace `<TAG>` and the `<DATABASE_*>` placeholders with values matching your own setup.
* You can use the newly built image (from step 2) instead of `hub.arenadata.io/adcm/adcm:<TAG>`.
* Your `PostgreSQL` instance needs to be version 14 or newer — `ADCM` relies on the `JSONB` field type.
* `DB_NAME` should already exist, and the user you connect with needs permission to modify its structure.
* You can set `-e DB_PORT=...` to change `PostgreSQL` port to connect to — by default it's `5432`.
* You can configure log level by setting `-e LOG_LEVEL=...` to one of `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (defaults to `ERROR`).
* On `SELinux`, mount the volume with `-v /opt/adcm:/adcm/data:Z` instead.

## Structure

* Components
  * [`adcm-web`](adcm-web/app/README.md) - frontend
  * [`python`](python/README.md) - backend (API, Ansible plugins, container init and task runner components)
  * [`go`](go/README.md) - status/event server
* Container image
  * [`Dockerfile`](Dockerfile) - container image definition
  * `conf` - `ADCM` bundle
  * `os` - filesystem overlay baked into the container image
* Build & tooling
  * [`Makefile`](Makefile) - management commands, run `make help` for available targets
  * `dev` - developer tooling (linters, profiling configs)

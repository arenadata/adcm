# Backend

Django-based core of `ADCM`: API, Ansible plugins, container init and task runner components.

Other dev docs:
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) - how the project is structured and organized
- [`docs/CODESTYLE.md`](docs/CODESTYLE.md) - conventions to follow when writing code
- [`docs/NOTES.md`](docs/NOTES.md) - commentary on non-obvious feature implementations

## How to

`ADCM` is shipped as container and dev pipelines rely on `Makefile`.

So based on your task:
- prepare environment / your code for push - `make pretty` then `make lint`
- run tests - `make unittests`
- validate end-to-end behavior - build image & run container

Actions described above are up to date and reliable, but some tasks require more control.
General approach here is to do these steps (in order until problem is solved):
1. Read docs in this project (mostly answers generic questions, navigate to problem)
2. Read sources:
   - startup script for steps required for setup (`startup.sh` or see `Dockerfile` entrypoint)
   - `Makefile` to know how linters/tests are launched with what configuration and so on
   - `pyproject.toml` contains information about environment, optional dependency groups and linter settings
3. Read official user [documentation](https://docs.arenadata.io/adcm/)
4. Ask other developers for insight

### Development cycle

1. Create branch with task ID in name (like `ADCM-4952` or `bug/ADCM-3910`, etc.)
2. Prepare/sync environment 
   (easiest is to run `make pretty` to install all major dependencies; otherwise, you can run installation parts from this command)
3. Write code and tests following codestyle and architecture
4. Ensure `make pretty` and `make lint` pass
5. (optional) Run tests with `make unittests`
6. Push to remote branch

### Run code locally

In all cases you'll need running `PostgreSQL`: you can connect to existing local/remote instance or run one in container (e.g. how it's done in `make unittests`).

#### Pass code to existing image

Passing code to existing image allows you to skip rebuilding image, but will still require container restart OR restarting services inside container on code change.
In other ways it's the closest to what final result will look like.

#### Run `Django` server locally just to serve API

Running `Django` server will require some preparations.
Exact commands should be found in entrypoint (with adjustment of local launch and file structure),
but general steps are:
1. Prepare secrets file (`application/scripts/manage_secrets.py init`)
2. Apply database migrations (`manage.py migrate`)
3. Prepare various system records (`init_db.py`)
4. Upgrade roles (`manage.py upgraderole`)
5. Run server (`manage.py runserver`)

Don't forget to set up environment variables for DB connection.

Also you may need to specify settings module for `Django`.

Data directory management is also important since files from previous launches may conflict with the new ones (mostly bundles, maybe files in `run` subdir).

#### Run other entrypoints outside of container

Running other entrypoints (scheduler, celery worker, task runner, ansible plugins) is trickier, but generally will require same steps as for running API server
and some extra environment (like filled database, ansible execution environment, etc.).

Do that only if other approaches failed to meet your task.

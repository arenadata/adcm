# Notes

Commentary on non-obvious feature implementations: the kind of context that's useful while working with a feature,
but doesn't fit into [`ARCHITECTURE.md`](ARCHITECTURE.md) or [`CODESTYLE.md`](CODESTYLE.md) and isn't reliably found
if left only as comments scattered across the code.

To add a note, add a new section below with:
- Feature name as the heading
- Related tasks
- Authors/editors
- A short explanation of what's non-obvious about it and why it's implemented the way it is

Keep entries updated as the described behavior changes; stale notes are worse than no notes.

## Ansible environments per bundle contract

- Related tasks: ADCM-8521
- Authors/editors: Aleksandr Alferov

The image temporarily ships both musl and glibc builds of ansible `2.21`. The environments are not relocatable
(the build prefix is baked into the ELF interpreter, RPATHs and shebangs), so each one lives in `/venv` exactly where
its ansible image builds it:

- `/venv/2.16`: musl (there is no glibc build of `2.16`: contract `2.2` doesn't support it);
- `/venv/2.21`: glibc;
- `/venv/2.21-musl`: musl.

The `venv` value bundles declare is **not** changed: the directory is resolved at job run time by
`cm.legacy.utils.get_venv_dir_name` from the declared `venv` and the bundle's `contract_version`:

| `venv` | `contract_version`     | directory         |
|--------|------------------------|-------------------|
| `2.21` | `2.2` and newer        | `/venv/2.21`      |
| `2.21` | `1.0`, `2.0`, `2.1`    | `/venv/2.21-musl` |
| `2.16` | any (up to `2.1`)      | `/venv/2.16`      |
| `adcm` | any                    | `/venv/adcm`      |

Only `venv` values listed in `VENVS_WITH_MUSL_BUILD` (`2.21`) have a separate musl directory.

The same directory is used for `PATH` and `ANSIBLE_COLLECTIONS_PATH`, so the `arenadata.adcm` collection is copied
into each environment (see `Dockerfile`, `Dockerfile.redos`).

Once musl builds are dropped, remove `get_venv_dir_name` and the `2.21-musl` environment from the Dockerfiles.

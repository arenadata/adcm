# Test conventions

Project-wide test rules that apply to this suite.

- Base: `GenericTestCase` (`python/tests/suites.py`) with `suite_setup = SETUP_WITH_RBAC`; `cls._initialize_roles_and_adcm()` in `setUpTestData`.
- Bundles go on FS as directories next to the tests (`tests/cases/<area>/bundles/...`), uploaded with `self.uc.upload_bundle(dir)`. No YAML templates inside test modules (allowed only for `core` tests).
- Plugin-executor paths may use `ADCMPluginExecutorSuite`-style executors directly.
- Run with `./run-tests.sh <label>` from the repo root (Postgres on :5500).
- `unittest_parametrize` is allowed, with identifier-safe ids. A parametrized body never branches on the param: write separate tests or parametrize the expected values.
- No private (`_`-prefixed) helpers in tests. Build shared expectations once in class setup.
- Code is typed. Public functions come before private ones in non-test modules (the snapshot module).
- No tests asserting that something is absent ("removed field is gone"). Empty golden diffs that record "no RBAC write" are a behaviour pin, not an absence test.
- The user manages commits and branches.

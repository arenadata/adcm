# ADCM Code Style

> Version: 1.0.0

Linters and type checking are the baseline of our code style — most of what would otherwise need to be written
down as a rule is meant to be enforced automatically by `make lint`. Right now they aren't turned on
strictly enough / for the whole codebase, so this document also specifies extra rules not (yet) covered by tooling.
Where neither tooling nor this document gives a direct rule, use official guidelines (e.g. `PEP8`) or common sense.

See [`ARCHITECTURE.md`](ARCHITECTURE.md) for how the project is structured and organized, and [`NOTES.md`](NOTES.md)
for commentary on specific non-obvious features.

## Exceptions

Tools sometimes get it wrong, and exceptional cases do occur, even if rarely. When that happens, silencing a
linter or type checker is allowed — but only with a comment explaining why. The same goes for any rule listed
below: there must be a reason to break it, and that reason should be visible at the point where it's broken.

## Rules

Grouped by what part of writing code they concern, roughly from most judgment-dependent to most mechanical.

### Hygiene & Maintenance

- Avoid TODO/FIXME. They are likely to be forgotten.
  Yet sometimes it's unavoidable, then add:
  - TODO/FIXME author
  - Task where to fix it
  - Descriptive message what should be done or not implemented at this point
- Docstrings and comments are the part of code and must be supported so it won't contradict the code itself:
  - Explain with code and typehints as much as possible
  - Comment on specific decisions/approaches taken (don't just describe what code does)
  - Write docstrings thoughtfully and make them durable or don't write them at all

### Structure & Design

- Don't use `__private` (dunder) class properties/methods.
- Order methods within a class: public, then protected, then (in test classes) test methods.
- Make as plain code structure as possible: avoid function-in-function and class-in-class
- Pass function arguments as named/keyword arguments only.

### Simple checks

- Use type annotations as much as possible (and check they are valid when code is out of typechecker default reach).
- Prefer f-string interpolation for `%`/`.format` formatting.
- Use `pathlib` instead of `os.path`.
- Don't import code from applications in migrations. If necessary, duplicate the code instead.

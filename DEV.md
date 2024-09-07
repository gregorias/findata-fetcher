# 🧰 Developer Documentation

This document is meant for developers and provides instruction on how to work
with the repository.

## Dev Environment Setup

This project requires [Lefthook](https://github.com/evilmartians/lefthook) and
[Commitlint](https://github.com/conventional-changelog/commitlint).

Set up Poetry

```bash
poetry install
```

Install lefthook:

```bash
lefthook install
```

Also install [direnv](https://direnv.net/) to benefit from some dev tools.

## Updating dependencies

To update locked dependencies, run

```shell
poetry update
```

From time to time, check if the major versions of dependencies in
`pyproject.toml` need updating.

## Testing

To run tests, use `testall`.

To run tests and check for coverage, use `coverage`.

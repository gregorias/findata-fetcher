# findata-fetcher

A scraper of personal financial data from websites.

UNDER DEVELOPMENT

This tool scrapes relevant financial data from diverse websites, e.g., Interactive Brokers, Degiro, UBS, into a CSV-file.

# Usage example

    $ pipenv shell
    $ python -m fetcher.tool output.csv

# Installation

    $ pip install --editable .

## Development notes

This section is meant for developers and provides instruction on how to work with the repository.

### Dev Environment Setup

The first time you start working with the repository, set up Pipenv:

    # Use 3.0 < x <= 3.7, because cefpython3 v66 does not support later version.
    # (https://github.com/cztomczak/cefpython/issues/546)
    pipenv install --python=3.7

Also install [direnv](https://direnv.net/) to benefit from some dev tools.

### Testing

In order to run tests, use `testall`.

In order to run tests and check for coverage use `coverage`.


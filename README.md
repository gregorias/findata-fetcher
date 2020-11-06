# findata-fetcher

A scraper of personal financial data from websites.

UNDER DEVELOPMENT

This tool scrapes relevant financial data from diverse websites, e.g., Interactive Brokers, Degiro, UBS, into a JSON-file.

## Installation

1. [Install Selenium Webdriver (geckodriver)](https://www.selenium.dev/documentation/en/selenium_installation/installing_webdriver_binaries/)
2. Run

    $ pip install --editable .

## Usage example

    $ pipenv shell # If not already using pipenv
    $ python -m fetcher.tool output.json

## Development notes

This section is meant for developers and provides instruction on how to work with the repository.

### Dev Environment Setup

The first time you start working with the repository, set up Pipenv:

    pipenv install

Also install [direnv](https://direnv.net/) to benefit from some dev tools.

### Testing

In order to run tests, use `testall`.

In order to run tests and check for coverage use `coverage`.

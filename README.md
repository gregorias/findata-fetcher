# findata-fetcher

This project is a collection of scripts that automate fetching or scraping
financial data from financial institutions' websites, e.g., Interactive
Brokers, BCGE.

You can use the fetched data to process it into a different database, e.g.,
[hledupt](https://github.com/gregorias/hledupt) uses this data to produce
plaintext accounting files.

## Installation

1. [Install Selenium Webdriver
   (geckodriver)](https://www.selenium.dev/documentation/en/selenium_installation/installing_webdriver_binaries/)
2. Run

    $ pip install --editable .

## Usage example

    $ pipenv shell # If not already using pipenv
    $ python -m fetcher.tool --help

## Development notes

This section is meant for developers and provides instruction on how to work with the repository.

### Dev Environment Setup

The first time you start working with the repository, set up Pipenv:

    pipenv install

Also install [direnv](https://direnv.net/) to benefit from some dev tools.

### Testing

To run tests, use `testall`.

To run tests and check for coverage, use `coverage`.

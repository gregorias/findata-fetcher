# findata-fetcher

This project is a collection of scripts that automate fetching statements or
scraping financial data from financial institutions' websites, e.g.,
Interactive Brokers, BCGE.

You can use the fetched data to process it into a different database, e.g.,
[hledupt](https://github.com/gregorias/hledupt) uses this data to produce
plaintext accounting files.

Currently implemented fetchers are:

* BCGE's account statement
* (BCGE CC) Viseca's latest credit card bill
* Coop receipt PDF from gmail
* Degiro's portfolio and account statements
* Finpension's transaction report (through gmail)
* Interactive Brokers' MTM summary statement
* mBank's account statement
* Splitwise's balance statement

## Installation

1. [Install Selenium Webdriver
   (geckodriver)](https://www.selenium.dev/documentation/en/selenium_installation/installing_webdriver_binaries/)
2. You have two choices for installation. I recommend using pipx, which will
   install the app in a standalone environment:

    pipx install .

   alternatively, you may just go with pip:

    pip install --editable .

### Shell completion

Findata-fetcher provides shell completion through [Click][click]. To enable
shell completion, follow [its
instructions](https://click.palletsprojects.com/en/8.1.x/shell-completion/#enabling-completion).

## Usage example

    pipenv shell # If not already using pipenv
    python -m fetcher.tool --help

[click]: https://click.palletsprojects.com/en/8.1.x/

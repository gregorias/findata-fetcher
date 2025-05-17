# 🧰 Developer Documentation

This document is meant for developers and provides instruction on how to work
with the repository.

## Dev Environment Setup

This project requires [Lefthook](https://github.com/evilmartians/lefthook) and
[Commitlint](https://github.com/conventional-changelog/commitlint).

Set up Uv

```bash
uv init
uv venv
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

## ADRs

### Entity-action naming

I name all Click *commands* starting with an *entity*, e.g., “BCGE,” followed by
the *action*, e.g., “fetch.”

There are plenty of *commands* that do not follow this naming scheme.
That’s OK, they are legacy commands. I don’t think it’s worth the effort
to update them.

### Use Playwright in favor of Selenium

I need to use a browser automation technology, and I decided to use Playwright:

- Playwright comes with a code generator tool.
- I found that Playwright comes with more relevant functionality, e.g.,
  capturing downloads.
- Playwright’s async support makes code more readable and easier to work with.

### Use 1Password SDK in favor of 1Password CLI

This app has previously used 1Password CLI, `op`. It should now use [the
SDK](https://developer.1password.com/docs/sdks/), because:

1. A dedicated Python library is more reliable and simpler than calling an
   external binary and parsing its output.
2. The app is more self-contained: the SDK can be downloaded as a dependency
   and I don’t need to separately install the CLI.

### No saving 1Password’s token in the config

This app has previously used a 1Password service account token saved in the
config file. I decided against that. The app has to never use the token in such
a way or a similar one in which it can be intercepted by other apps, e.g.,

- No saving to a file on a disk.
- No saving the secret to environment variables (subprocesses can see it then).

This is a security measure to limit the attack surface.

Fetcher can either fetch the token through 1Password directly or ask the caller
to provide it at runtime (e.g., through a prompt). Delegate secret management
up the stack.

### Save all secrets in 1Password

I keep all secrets in 1Password for the similar reasons as above: namely, to
limit the attack surface and secret-management complexity.

The secrets are even things like an OAuth token
[fetched by schwab-py](https://schwab-py.readthedocs.io/en/latest/auth.html#oauth-refresher).

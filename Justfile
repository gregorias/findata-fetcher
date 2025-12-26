bump:
  ./dev/bin/bump

coverage:
  uv run coverage run --source='fetcher/' --branch -m unittest discover -s test/ -t . && \
  uv run coverage html

mypy:
  mypy fetcher test

test: mypy unittest

unittest:
  python3 -m unittest discover -s test/ -t .

vulture:
  vulture fetcher/ vulture_allowlist.py

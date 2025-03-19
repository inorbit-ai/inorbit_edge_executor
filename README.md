# InOrbit Edge Executor

This package allows to execute InOrbit missions in connector robots.

## Installation

**Stable Release:** `pip install inorbit_edge_executor`<br>
**Development Head:**
`pip install git+https://github.com/inorbit-ai/inorbit_edge_executor.git`

## Development

See [CONTRIBUTING.md](CONTRIBUTING.md) for information related to developing
the code.

## The Three Commands You Need To Know

1. `pip install -e .[dev]`

   This will install your package in editable mode with all the required
   development dependencies (i.e. `tox`).

2. `make build`

   This will run `tox` which will run all your tests in Python 3.8 - 3.11 as
   well as linting your code.

3. `make clean`

   This will clean up various Python and build generated files so that you can
   ensure that you are working in a clean environment.
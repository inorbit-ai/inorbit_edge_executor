# InOrbit Edge Executor

This package allows to execute InOrbit missions in connector robots.

## Version >=3.0.0 disclaimer

Note that version 3.0.0 introduces some breaking changes compared to 2.0.0.

* Removed `MissionTrackingDatasource` (to be re-implemented as an optional dependency in a future
version).
* A new `DefaultTreeBuilder` that can be used to build behavior trees from mission definitions
with the behavior nodes included in this package.

In exchange `3.0.0` provides several fixes and feature parity with InOrbit's cloud executor.

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

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

## Using and integrating the package

This section explains how the package can be used to implement execution of missions from
InOrbit mission definitions. Requests to execute a mission are sent to the executor (normally part
of a robot connector) by InOrbit's mission dispatcher.

### Quickstart

The package provides a worker pool that executes missions using a Behavior Tree. The most common
pattern is to create a worker pool and submit to it missions received from InOrbit's dispatcher.

```python
import asyncio
from inorbit_edge_executor.inorbit import InOrbitAPI
from inorbit_edge_executor.worker_pool import WorkerPool
from inorbit_edge_executor.behavior_tree import DefaultTreeBuilder
from inorbit_edge_executor.mission import Mission
from inorbit_edge_executor.datatypes import MissionDefinition
from inorbit_edge_executor.dummy_backend import DummyDB

async def main():
    api = InOrbitAPI()
    pool = WorkerPool(db=DummyDB(), api=api, behavior_tree_builder=DefaultTreeBuilder())
    await pool.start()

    # Normally the mission is created and dispatched by InOrbit.
    # Here we assume you already have a mission id and definition.
    mission = Mission(id="<mission-id>", robot_id="<robot-id>", definition=MissionDefinition(label="Example", steps=[]))
    await pool.submit_work(mission)

    # Keep the pool running or shut down when appropriate
    await asyncio.sleep(5)
    await pool.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
```

### Running the included example

See `example.py` for a complete runnable program that:

- Starts a `WorkerPool` using `InOrbitAPI` and a simple in-memory `DummyDB`.
- Demonstrates translating mission steps into Behavior Tree nodes.
- Shows how to customize a step ("go to waypoint") with your own node.

Run it:

```bash
python example.py
```

The example will:

- Create a mock mission via the InOrbit mission tracking API (for demo purposes only; in production the dispatcher creates missions).
- Start the worker pool and submit the mission for execution.
- Execute two steps: a data-setting step and a custom waypoint step.

### Customizing behavior for your robot

You can define custom Behavior Tree nodes for robot-specific actions and teach the executor how to map mission steps to those nodes.

Key elements from `example.py`:

- **Custom node**: Subclass `BehaviorTree` and implement `async def _execute(self)` to perform the action.
- **Step-to-node builder**: Subclass `NodeFromStepBuilder` and implement `visit_<step_type>` methods (e.g., `visit_pose_waypoint`).
- **Tree builder**: Subclass `DefaultTreeBuilder` passing your custom step builder to control how trees are assembled.
- **Register node types**: Call `register_accepted_node_types([...])` so custom nodes can be serialized/deserialized.

Minimal outline:

```python
from inorbit_edge_executor.behavior_tree import (
    BehaviorTree, BehaviorTreeBuilderContext, DefaultTreeBuilder,
    NodeFromStepBuilder, register_accepted_node_types,
)

class MyWaypointNode(BehaviorTree):
    async def _execute(self):
        # Send robot to waypoint and wait until reached
        ...

register_accepted_node_types([MyWaypointNode])

class MyNodeFromStepBuilder(NodeFromStepBuilder):
    def visit_pose_waypoint(self, step):
        return MyWaypointNode(context=self.context, label=step.label, waypoint=step.waypoint)

class MyTreeBuilder(DefaultTreeBuilder):
    def __init__(self, *args, **kwargs):
        super().__init__(MyNodeFromStepBuilder, *args, **kwargs)
```

Then initialize the worker pool with `MyTreeBuilder()`:

```python
pool = WorkerPool(db=DummyDB(), api=InOrbitAPI(), behavior_tree_builder=MyTreeBuilder())
```

### Common concepts

- **WorkerPool**: Manages mission workers, start with `start()`, submit via `submit_work()`, and stop with `shutdown()`.
- **Mission**: Wraps mission id, robot id, definition, and optional runtime arguments.
- **Behavior Tree**: Execution engine for mission steps. `DefaultTreeBuilder` covers built-in steps; customize via your own builders and nodes.
- **Persistence**: Provide a DB (e.g., `DummyDB`) to allow worker serialization and resuming across restarts.

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

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

### Controlling the execution of a mission

The worker pool provides methods to control the execution of a mission:
- `pause_mission()`: Pauses a running mission.
- `resume_mission()`: Resumes a paused mission.
- `abort_mission()`: Cancels a running mission.

A robot Connector should implement the handling of the custom commands `"executeMissionAction"`, `"cancelMissionAction"` and `"updateMissionAction"` and call the corresponding methods in the worker pool to control a mission.

<!-- TODO(b-Tomas): move this to a working example -->

The following is a minimal [inorbit-connector](https://github.com/inorbit-ai/inorbit-connector-python) commands handler example that implements said commands:

```python
import json
from typing import override
from inorbit_edge.robot import COMMAND_CUSTOM_COMMAND
from inorbit_connector.connector import CommandResultCode, Connector # inorbit-connector~=1.2.1

def parse_args(args) -> dict:
    """Parse InOrbit command arguments to key-value pairs"""
    args_raw = list(args[1])
    script_args = {}
    if (
        isinstance(args_raw, list)
        and len(args_raw) % 2 == 0
        and all(isinstance(key, str) for key in args_raw[::2])
    ):
        script_args = dict(zip(args_raw[::2], args_raw[1::2]))
        return script_args
    else:
        return None


class ExampleRobot(Connector):
    """
    Example robot snippet that implements the custom command handler.
    It assumes a worker pool is has been initialized..
    """
    ...

    @override
    async def _inorbit_command_handler(robot_id, command_name, args, options):
    """Handler for processing custom command calls.
    Refer to https://github.com/inorbit-ai/inorbit-connector-python for documentation.
    """
    if command_name == COMMAND_CUSTOM_COMMAND:
        script_name = args[0]
        script_args = parse_args(args)

        if script_args is None:
            return options["result_function"](CommandResultCode.FAILURE, "Invalid arguments")

        if script_name == "executeMissionAction"
            mission = Mission(
                id=script_args.get("missionId"),
                robot_id=self.robot_id,
                definition=json.loads(script_args.get("missionDefinition", "{}")),
                arguments=json.loads(script_args.get("missionArgs", "{}")),
            )

            mission_runtime_options = MissionRuntimeOptions(**json.loads(script_args.get("options", "{}")))

            await self._worker_pool.submit_work(mission, mission_runtime_options)

        elif script_name == "cancelMissionAction":
            await self._worker_pool.abort_mission(script_args.get("missionId"))

        elif script_name == "updateMissionAction":
            mission_id = script_args.get("missionId")
            action = script_args.get("action")
            if action == "pause":
                await self._worker_pool.pause_mission(mission_id)
            elif action == "resume":
                await self._worker_pool.resume_mission(mission_id)
            else:
                return options["result_function"](CommandResultCode.FAILURE, "Invalid action")

    options["result_function"](CommandResultCode.SUCCESS)
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

# This program uses inorbit_edge_executor to implement execution of missions
# given mission definitions that are received from InOrbit's missions dispatcher.
# (More commonly this functionality would be integrated as part of a robot connector.)
#
# The package provides a worker pool functionality that takes care of executing
# missions. The out of the box implementation uses InOrbit APIs to implement the different
# steps.
#
# In this example we use the default behavior provided by the package, but customizing
# how the go to waypoint step is implemented. To achieve this we define:
# - MyWaypointNode: a behavior tree node that implements the go to waypoint step
# - MyWaypointNodeBuilder: a builder that translates mission definition steps to beavhior tree
#   nodes.
# - MyTreeBuilder: a builder that translates a mission definition to a behavior tree to execute
# the mission.

import asyncio
import logging
import os
from uuid import uuid4
from inorbit_edge_executor.behavior_tree import (
    DefaultTreeBuilder,
    BehaviorTree,
    NodeFromStepBuilder,
    BehaviorTreeBuilderContext,
    register_accepted_node_types,
)
from inorbit_edge_executor.datatypes import (
    MissionDefinition,
    MissionRuntimeOptions,
    MissionStepSetData,
    MissionStepPoseWaypoint,
    MissionStepIf,
    Pose,
)
from inorbit_edge_executor.worker_pool import WorkerPool
from inorbit_edge_executor.dummy_backend import DummyDB
from inorbit_edge_executor.inorbit import InOrbitAPI
from inorbit_edge_executor.mission import Mission

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class MyWaypointNode(BehaviorTree):
    """
    Node to make the robot go to a waypoint. It should wait for the robot to reach the waypoint
    before completing execution.
    """

    def __init__(self, context: BehaviorTreeBuilderContext, waypoint: Pose, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.waypoint = waypoint
        self.robot_id = context.robot_api.robot_id

    async def _execute(self):
        print(f"Sending robot {self.robot_id} to waypoint {self.waypoint}")
        print(f"Waiting for robot {self.robot_id} to reach waypoint {self.waypoint}")
        await asyncio.sleep(1)
        print(f"Robot {self.robot_id} reached waypoint {self.waypoint}")

    def dump_object(self):
        object = super().dump_object()
        object["waypoint"] = self.waypoint.copy()
        return object

    @classmethod
    def from_object(cls, context, waypoint, **kwargs):
        node = MyWaypointNode(context, waypoint, **kwargs)
        return node


# Register the new node type so it can be deserialized when needed
register_accepted_node_types([MyWaypointNode])


class MyNodeFromStepBuilder(NodeFromStepBuilder):
    """Translate mission definition steps to behavior tree nodes"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def visit_pose_waypoint(self, step: MissionStepPoseWaypoint):
        return MyWaypointNode(context=self.context, label=step.label, waypoint=step.waypoint)


class MyTreeBuilder(DefaultTreeBuilder):
    """Build a behavior tree from a mission definition"""

    def __init__(self, *args, **kwargs):
        super().__init__(MyNodeFromStepBuilder, *args, **kwargs)


async def main():
    """Run the mission executor"""
    # A database can be used to serialize workers, so they can be resumed on restarts
    db = DummyDB()
    # InOrbit API is used for various purpose, including: mission tracking,
    # evaluating expressions, dispatching actions and more
    INORBIT_API_KEY = os.getenv("INORBIT_API_KEY")
    if INORBIT_API_KEY is None:
        raise ValueError("INORBIT_API_KEY environment variable is not set")

    INORBIT_API_BASE_URL = os.getenv("INORBIT_API_BASE_URL", "https://api.inorbit.ai")

    ROBOT_ID = os.getenv("ROBOT_ID")
    if ROBOT_ID is None:
        raise ValueError("ROBOT_ID environment variable is not set")

    inorbit_api = InOrbitAPI(base_url=INORBIT_API_BASE_URL, api_key=INORBIT_API_KEY)
    worker_pool = WorkerPool(db=db, api=inorbit_api, behavior_tree_builder=MyTreeBuilder())
    # Mission should be already created in InOrbit during the dispatching. Here we mock that by
    # manually creating it using the mission tracking API.
    # This is not needed in real scenarios, as the mission is already created in InOrbit.
    mission_id = uuid4().hex
    logger.info(f"Creating mission {mission_id}")
    await inorbit_api.post(
        path="/missions",
        body={
            "missionId": mission_id,
            "robotId": ROBOT_ID,
            "state": "starting",
            "label": "Example inorbit_edge_executor mission",
            "tasks": [
                {"taskId": "step 0", "label": "Step 0"},
                {"taskId": "step 1", "label": "Step 1"},
                {"taskId": "step 2", "label": "Step 2"},
                {"taskId": "step 3", "label": "Then waypoint A"},
                {"taskId": "step 4", "label": "Else waypoint B"},
            ],
        },
    )
    # Launch the worker pool to start processing missions
    await worker_pool.start()
    # Execute a mission
    mission = Mission(
        id=mission_id,
        robot_id=ROBOT_ID,
        definition=MissionDefinition(
            label="A mission definition",
            steps=[
                MissionStepSetData.model_validate({
                    "label": "set some data",
                    "completeTask": "step 0",
                    "data": {"key": "value"},
                }),
                MissionStepSetData.model_validate({
                    "label": "set more data",
                    "completeTask": "step 1",
                    "data": {"key2": "value2"},
                }),
                MissionStepPoseWaypoint.model_validate({
                    "label": "go to waypoint",
                    "completeTask": "step 2",
                    "waypoint": {
                        "x": 0,
                        "y": 0,
                        "theta": 0,
                        "frameId": "map",
                        "waypointId": "wp1",
                    },
                }),
                MissionStepIf.model_validate({
                    "label": "if",
                    "if": {
                        "expression": "0 > 1",
                        "then": [
                            {
                                "label": "go to waypoint A",
                                "completeTask": "step 3",
                                "waypoint": {
                                    "x": 0,
                                    "y": 0,
                                    "theta": 0,
                                    "frameId": "map",
                                    "waypointId": "wpA",
                                },
                            },
                        ],
                        "else": [
                            {
                                "label": "go to waypoint B",
                                "completeTask": "step 4",
                                "waypoint": {
                                    "x": 0,
                                    "y": 0,
                                    "theta": 0,
                                    "frameId": "map",
                                    "waypointId": "wpB",
                                },
                            },
                        ],
                    }
                }),
            ],
        ),
        arguments={"arg1": "value1"},
    )
    options = MissionRuntimeOptions()
    await worker_pool.submit_work(mission=mission, options=options)
    # sleep 5 seconds so the workers have time to run
    await asyncio.sleep(5)
    await worker_pool.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

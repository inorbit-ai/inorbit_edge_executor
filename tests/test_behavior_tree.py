from logging import getLogger

import pytest
from inorbit_edge_executor.behavior_tree import (
    BehaviorTree,
    DefaultTreeBuilder,
    BehaviorTreeBuilderContext,
)
from inorbit_edge_executor.datatypes import MissionDefinition
from inorbit_edge_executor.datatypes import MissionRuntimeOptions
from inorbit_edge_executor.datatypes import MissionRuntimeSharedMemory
from inorbit_edge_executor.dummy_backend import DummyDB
from inorbit_edge_executor.inorbit import InOrbitAPI
from inorbit_edge_executor.inorbit import RobotApiFactory
from inorbit_edge_executor.mission import Mission

logger = getLogger("test-bt")


@pytest.fixture
def inorbit_api():
    return InOrbitAPI(base_url="http://inorbit", api_key="secret")


def test_bt_build_simple(inorbit_api):
    """
    This test only builds a basic mission tree with no steps, to validate its 'skeleton': the
    error handlers, mission start/completion nodes, etc. No actual steps are validated.
    """
    mission: Mission = Mission(
        id="mission123",
        robot_id="robot123",
        definition=MissionDefinition(label="A mission", steps=[]),
    )
    context = BehaviorTreeBuilderContext()
    context.mission = mission
    context.options = MissionRuntimeOptions()
    context.shared_memory = MissionRuntimeSharedMemory()
    tree: BehaviorTree = DefaultTreeBuilder().build_tree_for_mission(context)
    logger.info(tree.dump_object())
    expected_obj = {
        "type": "BehaviorTreeErrorHandler",
        "state": "",
        "label": "mission mission123",
        "children": [
            {
                "type": "BehaviorTreeSequential",
                "state": "",
                "label": "mission mission123",
                "children": [
                    {"type": "MissionInProgressNode", "state": "", "label": "mission start"},
                    {"type": "MissionCompletedNode", "state": "", "label": "mission completed"},
                    {
                        "type": "UnlockRobotNode",
                        "state": "",
                        "label": "unlock robot after mission completed",
                    },
                ],
            }
        ],
        "error_handler": {
            "type": "BehaviorTreeSequential",
            "state": "",
            "label": "error handlers",
            "children": [
                {
                    "type": "MissionAbortedNode",
                    "state": "",
                    "label": "mission aborted",
                    "status": "error",
                },
                {
                    "type": "UnlockRobotNode",
                    "state": "",
                    "label": "unlock robot after mission abort",
                },
            ],
        },
        "cancelled_handler": {
            "type": "BehaviorTreeSequential",
            "state": "",
            "label": "cancel handlers",
            "children": [
                {
                    "type": "MissionAbortedNode",
                    "state": "",
                    "label": "mission cancelled",
                    "status": "OK",
                },
                {
                    "type": "UnlockRobotNode",
                    "state": "",
                    "label": "unlock robot after mission cancel",
                },
            ],
        },
        "pause_handler": {
            "type": "BehaviorTreeSequential",
            "state": "",
            "label": "pause handlers",
            "children": [{"type": "MissionPausedNode", "state": "", "label": "mission paused"}],
        },
        "reset_execution_on_pause": False,
    }
    assert expected_obj == tree.dump_object()


def test_bt_wait():
    """
    Tests parsing and serializing of a simple wait (timeoutSecs) node
    """
    steps = [{"timeoutSecs": 10}]
    mission: Mission = Mission(
        id="mission123",
        # robot=Robot(id="robot123"),
        robot_id="robot123",
        definition=MissionDefinition(label="A mission", steps=steps),
    )
    context = BehaviorTreeBuilderContext()
    context.mission = mission
    context.options = MissionRuntimeOptions()
    tree: BehaviorTree = DefaultTreeBuilder().build_tree_for_mission(context)
    tree_obj = tree.dump_object()
    # Since we know the structure of the tree (tested in the first test), only fetch the node
    # corresponding to the step created
    assert len(tree_obj["children"]) == 1
    sequential_node = tree_obj["children"][0]
    assert len(sequential_node["children"]) == 5
    step_node = sequential_node["children"][2]
    logger.info(step_node)
    expected_obj = {"type": "WaitNode", "state": "", "wait_seconds": 10.0}
    assert expected_obj == step_node


def test_bt_wait_expression():
    """
    Tests parsing and serializing of a wait for an expression value
    """
    steps = [{"waitUntil": {"expression": "0>1", "target": {"robotId": "robot456"}}}]
    mission: Mission = Mission(
        id="mission123",
        # robot=Robot(id="robot123"),
        robot_id="robot123",
        definition=MissionDefinition(label="A mission", steps=steps),
    )
    api: InOrbitAPI = InOrbitAPI(base_url="localhost:1000", api_key="secret")
    context = BehaviorTreeBuilderContext()
    context.robot_api_factory = RobotApiFactory(api)
    context.mission = mission
    context.options = MissionRuntimeOptions()
    tree: BehaviorTree = DefaultTreeBuilder().build_tree_for_mission(context)
    tree_obj = tree.dump_object()
    # Since we know the structure of the tree (tested in the first test), only fetch the node
    # corresponding to the step created
    assert len(tree_obj["children"]) == 1
    sequential_node = tree_obj["children"][0]
    assert len(sequential_node["children"]) == 5
    step_node = sequential_node["children"][2]
    logger.info(step_node)
    expected_obj = {
        "type": "WaitExpressionNode",
        "state": "",
        "expression": "0>1",
        "target": {"robot_id": "robot456"},
        "retry_wait_secs": 3,
    }
    assert expected_obj == step_node


def test_bt_set_data():
    """
    Tests parsing and serializing of a wait for an expression value
    """
    steps = [{"data": {"repeatId": "abcde"}}]
    mission: Mission = Mission(
        id="mission123",
        # robot=Robot(id="robot123"),
        robot_id="robot123",
        definition=MissionDefinition(label="A mission", steps=steps),
    )
    context = BehaviorTreeBuilderContext()
    context.mission = mission
    context.options = MissionRuntimeOptions()
    tree: BehaviorTree = DefaultTreeBuilder().build_tree_for_mission(context)
    tree_obj = tree.dump_object()
    # Since we know the structure of the tree (tested in the first test), only fetch the node
    # corresponding to the step created
    assert len(tree_obj["children"]) == 1
    sequential_node = tree_obj["children"][0]
    assert len(sequential_node["children"]) == 5
    step_node = sequential_node["children"][2]
    logger.info(step_node)
    expected_obj = {"type": "SetDataNode", "state": "", "data": {"repeatId": "abcde"}}
    assert expected_obj == step_node

import pytest
import httpx
from pytest_httpx import HTTPXMock
from inorbit_edge_executor.behavior_tree import (
    NODE_STATE_SUCCESS,
    WaitExpressionNode,
    BehaviorTreeBuilderContext,
)
from inorbit_edge_executor.inorbit import RobotApiFactory
from inorbit_edge_executor.datatypes import Target

# test building from mission definition
# test serialize deserialize


@pytest.mark.asyncio
async def test_wait_expression_node(httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory):
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    eval_count = 0  # Count of times the expression is evaluated to simulate two evaluations

    def custom_response(request: httpx.Request):
        nonlocal eval_count
        if (
            request.method == "POST"
            and request.url.path == "/expressions/robot/robot123/eval"
            and request.content.decode("utf-8") == '{"expression":"getValue(\'battery\') > 20"}'
        ):
            eval_count += 1
            return httpx.Response(
                status_code=200,
                json={"success": True, "value": eval_count == 2},
            )
        return httpx.Response(status_code=400, json={"success": False, "message": "Invalid"})

    httpx_mock.add_callback(custom_response, is_reusable=True)
    node = WaitExpressionNode(
        context, "getValue('battery') > 20", label="wait expression", retry_wait_secs=0.1
    )
    await node.execute()
    assert node.state == NODE_STATE_SUCCESS


@pytest.mark.asyncio
async def test_wait_expression_node_with_target(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    httpx_mock.add_response(
        method="POST",
        url=f"http://unittest/expressions/robot/robotX/eval",
        json={"success": True, "value": True},
    )
    node = WaitExpressionNode(
        context,
        "getValue('battery') > 20",
        label="wait expression",
        target=Target(robotId="robotX"),
    )
    await node.execute()
    assert node.state == NODE_STATE_SUCCESS


def test_serialize(empty_context: BehaviorTreeBuilderContext):
    node = WaitExpressionNode(
        empty_context,
        "getValue('battery') > 20",
        label="wait expression",
        target=Target(robotId="robotX"),
        retry_wait_secs=2,
    )
    serialized = node.dump_object()
    assert serialized["expression"] == "getValue('battery') > 20"
    assert serialized["target"]["robot_id"] == "robotX"
    assert serialized["retry_wait_secs"] == 2


def test_deserialize(empty_context: BehaviorTreeBuilderContext):
    serialized = {
        "expression": "getValue('battery') > 20",
        "target": {"robot_id": "robotX"},
        "retry_wait_secs": 2,
    }
    node = WaitExpressionNode.from_object(empty_context, **serialized)
    assert node.expression == "getValue('battery') > 20"
    assert node.target.robot_id == "robotX"
    assert node.retry_wait_secs == 2

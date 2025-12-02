import pytest
import httpx
from pytest_httpx import HTTPXMock
from inorbit_edge_executor.behavior_tree import (
    NODE_STATE_SUCCESS,
    NODE_STATE_ERROR,
    IfNode,
    BehaviorTreeBuilderContext,
    BehaviorTreeSequential,
    DummyNode,
)
from inorbit_edge_executor.inorbit import RobotApiFactory
from inorbit_edge_executor.datatypes import Target


@pytest.mark.asyncio
async def test_if_node_executes_then_branch_when_true(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    """Test that IfNode executes then_branch when expression evaluates to True."""
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    # Mock expression evaluation returning True
    httpx_mock.add_response(
        method="POST",
        url="http://unittest/expressions/robot/robot123/eval",
        json={"success": True, "value": True},
    )

    # Create then and else branches
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))
    
    else_branch = BehaviorTreeSequential(label="else")
    else_branch.add_node(DummyNode(label="else_node"))

    node = IfNode(
        context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=else_branch,
        label="if node",
    )

    await node.execute()
    assert node.state == NODE_STATE_SUCCESS
    assert then_branch.state == NODE_STATE_SUCCESS
    assert then_branch.nodes[0].already_executed()
    # else_branch should not have executed
    assert not else_branch.nodes[0].already_executed()


@pytest.mark.asyncio
async def test_if_node_executes_else_branch_when_false(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    """Test that IfNode executes else_branch when expression evaluates to False."""
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    # Mock expression evaluation returning False
    httpx_mock.add_response(
        method="POST",
        url="http://unittest/expressions/robot/robot123/eval",
        json={"success": True, "value": False},
    )

    # Create then and else branches
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))
    
    else_branch = BehaviorTreeSequential(label="else")
    else_branch.add_node(DummyNode(label="else_node"))

    node = IfNode(
        context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=else_branch,
        label="if node",
    )

    await node.execute()
    assert node.state == NODE_STATE_SUCCESS
    # then_branch should not have executed
    assert not then_branch.nodes[0].already_executed()
    assert else_branch.state == NODE_STATE_SUCCESS
    assert else_branch.nodes[0].already_executed()


@pytest.mark.asyncio
async def test_if_node_succeeds_when_false_no_else_branch(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    """Test that IfNode succeeds (no-op) when expression is False and no else_branch exists."""
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    # Mock expression evaluation returning False
    httpx_mock.add_response(
        method="POST",
        url="http://unittest/expressions/robot/robot123/eval",
        json={"success": True, "value": False},
    )

    # Create only then branch
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))

    node = IfNode(
        context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=None,
        label="if node",
    )

    await node.execute()
    assert node.state == NODE_STATE_SUCCESS
    # then_branch should not have executed
    assert not then_branch.nodes[0].already_executed()


@pytest.mark.asyncio
async def test_if_node_with_target(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    """Test that IfNode evaluates expression on target robot when target is provided."""
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    # Mock expression evaluation on target robot
    httpx_mock.add_response(
        method="POST",
        url="http://unittest/expressions/robot/robot456/eval",
        json={"success": True, "value": True},
    )

    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))

    node = IfNode(
        context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        target=Target(robotId="robot456"),
        label="if node",
    )

    await node.execute()
    assert node.state == NODE_STATE_SUCCESS
    assert then_branch.state == NODE_STATE_SUCCESS


@pytest.mark.asyncio
async def test_if_node_propagates_error_from_expression_evaluation(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    """Test that IfNode propagates error when expression evaluation fails."""
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    # Mock expression evaluation returning error
    httpx_mock.add_response(
        method="POST",
        url="http://unittest/expressions/robot/robot123/eval",
        status_code=500,
        json={"success": False, "message": "Internal server error"},
    )

    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))

    node = IfNode(
        context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        label="if node",
    )

    await node.execute()
    assert node.state == NODE_STATE_ERROR
    # then_branch should not have executed
    assert not then_branch.nodes[0].already_executed()


@pytest.mark.asyncio
async def test_if_node_propagates_state_from_executed_branch(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory
):
    """Test that IfNode propagates state and error from executed branch."""
    robot = robot_api_factory.build("robot123")
    context = BehaviorTreeBuilderContext(
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )

    # Mock expression evaluation returning True
    httpx_mock.add_response(
        method="POST",
        url="http://unittest/expressions/robot/robot123/eval",
        json={"success": True, "value": True},
    )

    # Create then branch with a node that will error
    class ErrorNode(DummyNode):
        async def _execute(self):
            raise Exception("Test error")

    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(ErrorNode(label="error_node"))

    else_branch = BehaviorTreeSequential(label="else")
    else_branch.add_node(DummyNode(label="else_node"))

    node = IfNode(
        context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=else_branch,
        label="if node",
    )

    await node.execute()
    assert node.state == NODE_STATE_ERROR
    assert "Test error" in node.last_error
    assert then_branch.state == NODE_STATE_ERROR


def test_if_node_serialize(empty_context: BehaviorTreeBuilderContext):
    """Test serialization of IfNode."""
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))
    
    else_branch = BehaviorTreeSequential(label="else")
    else_branch.add_node(DummyNode(label="else_node"))

    node = IfNode(
        empty_context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=else_branch,
        target=Target(robotId="robot456"),
        label="if node",
    )

    serialized = node.dump_object()
    assert serialized["type"] == "IfNode"
    assert serialized["expression"] == "getValue('battery') > 50"
    assert serialized["target"]["robot_id"] == "robot456"
    assert serialized["then_branch"]["type"] == "BehaviorTreeSequential"
    assert serialized["else_branch"]["type"] == "BehaviorTreeSequential"


def test_if_node_serialize_no_else_branch(empty_context: BehaviorTreeBuilderContext):
    """Test serialization of IfNode without else_branch."""
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))

    node = IfNode(
        empty_context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=None,
        label="if node",
    )

    serialized = node.dump_object()
    assert serialized["type"] == "IfNode"
    assert serialized["expression"] == "getValue('battery') > 50"
    assert "else_branch" not in serialized
    assert serialized["then_branch"]["type"] == "BehaviorTreeSequential"


def test_if_node_deserialize(empty_context: BehaviorTreeBuilderContext):
    """Test deserialization of IfNode."""
    serialized = {
        "expression": "getValue('battery') > 50",
        "target": {"robot_id": "robot456"},
        "then_branch": {
            "type": "BehaviorTreeSequential",
            "state": "",
            "label": "then",
            "children": [{"type": "DummyNode", "state": "", "label": "then_node"}],
        },
        "else_branch": {
            "type": "BehaviorTreeSequential",
            "state": "",
            "label": "else",
            "children": [{"type": "DummyNode", "state": "", "label": "else_node"}],
        },
        "state": "",
        "label": "if node",
    }

    node = IfNode.from_object(empty_context, **serialized)
    assert node.expression == "getValue('battery') > 50"
    assert node.target.robot_id == "robot456"
    assert isinstance(node.then_branch, BehaviorTreeSequential)
    assert isinstance(node.else_branch, BehaviorTreeSequential)
    assert len(node.then_branch.nodes) == 1
    assert len(node.else_branch.nodes) == 1


def test_if_node_deserialize_no_else_branch(empty_context: BehaviorTreeBuilderContext):
    """Test deserialization of IfNode without else_branch."""
    serialized = {
        "expression": "getValue('battery') > 50",
        "then_branch": {
            "type": "BehaviorTreeSequential",
            "state": "",
            "label": "then",
            "children": [{"type": "DummyNode", "state": "", "label": "then_node"}],
        },
        "state": "",
        "label": "if node",
    }

    node = IfNode.from_object(empty_context, **serialized)
    assert node.expression == "getValue('battery') > 50"
    assert isinstance(node.then_branch, BehaviorTreeSequential)
    assert node.else_branch is None


def test_if_node_collect_nodes(empty_context: BehaviorTreeBuilderContext):
    """Test that collect_nodes recursively collects all nodes from both branches."""
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node1"))
    then_branch.add_node(DummyNode(label="then_node2"))
    
    else_branch = BehaviorTreeSequential(label="else")
    else_branch.add_node(DummyNode(label="else_node"))

    node = IfNode(
        empty_context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=else_branch,
        label="if node",
    )

    nodes_list = []
    node.collect_nodes(nodes_list)
    # Should collect: IfNode, then_branch Sequential, 2 then nodes, else_branch Sequential, 1 else node
    assert len(nodes_list) == 6
    assert nodes_list[0] == node
    assert nodes_list[1] == then_branch
    assert nodes_list[4] == else_branch


def test_if_node_reset_execution(empty_context: BehaviorTreeBuilderContext):
    """Test that reset_execution resets both branches."""
    then_branch = BehaviorTreeSequential(label="then")
    then_branch.add_node(DummyNode(label="then_node"))
    
    else_branch = BehaviorTreeSequential(label="else")
    else_branch.add_node(DummyNode(label="else_node"))

    node = IfNode(
        empty_context,
        expression="getValue('battery') > 50",
        then_branch=then_branch,
        else_branch=else_branch,
        label="if node",
    )

    # Mark nodes as executed
    then_branch.nodes[0].state = NODE_STATE_SUCCESS
    else_branch.nodes[0].state = NODE_STATE_SUCCESS
    node.state = NODE_STATE_SUCCESS

    # Reset execution
    node.reset_execution()

    assert node.state == ""
    assert then_branch.nodes[0].state == ""
    assert else_branch.nodes[0].state == ""


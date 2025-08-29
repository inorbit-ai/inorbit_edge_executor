import pytest
import asyncio
from inorbit_edge_executor.exceptions import TaskPausedException
from inorbit_edge_executor.behavior_tree import (
    BehaviorTreeErrorHandler,
    NODE_STATE_SUCCESS,
    NODE_STATE_CANCELLED,
    NODE_STATE_PAUSED,
    DummyNode,
    BehaviorTree,
    CANCEL_TASK_PAUSE_MESSAGE,
    BehaviorTreeBuilderContext,
)

SHORT_SLEEP_TIME = 0.05


class BadNode(BehaviorTree):
    """A simple node that raises an exception"""

    async def _execute(self):
        raise Exception("Bad node")


class SlowNode(BehaviorTree):
    """A simple node that takes a long time to execute"""

    async def _execute(self):
        await asyncio.sleep(SHORT_SLEEP_TIME)


@pytest.mark.asyncio
async def test_error_handler_invoked_on_error():
    bad_node = BadNode()
    error_handler = DummyNode()
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=bad_node,
        error_handler=error_handler,
        cancelled_handler=None,
    )
    await node.execute()
    assert node.state == NODE_STATE_SUCCESS
    assert error_handler.already_executed()


@pytest.mark.asyncio
async def test_cancel_handler_invoked_on_cancelled():
    cancel_handler = DummyNode()
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=SlowNode(),
        error_handler=None,
        cancelled_handler=cancel_handler,
    )
    task = asyncio.create_task(node.execute())
    await asyncio.sleep(SHORT_SLEEP_TIME)
    task.cancel()
    await task
    assert node.state == NODE_STATE_SUCCESS  # Set by the cancel handler
    assert cancel_handler.already_executed()


@pytest.mark.asyncio
async def test_cancel_handler_is_optional():
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=SlowNode(),
        error_handler=None,
        cancelled_handler=None,
    )
    task = asyncio.create_task(node.execute())
    await asyncio.sleep(SHORT_SLEEP_TIME)
    task.cancel()
    await task
    assert node.state == NODE_STATE_CANCELLED


@pytest.mark.asyncio
async def test_pause_handler_invoked_on_paused():
    pause_handler = DummyNode()
    behavior_tree = SlowNode()
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=behavior_tree,
        error_handler=None,
        cancelled_handler=None,
        pause_handler=pause_handler,
    )
    task = asyncio.create_task(node.execute())
    try:
        await asyncio.sleep(SHORT_SLEEP_TIME)
        task.cancel(CANCEL_TASK_PAUSE_MESSAGE)
        await task
    except TaskPausedException:
        pass
    assert behavior_tree.state == NODE_STATE_PAUSED
    assert pause_handler.already_executed()


@pytest.mark.asyncio
async def test_pause_can_reset_execution():
    pause_handler = DummyNode()
    behavior_tree = SlowNode()
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=behavior_tree,
        error_handler=None,
        cancelled_handler=None,
        pause_handler=pause_handler,
        reset_execution_on_pause=True,
    )
    task = asyncio.create_task(node.execute())
    try:
        await asyncio.sleep(SHORT_SLEEP_TIME)
        task.cancel(CANCEL_TASK_PAUSE_MESSAGE)
        await task
    except TaskPausedException:
        pass
    assert behavior_tree.state == ""


def test_serialize():
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=DummyNode(label="behavior_tree"),
        error_handler=DummyNode(label="error_handler"),
        cancelled_handler=DummyNode(label="cancelled_handler"),
        pause_handler=DummyNode(label="pause_handler"),
    )
    serialized = node.dump_object()
    assert serialized["children"][0]["label"] == "behavior_tree"
    assert serialized["error_handler"]["label"] == "error_handler"
    assert serialized["cancelled_handler"]["label"] == "cancelled_handler"
    assert serialized["pause_handler"]["label"] == "pause_handler"


def test_deserialize(empty_context: BehaviorTreeBuilderContext):
    serialized = {
        "children": [{"type": "DummyNode", "state": "", "label": "behavior_tree"}],
        "error_handler": {"type": "DummyNode", "state": "", "label": "error_handler"},
        "cancelled_handler": {"type": "DummyNode", "state": "", "label": "cancelled_handler"},
        "pause_handler": {"type": "DummyNode", "state": "", "label": "pause_handler"},
        "reset_execution_on_pause": True,
    }
    node = BehaviorTreeErrorHandler.from_object(empty_context, **serialized)
    assert node.behavior.label == "behavior_tree"


def test_collect_nodes():
    node = BehaviorTreeErrorHandler(
        context=None,
        behavior=DummyNode(label="behavior_tree"),
        error_handler=DummyNode(label="error_handler"),
        cancelled_handler=DummyNode(label="cancelled_handler"),
        pause_handler=DummyNode(label="pause_handler"),
    )
    nodes = []
    node.collect_nodes(nodes)
    assert len(nodes) == 5, "Expected parent + 4 children"

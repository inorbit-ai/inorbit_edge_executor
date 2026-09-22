import asyncio

import pytest
from inorbit_edge_executor.behavior_tree import (
    BehaviorTreeSequential,
    CANCEL_TASK_PAUSE_MESSAGE,
    DummyNode,
    BehaviorTree,
    NODE_STATE_PAUSED,
    NODE_STATE_SUCCESS,
    TimeoutNode,
)

SHORT_SLEEP_TIME = 0.05


class SlowNode(BehaviorTree):
    """A simple node that takes a long time to execute"""

    async def _execute(self):
        await asyncio.sleep(SHORT_SLEEP_TIME * 10)


@pytest.mark.asyncio
async def test_timeout_node_propagates_paused_state():
    slow_node = SlowNode()
    after_node = DummyNode()
    sequence = BehaviorTreeSequential()
    sequence.add_node(TimeoutNode(60, slow_node))
    sequence.add_node(after_node)
    task = asyncio.create_task(sequence.execute())
    await asyncio.sleep(SHORT_SLEEP_TIME)
    task.cancel(CANCEL_TASK_PAUSE_MESSAGE)
    await task
    assert slow_node.state == NODE_STATE_PAUSED
    assert sequence.state == NODE_STATE_PAUSED
    assert not after_node.already_executed()


@pytest.mark.asyncio
async def test_timeout_node_succeeds_when_wrapped_node_succeeds():
    node = TimeoutNode(60, DummyNode())
    await node.execute()
    assert node.state == NODE_STATE_SUCCESS

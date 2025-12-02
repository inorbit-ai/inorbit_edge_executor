import pytest
from inorbit_edge_executor.datatypes import (
    MissionStepIf,
    MissionStepSetData,
    MissionStepWait,
    MissionStepTypes,
    MissionDefinition,
)


def test_mission_step_if_basic():
    """Test basic MissionStepIf creation with if branch only."""
    step = MissionStepIf(
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "then": [{"data": {"key": "value"}}],
            }
        }
    )
    assert step.expression == "getValue('battery') > 50"
    assert step.target is None
    assert len(step.then) == 1
    assert isinstance(step.then[0], MissionStepSetData)
    assert step.else_ is None
    assert step.get_type() == MissionStepTypes.IF.value


def test_mission_step_if_with_else():
    """Test MissionStepIf creation with both if and else branches."""
    step = MissionStepIf(
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "then": [{"data": {"key": "if_value"}}],
                "else": [{"data": {"key": "else_value"}}],
            }
        }
    )
    assert step.expression == "getValue('battery') > 50"
    assert len(step.then) == 1
    assert isinstance(step.then[0], MissionStepSetData)
    assert step.then[0].data["key"] == "if_value"
    assert len(step.else_) == 1
    assert isinstance(step.else_[0], MissionStepSetData)
    assert step.else_[0].data["key"] == "else_value"


def test_mission_step_if_with_target():
    """Test MissionStepIf creation with target."""
    step = MissionStepIf(
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "target": {"robotId": "robot456"},
                "then": [{"timeoutSecs": 10}],
            }
        }
    )
    assert step.expression == "getValue('battery') > 50"
    assert step.target is not None
    assert step.target.robot_id == "robot456"
    assert len(step.then) == 1
    assert isinstance(step.then[0], MissionStepWait)


def test_mission_step_if_nested():
    """Test MissionStepIf with nested if steps."""
    step = MissionStepIf(
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "then": [
                    {
                        "if": {
                            "expression": "getValue('status') == 'ready'",
                            "then": [{"data": {"nested": True}}],
                        }
                    }
                ],
            }
        }
    )
    assert step.expression == "getValue('battery') > 50"
    assert len(step.then) == 1
    assert isinstance(step.then[0], MissionStepIf)
    nested_if = step.then[0]
    assert nested_if.expression == "getValue('status') == 'ready'"
    assert len(nested_if.then) == 1
    assert isinstance(nested_if.then[0], MissionStepSetData)


def test_mission_step_if_with_label_and_timeout():
    """Test MissionStepIf with label and timeout."""
    step = MissionStepIf(
        label="Check battery",
        timeoutSecs=30.0,
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "then": [{"data": {"key": "value"}}],
            }
        },
    )
    assert step.label == "Check battery"
    assert step.timeout_secs == 30.0
    assert step.expression == "getValue('battery') > 50"


def test_mission_step_if_accept_visitor():
    """Test MissionStepIf accept method for visitor pattern."""
    step = MissionStepIf(
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "then": [{"data": {"key": "value"}}],
            }
        }
    )

    class MockVisitor:
        def visit_if(self, step):
            return "visited_if"

    visitor = MockVisitor()
    result = step.accept(visitor)
    assert result == "visited_if"


def test_mission_definition_with_if_step():
    """Test MissionDefinition can contain MissionStepIf."""
    definition = MissionDefinition(
        label="Test mission",
        steps=[
            {
                "if": {
                    "expression": "getValue('battery') > 50",
                    "then": [{"data": {"key": "value"}}],
                    "else": [{"timeoutSecs": 5}],
                }
            }
        ],
    )
    assert len(definition.steps) == 1
    assert isinstance(definition.steps[0], MissionStepIf)
    assert definition.steps[0].expression == "getValue('battery') > 50"


def test_mission_step_if_multiple_steps_in_branches():
    """Test MissionStepIf with multiple steps in if and else branches."""
    step = MissionStepIf(
        **{
            "if": {
                "expression": "getValue('battery') > 50",
                "then": [
                    {"data": {"step": "if1"}},
                    {"data": {"step": "if2"}},
                    {"timeoutSecs": 10},
                ],
                "else": [
                    {"data": {"step": "else1"}},
                    {"timeoutSecs": 5},
                ],
            }
        }
    )
    assert len(step.then) == 3
    assert isinstance(step.then[0], MissionStepSetData)
    assert isinstance(step.then[1], MissionStepSetData)
    assert isinstance(step.then[2], MissionStepWait)
    assert len(step.else_) == 2
    assert isinstance(step.else_[0], MissionStepSetData)
    assert isinstance(step.else_[1], MissionStepWait)


def test_mission_step_if_validation():
    """Test that MissionStepIf validates required fields."""
    # Should fail without expression
    with pytest.raises(Exception):
        MissionStepIf(**{"if": {"then": [{"data": {"key": "value"}}]}})

    # Should fail without if branch
    with pytest.raises(Exception):
        MissionStepIf(**{"if": {"expression": "getValue('battery') > 50"}})

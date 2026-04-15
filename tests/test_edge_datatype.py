# SPDX-FileCopyrightText: 2024 InOrbit, Inc.
#
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from inorbit_edge_executor.datatypes import (
    Edge,
    EdgeCorridor,
    EdgeTrajectory,
    EdgeTrajectoryNurbsParameters,
    MissionDefinition,
    MissionStepPoseWaypoint,
)

# ---------------------------------------------------------------------------
# EdgeCorridor
# ---------------------------------------------------------------------------


def test_edge_corridor_basic():
    corridor = EdgeCorridor(width=2.0)
    assert corridor.width == 2.0


def test_edge_corridor_requires_width():
    with pytest.raises(ValidationError):
        EdgeCorridor()


# ---------------------------------------------------------------------------
# Edge — field presence and aliases
# ---------------------------------------------------------------------------


def test_edge_all_fields_from_js_resolver():
    """Full edge object as produced by the JS EdgeExecutor resolver."""
    edge = Edge(
        **{
            "edgeId": "e-AB",
            "startWaypointId": "A",
            "endWaypointId": "B",
            "bidirectional": True,
            "trajectory": {"type": "line"},
            "corridor": {"width": 2.0},
            "properties": {"edge": {"maxSpeed": "2"}},
        }
    )
    assert edge.edge_id == "e-AB"
    assert edge.start_waypoint_id == "A"
    assert edge.end_waypoint_id == "B"
    assert edge.bidirectional is True
    assert edge.trajectory.type == "line"
    assert edge.corridor.width == 2.0
    assert edge.properties == {"edge": {"maxSpeed": "2"}}


def test_edge_all_fields_optional():
    """Edge with no fields set is valid."""
    edge = Edge()
    assert edge.edge_id is None
    assert edge.start_waypoint_id is None
    assert edge.end_waypoint_id is None
    assert edge.bidirectional is None
    assert edge.trajectory is None
    assert edge.corridor is None
    assert edge.properties is None


def test_edge_partial_fields():
    edge = Edge(**{"edgeId": "e-XY", "bidirectional": False})
    assert edge.edge_id == "e-XY"
    assert edge.bidirectional is False
    assert edge.trajectory is None
    assert edge.corridor is None


# ---------------------------------------------------------------------------
# Edge — properties shape (Issue 2)
# ---------------------------------------------------------------------------


def test_edge_properties_nested_dict():
    """properties is Dict[str, Dict[str, Optional[str]]] — nested structure from annotation schema."""
    edge = Edge(
        **{
            "properties": {
                "edge": {"maxSpeed": "2", "someOtherProp": "value", "nullableProp": None}
            }
        }
    )
    assert edge.properties["edge"]["maxSpeed"] == "2"
    assert edge.properties["edge"]["someOtherProp"] == "value"
    assert edge.properties["edge"]["nullableProp"] is None


def test_edge_properties_multiple_namespaces():
    edge = Edge(
        **{
            "properties": {
                "edge": {"maxSpeed": "2"},
                "node": {"someFlag": "true"},
            }
        }
    )
    assert edge.properties["edge"]["maxSpeed"] == "2"
    assert edge.properties["node"]["someFlag"] == "true"


def test_edge_properties_flat_dict_is_invalid():
    """A flat Dict[str, str] was the old (broken) shape — it must now be rejected."""
    with pytest.raises(ValidationError):
        Edge(**{"properties": {"maxSpeed": "2"}})


# ---------------------------------------------------------------------------
# Edge — trajectory variants
# ---------------------------------------------------------------------------


def test_edge_trajectory_line():
    edge = Edge(**{"trajectory": {"type": "line"}})
    assert edge.trajectory.type == "line"
    assert edge.trajectory.parameters is None


def test_edge_trajectory_nurbs():
    edge = Edge(
        **{
            "trajectory": {
                "type": "nurbs",
                "parameters": {
                    "degree": 3,
                    "knotVector": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                    "controlPoints": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 1.0, "y": 0.5},
                        {"x": 2.0, "y": 0.0},
                    ],
                },
            }
        }
    )
    assert edge.trajectory.type == "nurbs"
    assert edge.trajectory.parameters.degree == 3
    assert len(edge.trajectory.parameters.knotVector) == 6
    assert len(edge.trajectory.parameters.controlPoints) == 3


def test_edge_trajectory_nurbs_missing_parameters_is_invalid():
    with pytest.raises(ValidationError):
        Edge(**{"trajectory": {"type": "nurbs"}})


def test_edge_trajectory_line_with_parameters_is_invalid():
    with pytest.raises(ValidationError):
        Edge(
            **{
                "trajectory": {
                    "type": "line",
                    "parameters": {
                        "degree": 3,
                        "knotVector": [0.0, 1.0],
                        "controlPoints": [{"x": 0.0, "y": 0.0}],
                    },
                }
            }
        )


# ---------------------------------------------------------------------------
# MissionStepPoseWaypoint with a full edge
# ---------------------------------------------------------------------------


def test_mission_step_pose_waypoint_with_full_edge():
    """End-to-end: step as received after JS EdgeExecutor resolution."""
    step = MissionStepPoseWaypoint(
        **{
            "waypoint": {
                "x": 1.0,
                "y": 2.0,
                "theta": 0.0,
                "frameId": "map",
                "waypointId": "A",
            },
            "edge": {
                "edgeId": "e-AB",
                "startWaypointId": "A",
                "endWaypointId": "B",
                "bidirectional": True,
                "trajectory": {"type": "line"},
                "corridor": {"width": 1.5},
                "properties": {"edge": {"maxSpeed": "1.5"}},
            },
        }
    )
    assert step.edge.edge_id == "e-AB"
    assert step.edge.start_waypoint_id == "A"
    assert step.edge.end_waypoint_id == "B"
    assert step.edge.bidirectional is True
    assert step.edge.trajectory.type == "line"
    assert step.edge.corridor.width == 1.5
    assert step.edge.properties["edge"]["maxSpeed"] == "1.5"


def test_mission_step_pose_waypoint_without_edge():
    step = MissionStepPoseWaypoint(
        **{
            "waypoint": {
                "x": 0.0,
                "y": 0.0,
                "theta": 0.0,
                "frameId": "map",
                "waypointId": "A",
            }
        }
    )
    assert step.edge is None


# ---------------------------------------------------------------------------
# MissionDefinition round-trip
# ---------------------------------------------------------------------------


def test_mission_definition_with_edge_step():
    definition = MissionDefinition(
        label="Test mission",
        steps=[
            {
                "waypoint": {
                    "x": 0.0,
                    "y": 0.0,
                    "theta": 0.0,
                    "frameId": "map",
                    "waypointId": "start",
                },
                "label": "Start",
            },
            {
                "waypoint": {
                    "x": 5.0,
                    "y": 5.0,
                    "theta": 1.57,
                    "frameId": "map",
                    "waypointId": "end",
                },
                "edge": {
                    "edgeId": "e-start-end",
                    "startWaypointId": "start",
                    "endWaypointId": "end",
                    "bidirectional": False,
                    "trajectory": {"type": "line"},
                    "corridor": {"width": 2.0},
                    "properties": {"edge": {"maxSpeed": "2"}},
                },
                "label": "End",
            },
        ],
    )
    assert len(definition.steps) == 2
    first, second = definition.steps
    assert isinstance(first, MissionStepPoseWaypoint)
    assert first.edge is None
    assert isinstance(second, MissionStepPoseWaypoint)
    assert second.edge.edge_id == "e-start-end"
    assert second.edge.corridor.width == 2.0


# ---------------------------------------------------------------------------
# Edge — serialization (model_dump by_alias)
# ---------------------------------------------------------------------------


def test_edge_model_dump_uses_aliases():
    """model_dump(by_alias=True) must produce JS-style camelCase keys so that
    Edge.model_validate() can round-trip through the serialized dict."""
    edge = Edge.model_validate(
        {
            "edgeId": "e-AB",
            "startWaypointId": "A",
            "endWaypointId": "B",
            "bidirectional": True,
            "trajectory": {"type": "line"},
            "corridor": {"width": 2.0},
            "properties": {"edge": {"maxSpeed": "2"}},
        }
    )

    dumped = edge.model_dump(by_alias=True)
    assert dumped["edgeId"] == "e-AB"
    assert dumped["startWaypointId"] == "A"
    assert dumped["endWaypointId"] == "B"
    assert dumped["corridor"]["width"] == 2.0

    # Round-trip: the serialized dict must be re-parseable
    restored = Edge.model_validate(dumped)
    assert restored.edge_id == "e-AB"
    assert restored.corridor.width == 2.0
    assert restored.properties["edge"]["maxSpeed"] == "2"

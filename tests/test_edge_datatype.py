# SPDX-FileCopyrightText: 2024 InOrbit, Inc.
#
# SPDX-License-Identifier: MIT

import pytest
from pydantic import ValidationError

from inorbit_edge_executor.datatypes import (
    Edge,
    EdgeCorridor,
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
# Edge — field presence
# ---------------------------------------------------------------------------


def test_edge_all_fields():
    edge = Edge(
        **{
            "routeId": "route-AB",
            "trajectory": {
                "degree": 3,
                "knotVector": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                "controlPoints": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 1.0, "y": 0.5},
                    {"x": 2.0, "y": 0.0},
                ],
            },
            "corridor": {"width": 2.0},
            "properties": {"routeSegment": {"maxSpeed": "2"}},
        }
    )
    assert edge.routeId == "route-AB"
    assert edge.trajectory.degree == 3
    assert edge.corridor.width == 2.0
    assert edge.properties == {"routeSegment": {"maxSpeed": "2"}}


def test_edge_optional_fields_default_to_none():
    edge = Edge(routeId="route-1")
    assert edge.trajectory is None
    assert edge.corridor is None
    assert edge.properties is None


def test_edge_partial_fields():
    edge = Edge(**{"routeId": "route-XY", "corridor": {"width": 1.5}})
    assert edge.routeId == "route-XY"
    assert edge.corridor.width == 1.5
    assert edge.trajectory is None
    assert edge.properties is None


def test_edge_requires_route_id():
    with pytest.raises(ValidationError):
        Edge()


# ---------------------------------------------------------------------------
# Edge — properties shape
# ---------------------------------------------------------------------------


def test_edge_properties_nested_dict():
    edge = Edge(
        **{
            "routeId": "route-1",
            "properties": {
                "routeSegment": {"maxSpeed": "2", "someOtherProp": "value", "nullableProp": None}
            },
        }
    )
    assert edge.properties["routeSegment"]["maxSpeed"] == "2"
    assert edge.properties["routeSegment"]["someOtherProp"] == "value"
    assert edge.properties["routeSegment"]["nullableProp"] is None


def test_edge_properties_flat_dict_is_invalid():
    with pytest.raises(ValidationError):
        Edge(**{"routeId": "route-1", "properties": {"maxSpeed": "2"}})


# ---------------------------------------------------------------------------
# Edge — trajectory
# ---------------------------------------------------------------------------


def test_edge_trajectory_null_means_straight_line():
    edge = Edge(**{"routeId": "route-1"})
    assert edge.trajectory is None


def test_edge_trajectory_nurbs():
    edge = Edge(
        **{
            "routeId": "route-1",
            "trajectory": {
                "degree": 3,
                "knotVector": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                "controlPoints": [
                    {"x": 0.0, "y": 0.0},
                    {"x": 1.0, "y": 0.5},
                    {"x": 2.0, "y": 0.0},
                ],
            },
        }
    )
    assert edge.trajectory.degree == 3
    assert len(edge.trajectory.knotVector) == 6
    assert len(edge.trajectory.controlPoints) == 3


# ---------------------------------------------------------------------------
# MissionStepPoseWaypoint with routeSegment
# ---------------------------------------------------------------------------


def test_mission_step_pose_waypoint_with_full_route_segment():
    step = MissionStepPoseWaypoint(
        **{
            "waypoint": {
                "x": 1.0,
                "y": 2.0,
                "theta": 0.0,
                "frameId": "map",
                "waypointId": "A",
            },
            "routeSegment": {
                "routeId": "route-AB",
                "trajectory": {
                    "degree": 3,
                    "knotVector": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                    "controlPoints": [
                        {"x": 0.0, "y": 0.0},
                        {"x": 1.0, "y": 0.5},
                        {"x": 2.0, "y": 0.0},
                    ],
                },
                "corridor": {"width": 1.5},
                "properties": {"routeSegment": {"maxSpeed": "1.5"}},
            },
        }
    )
    assert step.routeSegment.routeId == "route-AB"
    assert step.routeSegment.trajectory.degree == 3
    assert step.routeSegment.corridor.width == 1.5
    assert step.routeSegment.properties["routeSegment"]["maxSpeed"] == "1.5"


def test_mission_step_pose_waypoint_without_route_segment():
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
    assert step.routeSegment is None


# ---------------------------------------------------------------------------
# MissionDefinition round-trip
# ---------------------------------------------------------------------------


def test_mission_definition_with_route_segment_step():
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
                "routeSegment": {
                    "routeId": "route-start-end",
                    "trajectory": None,
                    "corridor": {"width": 2.0},
                    "properties": {"routeSegment": {"maxSpeed": "2"}},
                },
                "label": "End",
            },
        ],
    )
    assert len(definition.steps) == 2
    first, second = definition.steps
    assert isinstance(first, MissionStepPoseWaypoint)
    assert first.routeSegment is None
    assert isinstance(second, MissionStepPoseWaypoint)
    assert second.routeSegment.routeId == "route-start-end"
    assert second.routeSegment.corridor.width == 2.0


# ---------------------------------------------------------------------------
# Edge — serialization round-trip
# ---------------------------------------------------------------------------


def test_edge_model_dump_round_trip():
    edge = Edge.model_validate(
        {
            "routeId": "route-AB",
            "trajectory": {
                "degree": 3,
                "knotVector": [0.0, 0.0, 0.0, 1.0, 1.0, 1.0],
                "controlPoints": [{"x": 0.0, "y": 0.0}, {"x": 2.0, "y": 0.0}],
            },
            "corridor": {"width": 2.0},
            "properties": {"routeSegment": {"maxSpeed": "2"}},
        }
    )

    dumped = edge.model_dump()
    restored = Edge.model_validate(dumped)
    assert restored.routeId == "route-AB"
    assert restored.corridor.width == 2.0
    assert restored.trajectory.degree == 3

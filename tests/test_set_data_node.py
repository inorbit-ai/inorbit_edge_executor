import pytest
import httpx
from pytest_httpx import HTTPXMock
from inorbit_edge_executor.behavior_tree import (
    NODE_STATE_SUCCESS,
    SetDataNode,
    BehaviorTreeBuilderContext,
)
from inorbit_edge_executor.inorbit import RobotApiFactory, MissionTrackingAPI, InOrbitAPI
from inorbit_edge_executor.mission import Mission
from inorbit_edge_executor.datatypes import MissionDefinition, MissionStepSetData
from datetime import datetime


@pytest.mark.asyncio
async def test_set_data_node(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory, inorbit_api: InOrbitAPI
):
    robot = robot_api_factory.build("robot123")
    mission = Mission(
        id="mission123",
        robot_id="robot123",
        definition=MissionDefinition(
            steps=[MissionStepSetData(label="Set data", data={"test": "test"})]
        ),
        arguments={},
        tasks_list=[],
    )
    mt = MissionTrackingAPI(
        mission=mission,
        api=inorbit_api,
    )
    context = BehaviorTreeBuilderContext(
        mt=mt,
        mission=mission,
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )
    node = SetDataNode(context, {"test": "test"})
    httpx_mock.add_response(
        method="PUT",
        url="http://unittest/missions/mission123",
        json={},
    )
    await node.execute()
    assert (
        httpx_mock.get_request(method="PUT", url="http://unittest/missions/mission123") is not None
    )
    assert (
        httpx_mock.get_request(method="PUT", url="http://unittest/missions/mission123").content
        == b'{"data":{"test":"test"}}'
    )
    assert node.state == NODE_STATE_SUCCESS


@pytest.mark.asyncio
async def test_set_data_node_with_expression(
    httpx_mock: HTTPXMock, robot_api_factory: RobotApiFactory, inorbit_api: InOrbitAPI
):
    robot = robot_api_factory.build("robot123")
    mission = Mission(
        id="mission123",
        robot_id="robot123",
        definition=MissionDefinition(
            steps=[
                MissionStepSetData(
                    label="Set data",
                    data={
                        "test": "test",
                        "r2d2_speed": {
                            "expression": "getValue('speed')",
                            "target": {"robotId": "r2d2"},
                        },
                    },
                )
            ]
        ),
        arguments={},
        tasks_list=[],
    )
    mt = MissionTrackingAPI(
        mission=mission,
        api=inorbit_api,
    )
    context = BehaviorTreeBuilderContext(
        mt=mt,
        mission=mission,
        robot_api=robot,
        robot_api_factory=robot_api_factory,
    )
    node = SetDataNode(
        context,
        {
            "my_battery": {"expression": "getValue('battery')"},
            "r2d2_speed": {"expression": "getValue('speed')", "target": {"robotId": "r2d2"}},
        },
    )

    def custom_response(request: httpx.Request):
        if (
            request.method == "POST"
            and request.url.path == "/expressions/robot/robot123/eval"
            and request.content.decode("utf-8") == '{"expression":"getValue(\'battery\')"}'
        ):
            return httpx.Response(
                status_code=200,
                json={"success": True, "value": 25},
            )
        elif (
            request.method == "POST"
            and request.url.path == "/expressions/robot/r2d2/eval"
            and request.content.decode("utf-8") == '{"expression":"getValue(\'speed\')"}'
        ):
            return httpx.Response(
                status_code=200,
                json={"success": True, "value": 10},
            )
        return httpx.Response(status_code=400, json={"success": False, "message": "Invalid"})

    httpx_mock.add_callback(custom_response, is_reusable=True)
    await node.execute()
    assert node.state == NODE_STATE_SUCCESS
    request = httpx_mock.get_request(method="PUT", url="http://unittest/missions/mission123")
    assert request.content == b'{"data":{"my_battery":25,"r2d2_speed":10}}'

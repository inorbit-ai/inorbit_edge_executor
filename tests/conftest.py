import pytest
from inorbit_edge_executor.inorbit import InOrbitAPI, RobotApiFactory
from inorbit_edge_executor.behavior_tree import BehaviorTreeBuilderContext


@pytest.fixture
def inorbit_api():
    return InOrbitAPI(base_url="http://unittest", api_key="secret")


@pytest.fixture
def robot_api_factory(inorbit_api):
    return RobotApiFactory(inorbit_api)


@pytest.fixture
def empty_context(robot_api_factory: RobotApiFactory):
    return BehaviorTreeBuilderContext(
        robot_api_factory=robot_api_factory,
    )

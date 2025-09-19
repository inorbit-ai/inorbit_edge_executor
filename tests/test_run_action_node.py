import pytest
from unittest.mock import AsyncMock, Mock

from inorbit_edge_executor.behavior_tree import RunActionNode, BehaviorTreeBuilderContext
from inorbit_edge_executor.datatypes import Target
from inorbit_edge_executor.inorbit import RobotApi, RobotApiFactory


class TestRunActionNodeRetry:
    @pytest.fixture
    def mock_robot_api(self):
        """Mock RobotApi for testing"""
        mock_api = Mock(spec=RobotApi)
        mock_api.robot_id = "test_robot"
        mock_api.execute_action = AsyncMock()
        return mock_api

    @pytest.fixture
    def mock_mission_tracking(self):
        """Mock mission tracking for testing"""
        mock_mt = Mock()
        mock_mt.resolve_arguments = AsyncMock(return_value={"param": "value"})
        return mock_mt

    @pytest.fixture
    def context(self, mock_robot_api, mock_mission_tracking):
        """Create a test context with mocked dependencies"""
        context = BehaviorTreeBuilderContext()
        context.robot_api = mock_robot_api
        context.mt = mock_mission_tracking
        return context

    @pytest.mark.asyncio
    async def test_execute_action_success_first_try(self, context, mock_robot_api):
        """Test successful action execution on first attempt"""
        # Setup
        mock_robot_api.execute_action.return_value = {"status": "success"}

        node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=3,
            retry_wait_seconds=0.01,
        )

        # Execute
        await node._execute()

        # Verify
        mock_robot_api.execute_action.assert_called_once_with(
            "test_action", arguments={"param": "value"}
        )

    @pytest.mark.asyncio
    async def test_execute_action_success_after_retries(self, context, mock_robot_api):
        """Test successful action execution after some failures"""
        # Setup - fail first 2 attempts, succeed on 3rd
        mock_robot_api.execute_action.side_effect = [
            Exception("Network timeout"),
            Exception("Connection refused"),
            {"status": "success"},  # Success on third try
        ]

        node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=3,
            retry_wait_seconds=0.01,
        )

        # Execute
        await node._execute()

        # Verify
        assert mock_robot_api.execute_action.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_action_fail_all_retries(self, context, mock_robot_api):
        """Test action execution failure after exhausting all retries"""
        # Setup - all attempts fail
        test_exception = Exception("Persistent network error")
        mock_robot_api.execute_action.side_effect = test_exception

        node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=2,
            retry_wait_seconds=0.01,
        )

        # Execute and verify exception is raised
        with pytest.raises(Exception, match="Persistent network error"):
            await node._execute()

        # Verify all retry attempts were made (max_retries + 1 = 3 attempts)
        assert mock_robot_api.execute_action.call_count == 3

    @pytest.mark.asyncio
    async def test_execute_action_different_exception_types(self, context, mock_robot_api):
        """Test that different types of exceptions are handled consistently"""
        exceptions_to_test = [
            ValueError("Invalid parameter"),
            ConnectionError("Network unreachable"),
            TimeoutError("Request timeout"),
            RuntimeError("Service unavailable"),
        ]

        for exception in exceptions_to_test:
            # Reset mock
            mock_robot_api.execute_action.reset_mock()
            mock_robot_api.execute_action.side_effect = exception

            node = RunActionNode(
                context=context,
                action_id="test_action",
                arguments={"param": "value"},
                max_retries=1,
                retry_wait_seconds=0.01,
            )

            # Execute and verify exception is raised
            with pytest.raises(type(exception)):
                await node._execute()

            # Verify retries were attempted
            assert mock_robot_api.execute_action.call_count == 2

    @pytest.mark.asyncio
    async def test_execute_action_with_custom_max_retries(self, context, mock_robot_api):
        """Test action execution with different max_retries values"""
        test_cases = [0, 1, 5, 10]

        for max_retries in test_cases:
            # Reset mock
            mock_robot_api.execute_action.reset_mock()
            mock_robot_api.execute_action.side_effect = Exception("Always fail")

            node = RunActionNode(
                context=context,
                action_id="test_action",
                arguments={"param": "value"},
                max_retries=max_retries,
                retry_wait_seconds=0.01,
            )

            # Execute and verify exception is raised
            with pytest.raises(Exception):
                await node._execute()

            # Verify correct number of attempts (max_retries + 1)
            expected_attempts = max_retries + 1
            assert mock_robot_api.execute_action.call_count == expected_attempts

    @pytest.mark.asyncio
    async def test_retry_delay_timing(self, context, mock_robot_api):
        """Test that retry delays are working (approximate timing)"""
        # Setup
        mock_robot_api.execute_action.side_effect = [
            Exception("Fail 1"),
            Exception("Fail 2"),
            {"status": "success"},
        ]

        node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=2,
            retry_wait_seconds=0.01,
        )

        # Execute with timing
        import time

        start_time = time.time()
        await node._execute()
        end_time = time.time()

        # Should take at least 0.02 seconds (2 retries * 0.01 seconds each)
        # but allow some tolerance for test execution overhead
        assert end_time - start_time >= 0.015

    @pytest.mark.asyncio
    async def test_execute_action_with_target_robot(self, mock_mission_tracking):
        """Test action execution with a different target robot"""
        # Setup target robot
        target = Target(robotId="target_robot")

        # Create mock robot API factory
        mock_target_robot_api = Mock(spec=RobotApi)
        mock_target_robot_api.execute_action = AsyncMock(return_value={"status": "success"})

        mock_factory = Mock(spec=RobotApiFactory)
        mock_factory.build.return_value = mock_target_robot_api

        context = BehaviorTreeBuilderContext()
        context.robot_api_factory = mock_factory
        context.mt = mock_mission_tracking

        node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            target=target,
            max_retries=2,
            retry_wait_seconds=0.01,
        )

        # Execute
        await node._execute()

        # Verify
        mock_factory.build.assert_called_once_with("target_robot")
        mock_target_robot_api.execute_action.assert_called_once_with(
            "test_action", arguments={"param": "value"}
        )

    def test_dump_object_includes_max_retries(self, context):
        """Test that dump_object includes max_retries parameter"""
        node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=5,
            retry_wait_seconds=0.01,
        )

        dumped = node.dump_object()

        assert dumped["max_retries"] == 5
        assert dumped["retry_wait_seconds"] == 0.01
        assert dumped["action_id"] == "test_action"
        assert dumped["arguments"] == {"param": "value"}

    def test_from_object_creates_node_with_max_retries(self, context):
        """Test that from_object correctly handles max_retries parameter"""
        node = RunActionNode.from_object(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=7,
            retry_wait_seconds=0.01,
        )

        assert node.max_retries == 7
        assert node.retry_wait_seconds == 0.01
        assert node.action_id == "test_action"
        assert node.arguments == {"param": "value"}

    def test_from_object_defaults_max_retries(self, context):
        """Test that from_object uses default max_retries when not specified"""
        node = RunActionNode.from_object(
            context=context, action_id="test_action", arguments={"param": "value"}
        )

        assert node.max_retries == 3  # Default value
        assert node.retry_wait_seconds == 5.0  # Default value

    def test_serialization_round_trip(self, context):
        """Test that serialization and deserialization preserve max_retries"""
        original_node = RunActionNode(
            context=context,
            action_id="test_action",
            arguments={"param": "value"},
            max_retries=4,
            retry_wait_seconds=0.01,
            label="test_label",
        )

        # Serialize
        dumped = original_node.dump_object()

        # Remove type field that's used by the serialization system
        dumped_for_restore = dumped.copy()
        del dumped_for_restore["type"]

        # Deserialize
        restored_node = RunActionNode.from_object(context=context, **dumped_for_restore)

        # Verify all properties are preserved
        assert restored_node.max_retries == 4
        assert restored_node.retry_wait_seconds == 0.01
        assert restored_node.action_id == "test_action"
        assert restored_node.arguments == {"param": "value"}
        assert restored_node.label == "test_label"

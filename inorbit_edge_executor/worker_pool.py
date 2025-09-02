"""
worker_pool

Worker pool implementation. Implements a Pool of workers to be used for mission
execution.
"""

import asyncio

from .behavior_tree import (
    BehaviorTreeBuilderContext,
    TreeBuilder,
    DefaultTreeBuilder,
    build_tree_from_object,
)
from .datatypes import (
    MissionRuntimeOptions,
    MissionRuntimeSharedMemory,
    MissionWorkerState,
    MissionTrackingTypes,
)
from .db import WorkerPersistenceDB
from .exceptions import (
    InvalidMissionStateException,
    MissionNotFoundException,
    RobotBusyException,
    TranslationException,
)
from .inorbit import InOrbitAPI, MissionStatus, MissionTrackingAPI, RobotApiFactory
from .logger import setup_logger
from .mission import Mission
from .worker import Worker

logger = setup_logger(name="WorkerPool")


class WorkerPool:
    """
    Manages and keeps track of workers. It receives missions and executes them
    using Workers. It also persists workers' state and reloads them on restart.

    Different connectors may subclass this class and reimplement with their specifics:

     - create_builder_context(): Creating a subclass of BehaviorTreeBuilderContext
       if necessary, populated with any specific context needed by the connector
       (e.g. an API class).
       Reimplementing prepare_builder_context() is optional; it gets executed later
       after constructing the context.
     - deserialize_mission(): If the Mission class is different from the Mission one used
       by default in the base package, reimplement this. It should only call
       SomeMissionSubclass.model_validate() to deserialize.
     - translate_mission(): An optional step, where a Mission is translated from the
       version received from InOrbit to any other form, as required by the connector.
       Normally, only the definition part of the mission would be changed.
    """

    def __init__(
        self,
        api: InOrbitAPI,
        db: WorkerPersistenceDB,
        mt_type: MissionTrackingTypes = None,
        robot_session_config: dict = None,
        behavior_tree_builder: TreeBuilder = None,
    ):
        if not api:
            raise Exception("Missing InOrbitAPI for WorkerPool initialization")
        self._api = api
        self._db = db
        if mt_type == MissionTrackingTypes.DATASOURCE and not robot_session_config:
            raise Exception("Missing robot_session_config for Mission Tracking Datasource type.")
        self._mt_type: MissionTrackingTypes = mt_type
        self._robot_session_config = robot_session_config
        # Workers, by mission id. Protected by self._mutex
        self._workers = {}
        # No work can be received until this flag is True, set during start().
        self._running = False
        # Lock to protect workers pool state
        self._mutex = asyncio.Lock()
        self._behavior_tree_builder = (
            behavior_tree_builder if behavior_tree_builder else DefaultTreeBuilder()
        )

    async def start(self):
        """
        Starts the worker pool. Enables receiving work after this call.
        """
        if self._running:
            return
        self._running = True

        try:
            await self._db.delete_finished_missions()
        except Exception as e:
            logger.error(e)
        # Load state from DB: Retrieve unfinished missions and create workers for them
        serialized_workers = []
        try:
            serialized_workers = await self._db.fetch_all_missions(finished=False, paused=False)
        except Exception as e:
            logger.error("Error loading state from DB. Some missions may not resume", e)

        logger.info(f"Retrieved {len(serialized_workers)} mission workers to resume execution")
        for worker_state in serialized_workers:
            await self.execute_serialized_worker(worker_state)

    async def shutdown(self):
        """
        Stops the worker pool. It's actually not doing anything more than preventing new jobs
        to be submitted.
        """
        self._running = False

    async def notify(self, worker: Worker):
        """Notified when a worker changed its state. Persist it"""
        # TODO(herchu) batch these calls, marking workers as 'dirty': normally, many nodes
        # in the behavior tree are marked as changed (one ends, another starts); or also nodes
        # change and then the worker itself changes (marked as completed). We should not save
        # the object to DB multiple times in these cases.
        if self._running:
            await self.persist(worker)

    def deserialize_mission(self, serialized_mission):
        # Subclasses can change the mission class
        return Mission.model_validate(serialized_mission)

    def build_worker_from_serialized(self, serialized_worker) -> Worker:
        # Note that fields must match the format created by serialize()!
        # First get the fields from
        options = MissionRuntimeOptions.model_validate(serialized_worker.state["options"])
        mission = self.deserialize_mission(serialized_worker.state["mission"])
        shared_memory = MissionRuntimeSharedMemory.model_validate(
            serialized_worker.state["shared_memory"]
        )

        # Make a context for building trees
        context = self.create_builder_context()
        self.prepare_builder_context(context, mission)
        context.shared_memory = shared_memory
        context.options = options
        shared_memory.frozen = False
        tree = build_tree_from_object(context, serialized_worker.state["tree"])
        shared_memory.freeze()

        # Make a context for building trees
        worker = Worker(mission, options, shared_memory)
        worker.set_behavior_tree(tree)
        worker.set_finished(serialized_worker.state["finished"])
        # NOTE (Elvio): This validation was added for backward compatibility when the pause/resume
        # feature was added
        worker.set_paused(serialized_worker.state.get("paused", False))
        # Set the MissionTrackingAPI from the context if available
        worker.set_mt(context.mt)
        return worker

    async def execute_serialized_worker(self, worker_state: MissionWorkerState):
        """
        Executes a serialized worker.
        It creates the worker using FromSerialized() method and executes its behavior tree.
        """
        try:
            worker = self.build_worker_from_serialized(worker_state)
            logger.debug(f"Worker from serialized: {worker}")
            # If the worker was paused, resume it
            await worker.resume()
            # Worker is being executed, it should be tracked in memory
            self._workers[worker._mission.id] = worker
            worker.subscribe(self)
            logger.debug(f"Created worker {worker.id} from serialized version")
            # Start executing this mission. The behavior tree will resume from last
            # non-executed node
            asyncio.create_task(worker.execute())
        except Exception as e:
            logger.warning(
                f"Could not build worker {worker_state.mission_id} from serialized version. "
                f"It will NOT resume",
                e,
            )
            try:
                logger.warning(f"Removing mission {worker_state.mission_id}")
                await self._db.delete_mission(worker_state.mission_id)
            except Exception as ex:
                logger.warning(ex)

    def create_builder_context(self) -> BehaviorTreeBuilderContext:
        """
        Creates an empty context for building trees. Subclasses may reimplement and
        return a subclass of BehaviorTreeBuilderContext
        """
        return BehaviorTreeBuilderContext()

    def prepare_builder_context(self, context: BehaviorTreeBuilderContext, mission: Mission):
        """ """
        context.mission = mission
        context.error_context = dict()
        robot_api_factory = RobotApiFactory(self._api)
        context.robot_api_factory = robot_api_factory
        context.robot_api = robot_api_factory.build(mission.robot_id)

        if self._mt_type == MissionTrackingTypes.DATASOURCE:
            raise NotImplementedError("Mission tracking datasource is not supported")
        else:
            context.mt = MissionTrackingAPI(mission, self._api)

    def translate_mission(self, mission: Mission):
        """
        Performs any necessary translation from a mission (from its definition coming
        from InOrbit) to one that the current connector can execute.

        For example, connectors may merge two "visit waypoint" into one "navigate from
        waypoint A to waypoint B" step, if that's how the robot or fleet manager works.

        The resulting MissionDefinition can then include non-standard MissionSteps.

        By default it does nothing; simply returns the same mission.
        """
        return mission

    async def submit_work(
        self,
        mission: Mission,
        options: MissionRuntimeOptions,
        shared_memory: MissionRuntimeSharedMemory = None,
    ):
        if not self._running:
            raise Exception("WorkerPool is not started")

        mission_id = mission.id
        try:
            mission = self.translate_mission(mission)
        except Exception as e:
            logger.exception(e)
            raise TranslationException()

        if not shared_memory:
            shared_memory = MissionRuntimeSharedMemory()

        context = self.create_builder_context()
        self.prepare_builder_context(context, mission)
        context.shared_memory = shared_memory
        context.options = options

        # Create worker, not yet started (it can still be discarded)
        worker = Worker(mission, options, shared_memory)
        try:
            bt = self._behavior_tree_builder.build_tree_for_mission(context)
            worker.set_behavior_tree(bt)
        except Exception as e:
            logger.error(f"Error compiling mission tree: {e}", exc_info=True)
            return {"error": str(e)}

        shared_memory.freeze()
        async with self._mutex:
            current_mission = await self._db.fetch_robot_active_mission(mission.robot_id)
            logger.debug("Robot active mission: %s", current_mission)
            if current_mission is not None:
                raise RobotBusyException()
            self._workers[mission.id] = worker
            # Persist initial state
            await self.persist(worker)
        worker.subscribe(self)
        logger.info(f"Starting execution for mission {mission.id}.")
        asyncio.create_task(worker.execute())
        return {"id": mission_id}  # add status? "executing"

    async def persist(self, worker: Worker):
        try:
            await self._db.save_mission(worker.serialize())
            logger.debug(f"Mission {worker.id()} state persisted")
        except Exception as e:
            logger.error(f"Error persisting worker {worker.id()} state: {str(e)}")

    def abort_mission(self, mission_id: str) -> dict | bool:
        """
        Aborts running a mission. If there is no worker for the mission, it returns False.

        Args:
            mission_id (str): InOrbit mission ID to abort.

        Return:
            {"id": mission_id, "cancelled": True} if the mission was cancelled,
            {"id": mission_id} if not.
            False, if the mission was not found.
        """
        if mission_id in self._workers:
            ret = {"id": mission_id}
            ret["cancelled"] = self._workers[mission_id].cancel()
            return ret
        else:
            return False

    async def get_mission_status(self, mission_id) -> dict | None:
        """
        Returns a serialized representation of the status of a mission (of its worker). This uses
        the same serialization methods used for persisting mission states, which must fully
        represent the current status of a mission. It is used only for debugging.
        """
        async with self._mutex:
            if mission_id in self._workers:
                return self._workers[mission_id].dump_object()
            else:
                return None

    async def pause_mission(self, mission_id) -> None:
        """
        Pauses a running mission. If there's no worker for the mission it raises
        MissionNotFoundException(). If the mission is already paused it raises
        InvalidMissionStateException().
        """
        async with self._mutex:
            if mission_id in self._workers:
                await self._workers[mission_id].pause()
                del self._workers[mission_id]
            else:
                serialized_mission = await self._db.fetch_mission(mission_id=mission_id)
                if serialized_mission and serialized_mission.state["paused"]:
                    logger.warning(f"Mission {mission_id} is already paused.")
                    raise InvalidMissionStateException()
                elif not serialized_mission or serialized_mission.state["finished"]:
                    logger.warning(f"Mission {mission_id} not found or it's already finished")
                    raise MissionNotFoundException()

    async def resume_mission(self, mission_id) -> None:
        """
        Resumes a paused mission. Paused missions are retrieved from the db, they are serialized
        and they should not be running in a worker. If the mission is finished or not present in
        the db it raises a MissionNotFoundException(). If the mission is not paused it raises
        InvalidMissionStateException().
        """
        serialized_mission = await self._db.fetch_mission(mission_id=mission_id)
        if not serialized_mission or serialized_mission.state["finished"]:
            logger.warning(f"Mission {mission_id} not found or it's already finished.")
            raise MissionNotFoundException()
        if not serialized_mission.state["paused"]:
            logger.warning(f"Mission {mission_id} is not paused. It will not be resumed")
            raise InvalidMissionStateException()
        await self.execute_serialized_worker(serialized_mission)

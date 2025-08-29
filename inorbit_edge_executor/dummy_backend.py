# This module provides a minimal storage backend that only keeps track of busy robots
from typing import List

from .datatypes import MissionWorkerState
from .db import WorkerPersistenceDB
from .logger import setup_logger

logger = setup_logger(name="MissionExecutor")


class DummyDB(WorkerPersistenceDB):
    def __init__(self):
        self._busy_robots = dict()
        self._missions = dict()

    async def connect(self):
        pass

    async def shutdown(self):
        pass

    async def fetch_mission(self, mission_id) -> MissionWorkerState:
        return self._missions.get(mission_id)

    async def save_mission(self, mission: MissionWorkerState):
        self._missions[mission.mission_id] = mission
        if mission.finished:
            try:
                del self._busy_robots[mission.robot_id]
            except Exception:
                logger.error("error deleting mission", exc_info=True)
        else:
            self._busy_robots[mission.robot_id] = mission.mission_id

    async def fetch_all_missions(self, finished=None, paused=None) -> List[MissionWorkerState]:
        return list(self._missions.values())

    async def fetch_robot_active_mission(self, robot_id: str):
        """
        Returns the id of the mission being currently executed by a robot if any
        """
        return self._busy_robots.get(robot_id)

    async def delete_mission(self, mission_id: str):
        try:
            delete = [
                robot_id
                for robot_id in self._busy_robots
                if self._busy_robots[robot_id] == mission_id
            ]
            for robot_id in delete:
                del self._busy_robots[robot_id]
        except Exception:
            logger.error("error deleting missions", exc_info=True)
        try:
            del self._missions[mission_id]
        except Exception:
            logger.error("error deleting mission", exc_info=True)

    async def delete_finished_missions(self):
        finished_mission_ids = [
            mission_id for mission_id in self._missions if self._missions[mission_id].finished
        ]
        for mission_id in finished_mission_ids:
            del self._missions[mission_id]

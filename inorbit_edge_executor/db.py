from typing import List

from .datatypes import MissionWorkerState
from .logger import setup_logger

logger = setup_logger(name="MissionExecutor")

# The DB is a singleton, returned by get_db()
the_db = None


class WorkerPersistenceDB:
    """
    Superclass for DB wrappers. It defines a simple API for querying and storing worker states.
    """

    async def connect(self):
        pass

    async def shutdown(self):
        pass

    async def save_mission(self, mission: MissionWorkerState):
        raise Exception("Implemented by subclass")

    async def fetch_mission(self, mission_id) -> MissionWorkerState:
        raise Exception("Implemented by subclass")

    async def delete_mission(self, mission_id):
        raise Exception("Implemented by subclass")

    async def delete_finished_missions(self):
        raise Exception("Implemented by subclass")

    async def fetch_all_missions(self, finished, paused) -> List[MissionWorkerState]:
        raise Exception("Implemented by subclass")

    async def fetch_robot_active_mission(self, robot_id: str):
        raise Exception("Implemented by subclass")


async def get_db(db_path=None) -> WorkerPersistenceDB:
    """
    Factory for creating a DB from settings
    It reads the 'db' element from settings and creates a DB wrapper.
    Only implemented for sqlite3, in the format "sqlite:<filename>"
    """
    if db_path is None:
        raise Exception("db_path is None")
    global the_db
    if not the_db:
        filename = db_path
        if filename == "dummy":
            # Dummy storage allow us to run the service without SQLite
            # Note that this backend is really limited. The only functionality it implements is
            # related to tracking busy robots
            logger.warning("Using dummy storage backend")
            from .dummy_backend import DummyDB

            the_db = DummyDB()
            await the_db.connect()
        elif filename.startswith("sql"):
            from .sqlite_backend import SqliteDB

            the_db = SqliteDB(filename[7:])
            await the_db.connect()
        else:
            raise Exception("Invalid DB format/filename: " + filename)
    return the_db

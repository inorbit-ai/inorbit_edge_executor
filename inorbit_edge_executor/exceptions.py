class TranslationException(Exception):
    """
    TranslationException is raised when an InOrbit mission can't be translated
    into the robot/fleet manager specific mission.
    """

    pass


class RobotBusyException(Exception):
    """
    RobotBusyException is raised when trying to create a new worker for a robot that is already
    executing a mission
    """

    pass


class TaskPausedException(BaseException):
    """
    TaskPausedException is raised when a worker is executing a behavior tree and it
    is intenionally paused in the middle of its execution.
    """

    pass


class InvalidMissionStateException(Exception):
    """
    InvalidMissionStateException is raised when trying to pause an already paused mission
    or resume a running mission"
    """

    pass


class MissionNotFoundException(Exception):
    """
    MissionNotFoundException is raised when a mission is not found in the database or in the
    workers assigned to the worker pool.
    """

    pass

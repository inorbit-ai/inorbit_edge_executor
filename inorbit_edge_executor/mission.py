# Mission execution logic
from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import model_validator
from typing_extensions import Self

from .datatypes import (
    StepsList, MissionStepSetData, MissionStepPoseWaypoint, MissionStepRunAction, MissionStepWait, MissionStepWaitUntil, MissionStepIf,
    MissionTask, MissionStep, MissionDefinition
)

class MissionTasksExtractor:
    """
    Helper class that visits mission steps and collects the tasks to be executed.
    """
    def __init__(self):
        self._tasks_list: List[MissionTask] = []

    def extract_tasks(self, steps: StepsList) -> List[MissionTask]:
        for step in steps:
            step.accept(self)
        return self._tasks_list

    def collect_step(self, step: MissionStep):
        if step.complete_task is not None:
            self._tasks_list.append(MissionTask(taskId=step.complete_task, label=step.complete_task))

    def visit_set_data(self, step: MissionStepSetData):
        self.collect_step(step)

    def visit_pose_waypoint(self, step: MissionStepPoseWaypoint):
        self.collect_step(step)

    def visit_run_action(self, step: MissionStepRunAction):
        self.collect_step(step)

    def visit_wait(self, step: MissionStepWait):
        self.collect_step(step)

    def visit_wait_until(self, step: MissionStepWaitUntil):
        self.collect_step(step)

    def visit_if(self, step: MissionStepIf):
        self.collect_step(step)
        self.extract_tasks(step.then)
        if step.else_ is not None:
            self.extract_tasks(step.else_)


class Mission(BaseModel):
    """
    Represents a (parsed) mission. It includes the definition, the runtime arguments and tasks.
    The object is serializable
    """

    id: str
    robot_id: str
    definition: MissionDefinition
    arguments: Union[Dict[str, Any], None] = Field(default=None)
    tasks_list: List[MissionTask] = Field(default=None)  # Derived from 'definition'
    model_config = ConfigDict(extra="forbid")

    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)  # Let Pydantic initialize fields from constructor args
        if not self.tasks_list:  # if not coming from a serialized version
            # TODO make another public constructor instead of this hack
            self.tasks_list = self._build_tasks(self.definition)
        pass

    def _build_tasks(self, mission_definition: MissionDefinition) -> List[MissionTask]:
        extractor = MissionTasksExtractor()
        return extractor.extract_tasks(mission_definition.steps)

    def find_task(self, task_id):
        return next((task for task in self.tasks_list if task.task_id == task_id), None)

    def mark_task_completed(self, task_id):
        # task = self._tasks.get(task_id)
        task = self.find_task(task_id)
        if task is None:
            return
        task.completed = True
        task.in_progress = False

    def mark_task_in_progress(self, task_id):
        # task = self._tasks.get(task_id)
        task = self.find_task(task_id)
        if task is None:
            return
        task.in_progress = True

    @model_validator(mode="after")
    def validate(self) -> Self:
        # TO be overloaded by the child classes.
        return self

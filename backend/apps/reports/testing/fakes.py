"""In-memory fake of the reports facade, for tests of the dashboard home page.

reports = InMemoryReportsFacade()
reports.figures[Actor(30, "supervisor")] = HomeFiguresDTO(approvals_waiting=4)
"""

from apps.core.application.dtos import Actor
from apps.reports.application.dtos import HomeFiguresDTO


class InMemoryReportsFacade:
    def __init__(self) -> None:
        self.figures: dict[Actor, HomeFiguresDTO] = {}

    def home_figures(self, actor: Actor) -> HomeFiguresDTO:
        return self.figures.get(actor, HomeFiguresDTO())

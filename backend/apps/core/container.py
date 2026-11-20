"""Builds core's adapters. Other modules' containers call these to get the shared ports."""

from .application.ports import AuditLogger, Clock, FileStorage, UnitOfWork
from .infrastructure.audit import OrmAuditLogger
from .infrastructure.clock import SystemClock
from .infrastructure.storage import DjangoFileStorage
from .infrastructure.unit_of_work import DjangoUnitOfWork


def clock() -> Clock:
    return SystemClock()


def audit_logger() -> AuditLogger:
    return OrmAuditLogger()


def file_storage() -> FileStorage:
    return DjangoFileStorage()


def unit_of_work() -> UnitOfWork:
    """A new unit of work for each service call; it is not reusable across threads."""
    return DjangoUnitOfWork()

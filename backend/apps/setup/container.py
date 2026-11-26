"""Builds the setup services with their real adapters (design section 5)."""

from apps.core import container as core

from .application.facade import SetupFacade, SetupFacadeService
from .application.queries import GetLookups, GetLookupsVersion, ListClinics
from .application.services import (
    AddChairs,
    Reorder,
    SaveRecord,
    SeedDefaults,
    SetChairStatus,
    SetRecordActive,
    UpdateSettings,
)
from .infrastructure.repositories import (
    OrmChairRepository,
    OrmClinicRepository,
    OrmLookupRepository,
    OrmRecordRepository,
    OrmSettingRepository,
    OrmTermRepository,
)
from .infrastructure.seed import JsonSeedSource


def facade() -> SetupFacade:
    """What other modules' containers pass to their services as the setup port."""
    return SetupFacadeService(
        terms=OrmTermRepository(),
        clinics=OrmClinicRepository(),
        chairs=OrmChairRepository(),
        lookups=OrmLookupRepository(),
        settings=OrmSettingRepository(),
        set_chair_status=set_chair_status(),
    )


def save_record() -> SaveRecord:
    return SaveRecord(
        OrmRecordRepository(),
        OrmTermRepository(),
        OrmSettingRepository(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def set_record_active() -> SetRecordActive:
    return SetRecordActive(
        OrmRecordRepository(), OrmSettingRepository(), core.audit_logger(), core.unit_of_work()
    )


def reorder() -> Reorder:
    return Reorder(
        OrmRecordRepository(),
        OrmTermRepository(),
        OrmSettingRepository(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def add_chairs() -> AddChairs:
    return AddChairs(
        OrmRecordRepository(),
        OrmChairRepository(),
        OrmTermRepository(),
        OrmSettingRepository(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def set_chair_status() -> SetChairStatus:
    return SetChairStatus(
        OrmChairRepository(), core.clock(), core.audit_logger(), core.unit_of_work()
    )


def update_settings() -> UpdateSettings:
    return UpdateSettings(OrmSettingRepository(), core.audit_logger(), core.unit_of_work())


def seed_defaults() -> SeedDefaults:
    return SeedDefaults(
        OrmRecordRepository(),
        OrmTermRepository(),
        OrmSettingRepository(),
        JsonSeedSource(),
        core.audit_logger(),
        core.unit_of_work(),
    )


def get_lookups() -> GetLookups:
    return GetLookups(OrmLookupRepository(), OrmSettingRepository())


def get_lookups_version() -> GetLookupsVersion:
    return GetLookupsVersion(OrmSettingRepository())


def list_clinics() -> ListClinics:
    return ListClinics(OrmClinicRepository(), OrmChairRepository())

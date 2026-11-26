"""Setup reads for the API. The setup lists are the same for every role, so no scope filter
applies (design section 8)."""

from collections.abc import Sequence
from dataclasses import replace

from apps.setup.domain.settings import SETTINGS

from .dtos import ClinicChairsDTO, ClinicDTO, ClinicType, LookupsDTO
from .ports import ChairRepository, ClinicRepository, LookupRepository, SettingRepository


class GetLookupsVersion:
    """The version alone, so ``GET /lookups/`` can answer 304 without reading the lists."""

    def __init__(self, settings: SettingRepository) -> None:
        self._settings = settings

    def execute(self) -> int:
        return self._settings.lookups_version()


class GetLookups:
    """``GET /lookups/``: every lookup list in one call, with the version and the settings the
    app needs."""

    def __init__(self, lookups: LookupRepository, settings: SettingRepository) -> None:
        self._lookups = lookups
        self._settings = settings

    def execute(self) -> LookupsDTO:
        stored = self._settings.all()
        return replace(
            self._lookups.lookup_lists(),
            version=self._settings.lookups_version(),
            settings={s.key: stored.get(s.key) for s in SETTINGS if s.in_lookups},
        )


class ListClinics:
    """``GET /clinics/``: active clinics by number, optionally of one type."""

    def __init__(self, clinics: ClinicRepository, chairs: ChairRepository) -> None:
        self._clinics = clinics
        self._chairs = chairs

    def execute(self, *, type: ClinicType | None = None) -> Sequence[ClinicDTO]:
        return self._clinics.list(type=type)

    def with_chairs(self, *, type: ClinicType | None = None) -> Sequence[ClinicChairsDTO]:
        """``?with=chair_status``: each clinic with its active chairs and their status."""
        clinics = self._clinics.list(type=type)
        chairs = self._chairs.list_for_clinic([c.id for c in clinics], in_service_only=False)
        return [
            ClinicChairsDTO(clinic, tuple(ch for ch in chairs if ch.clinic_id == clinic.id))
            for clinic in clinics
        ]

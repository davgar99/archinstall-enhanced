from pytest import MonkeyPatch

from archinstall.lib.installer import Installer


def test_service_verification_does_not_query_removed_reflector_service(monkeypatch: MonkeyPatch) -> None:
	installer = object.__new__(Installer)
	queried_services: list[str] = []

	def service_state(service: str) -> str:
		queried_services.append(service)
		return 'dead'

	monkeypatch.setattr(installer, '_service_state', service_state)
	installer._verify_service_stop(skip_ntp=True, skip_wkd=True)

	assert queried_services == []


def test_sanity_check_keeps_offline_argument_compatibility(monkeypatch: MonkeyPatch) -> None:
	installer = object.__new__(Installer)
	verification_calls: list[tuple[bool, bool]] = []

	def verify(skip_ntp: bool, skip_wkd: bool) -> None:
		verification_calls.append((skip_ntp, skip_wkd))

	monkeypatch.setattr(installer, '_verify_service_stop', verify)
	installer.sanity_check(offline=True, skip_ntp=True, skip_wkd=False)

	assert verification_calls == [(True, False)]

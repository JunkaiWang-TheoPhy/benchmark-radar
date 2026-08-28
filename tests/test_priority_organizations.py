from pathlib import Path

import pytest
import yaml

from benchmark_radar.priority_organizations import (
    PriorityOrganizationRegistryError,
    load_priority_github_organizations,
)


def _write_registry(path: Path, organizations: list[dict]) -> Path:
    path.write_text(
        yaml.safe_dump({"schema_version": 1, "organizations": organizations}, sort_keys=False),
        encoding="utf-8",
    )
    return path


def _organizations(count: int = 300) -> list[dict]:
    return [
        {"login": f"ai-lab-{index}", "tier": "priority", "display_name": f"AI Lab {index}"}
        for index in range(count)
    ]


def test_priority_organization_registry_loads_300_public_logins(tmp_path):
    registry = _write_registry(tmp_path / "organizations.yml", _organizations())

    loaded = load_priority_github_organizations(registry)

    assert len(loaded) == 300
    assert loaded[0] == {
        "login": "ai-lab-0",
        "tier": "priority",
        "display_name": "AI Lab 0",
    }


def test_priority_organization_registry_rejects_insufficient_entries(tmp_path):
    registry = _write_registry(tmp_path / "organizations.yml", _organizations(299))

    with pytest.raises(PriorityOrganizationRegistryError, match="at least 300"):
        load_priority_github_organizations(registry)


def test_priority_organization_registry_rejects_duplicate_or_invalid_tier(tmp_path):
    entries = _organizations()
    entries[1]["login"] = entries[0]["login"].upper()
    registry = _write_registry(tmp_path / "duplicate.yml", entries)

    with pytest.raises(PriorityOrganizationRegistryError, match="Duplicate organization"):
        load_priority_github_organizations(registry)

    entries = _organizations()
    entries[0]["tier"] = "unknown"
    registry = _write_registry(tmp_path / "tier.yml", entries)

    with pytest.raises(PriorityOrganizationRegistryError, match="invalid tier"):
        load_priority_github_organizations(registry)

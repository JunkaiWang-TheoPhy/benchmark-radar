"""Validated registry of public GitHub organizations used for discovery priority."""

from __future__ import annotations

from pathlib import Path

import yaml


class PriorityOrganizationRegistryError(ValueError):
    """Raised when the reviewed GitHub-organization registry is malformed."""


VALID_TIERS = {"priority", "standard", "probation"}


def load_priority_github_organizations(path: str | Path) -> list[dict[str, str]]:
    """Load a reviewed registry without making reputation part of evidence scoring.

    The caller only receives the small execution-time surface. Rich collection
    evidence remains in YAML for reviewers and is deliberately not copied into
    every daily snapshot.
    """
    registry_path = Path(path)
    try:
        payload = yaml.safe_load(registry_path.read_text(encoding="utf-8"))
    except OSError as error:
        raise PriorityOrganizationRegistryError(
            f"Cannot read priority GitHub organization registry: {registry_path}"
        ) from error
    if not isinstance(payload, dict) or payload.get("schema_version") != 1:
        raise PriorityOrganizationRegistryError(
            "Priority GitHub organization registry must use schema_version 1"
        )
    rows = payload.get("organizations")
    if not isinstance(rows, list):
        raise PriorityOrganizationRegistryError(
            "Priority GitHub organization registry organizations must be an array"
        )

    normalized: list[dict[str, str]] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise PriorityOrganizationRegistryError(f"Organization #{index} must be an object")
        login = str(row.get("login") or "").strip()
        tier = str(row.get("tier") or "").strip().casefold()
        display_name = str(row.get("display_name") or login).strip()
        if not login or not all(character.isalnum() or character == "-" for character in login):
            raise PriorityOrganizationRegistryError(
                f"Organization #{index} has an invalid GitHub login"
            )
        if tier not in VALID_TIERS:
            raise PriorityOrganizationRegistryError(
                f"Organization {login} has an invalid tier {tier!r}"
            )
        if login.casefold() in seen:
            raise PriorityOrganizationRegistryError(f"Duplicate organization login: {login}")
        seen.add(login.casefold())
        normalized.append({"login": login, "tier": tier, "display_name": display_name})

    if len(normalized) < 300:
        raise PriorityOrganizationRegistryError(
            "Priority GitHub organization registry needs at least 300 organizations, "
            f"got {len(normalized)}"
        )
    return normalized

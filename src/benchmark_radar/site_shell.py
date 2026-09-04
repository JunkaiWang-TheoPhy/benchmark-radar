"""Shared HTML escaping and schema helpers for generated app pages."""

from __future__ import annotations

import html
import json
from collections.abc import Iterable
from typing import Any

from .feed import SITE_URL


def esc(value: Any) -> str:
    return html.escape(str(value), quote=True)


def json_ld(payload: dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True).replace("</", "<\\/")


def breadcrumb_schema(*items: tuple[str, str], canonical: str) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "@id": f"{canonical}#breadcrumb",
        "itemListElement": [
            {
                "@type": "ListItem",
                "position": position,
                "name": name,
                "item": url,
            }
            for position, (name, url) in enumerate(items, start=1)
        ],
    }


def webpage_schema(
    *, title: str, description: str, canonical: str, languages: Iterable[str] = ("en",)
) -> dict[str, Any]:
    return {
        "@context": "https://schema.org",
        "@type": "WebPage",
        "@id": canonical,
        "name": title,
        "url": canonical,
        "description": description,
        "inLanguage": list(languages),
        "isPartOf": {"@id": f"{SITE_URL}/#website"},
    }

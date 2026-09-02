"""Single source of truth for the project's self-citation (issue #483).

The APA text mirrors ``CITATION.cff``'s ``preferred-citation`` block and the
copy blocks on https://benchmark-radar.org/#cite. The version is read from
the package metadata so a release bumps the citation without a separate edit;
the year and DOI are stable because the technical report is deposited once.
"""

from __future__ import annotations

from . import __version__

PUBLICATION_YEAR = "2026"
DOI = "10.5281/zenodo.22167102"
CITE_URL = "https://benchmark-radar.org/#cite"


def apa_citation() -> str:
    return (
        f"Wu, K. ({PUBLICATION_YEAR}). Benchmark Radar v{__version__}: Technical Report "
        f"(Version {__version__}). https://doi.org/{DOI}"
    )


def cite_reminder() -> str:
    """Footer printed when a CLI command finishes (issue #483)."""
    return (
        "\n"
        "If Benchmark Radar helped your work, please cite it:\n"
        f"  {apa_citation()}\n"
        f"  More citation formats: {CITE_URL}"
    )

from pathlib import Path

import pytest

SITE = Path(__file__).resolve().parents[1] / "site"

# The shell plus the two scripts the view-page generator parses: per-view SEO
# strings out of app.js, category colors out of glyphs.js. It reads them from
# the site it is building so a generated page and the script it loads can never
# disagree about a title or a swatch.
SHELL_FILES = ("index.html", "assets/app.js", "assets/glyphs.js")


@pytest.fixture
def site_shell():
    """Put the real dashboard shell where a full site build expects it.

    The pages at /leaderboard/, /trends/ and /explore/ are copies of this one
    document with a different view opened and its rows seeded, so any build
    that writes them has to read it first. Stubs would not carry the markers
    the generator substitutes into, and the generator refuses to guess.
    """

    def install(site_dir: Path) -> Path:
        for name in SHELL_FILES:
            target = site_dir / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes((SITE / name).read_bytes())
        return site_dir / "index.html"

    return install

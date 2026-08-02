from pathlib import Path

import pytest
import yaml

from benchmark_radar.model_cards import (
    DEFAULT_REGISTRY_PATH,
    ModelCardRegistryError,
    adoption_rank,
    build_adoption_rank,
    load_registry,
)


def write_registry(tmp_path: Path, document: dict) -> Path:
    path = tmp_path / "model_cards.yml"
    path.write_text(yaml.safe_dump(document, sort_keys=False), encoding="utf-8")
    return path


def minimal_registry(**overrides) -> dict:
    document = {
        "schema_version": 1,
        "benchmarks": [
            {
                "id": "alpha",
                "name": "Alpha",
                "domain": "math",
                "url": "https://example.com/a",
                "caveat": "Alpha caveat.",
            },
            {
                "id": "beta",
                "name": "Beta",
                "domain": "coding",
                "url": "https://example.com/b",
                "caveat": "Beta caveat.",
            },
        ],
        "model_cards": [
            {
                "id": "org_one_card",
                "organization": "Org One",
                "model": "One",
                "document_type": "model_card",
                "published": "2025-01-01",
                "url": "https://example.com/one",
                "benchmarks": ["alpha", "beta"],
            },
            {
                "id": "org_two_card",
                "organization": "Org Two",
                "model": "Two",
                "document_type": "system_card",
                "published": "2025-02-01",
                "url": "https://example.com/two",
                "benchmarks": ["alpha"],
            },
        ],
    }
    document.update(overrides)
    return document


def test_shipped_registry_loads_and_ranks():
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    assert board["model_card_count"] > 0
    assert board["benchmark_count"] > 0
    # Every organization named in issue #83 is represented, so the ranking is
    # not an artifact of one vendor's reporting habits.
    assert {
        "OpenAI",
        "Anthropic",
        "Google DeepMind",
        "Meta",
        "Qwen",
        "DeepSeek",
        "Mistral",
        "xAI",
    } <= set(board["organizations"])


def test_rank_is_total_and_deterministic():
    board = adoption_rank(load_registry(DEFAULT_REGISTRY_PATH))
    entries = board["entries"]

    assert [entry["rank"] for entry in entries] == list(range(1, len(entries) + 1))
    # Cards descending, then organizations descending, then name ascending. No
    # entry may outrank one with a strictly higher card count.
    keys = [
        (-entry["card_count"], -entry["organization_count"], entry["name"]) for entry in entries
    ]
    assert keys == sorted(keys)


def test_repeated_configurations_do_not_inflate_a_single_card(tmp_path):
    # Issue #83's central caveat: one card reporting AIME at pass@1 and
    # consensus@64 is still one card choosing to report AIME. If duplicates
    # counted, a verbose appendix would outvote a whole other vendor.
    document = minimal_registry()
    document["model_cards"][0]["benchmarks"] = ["alpha", "alpha", "alpha", "beta"]
    board = adoption_rank(load_registry(write_registry(tmp_path, document)))

    alpha = next(entry for entry in board["entries"] if entry["benchmark_id"] == "alpha")
    assert alpha["card_count"] == 2
    assert alpha["organization_count"] == 2
    assert len(alpha["adopters"]) == 2


def test_organization_count_distinguishes_a_standard_from_a_house_style(tmp_path):
    document = minimal_registry()
    document["model_cards"].append(
        {
            "id": "org_one_second_card",
            "organization": "Org One",
            "model": "One Plus",
            "document_type": "model_card",
            "published": "2025-03-01",
            "url": "https://example.com/one-plus",
            "benchmarks": ["beta"],
        }
    )
    board = adoption_rank(load_registry(write_registry(tmp_path, document)))

    alpha = next(entry for entry in board["entries"] if entry["benchmark_id"] == "alpha")
    beta = next(entry for entry in board["entries"] if entry["benchmark_id"] == "beta")

    # Both are reported by two cards, but alpha crosses two organizations and
    # beta is one vendor twice. That is precisely the tie the second column
    # exists to break, so alpha must outrank beta.
    assert alpha["card_count"] == beta["card_count"] == 2
    assert alpha["organization_count"] == 2
    assert beta["organization_count"] == 1
    assert alpha["rank"] < beta["rank"]


def test_adoption_share_is_relative_to_the_document_count(tmp_path):
    board = adoption_rank(load_registry(write_registry(tmp_path, minimal_registry())))

    alpha = next(entry for entry in board["entries"] if entry["benchmark_id"] == "alpha")
    beta = next(entry for entry in board["entries"] if entry["benchmark_id"] == "beta")
    assert alpha["adoption_share"] == 1.0
    assert beta["adoption_share"] == 0.5


def test_unknown_benchmark_reference_is_rejected(tmp_path):
    # A typo must not silently mint a benchmark with an adoption count of one,
    # which is indistinguishable from a real benchmark nobody adopted.
    document = minimal_registry()
    document["model_cards"][0]["benchmarks"] = ["alpha", "gamma"]
    path = write_registry(tmp_path, document)

    with pytest.raises(ModelCardRegistryError, match="unknown benchmarks: gamma"):
        load_registry(path)


def test_duplicate_ids_are_rejected(tmp_path):
    document = minimal_registry()
    document["benchmarks"].append(
        {"id": "alpha", "name": "Alpha again", "domain": "math", "caveat": "Dup."}
    )
    with pytest.raises(ModelCardRegistryError, match="duplicate benchmark id"):
        load_registry(write_registry(tmp_path, document))

    document = minimal_registry()
    document["model_cards"].append(dict(document["model_cards"][0]))
    with pytest.raises(ModelCardRegistryError, match="duplicate model card id"):
        load_registry(write_registry(tmp_path, document))


def test_non_http_card_url_is_rejected(tmp_path):
    document = minimal_registry()
    document["model_cards"][0]["url"] = "file:///etc/passwd"
    with pytest.raises(ModelCardRegistryError, match="url must be HTTP"):
        load_registry(write_registry(tmp_path, document))


def test_unsupported_schema_version_is_rejected(tmp_path):
    with pytest.raises(ModelCardRegistryError, match="unsupported schema_version"):
        load_registry(write_registry(tmp_path, minimal_registry(schema_version=99)))


def test_missing_registry_file_is_reported(tmp_path):
    with pytest.raises(ModelCardRegistryError, match="registry file not found"):
        load_registry(tmp_path / "absent.yml")


def test_every_benchmark_states_what_it_does_not_settle():
    registry = load_registry(DEFAULT_REGISTRY_PATH)

    # A ranking that puts a saturated or contaminated benchmark near the top
    # without saying so invites the exact misreading issue #83 warns about, so
    # the caveat is required data rather than optional prose.
    missing = [
        benchmark["id"]
        for benchmark in registry["benchmarks"]
        if not str(benchmark.get("caveat") or "").strip()
    ]
    assert not missing


def test_a_benchmark_without_a_caveat_is_rejected(tmp_path):
    # Enforced for any registry, not spot-checked on the shipped one: a custom
    # --model-cards file could otherwise publish rows with no qualification at
    # all, which is precisely the misreading the caveat exists to prevent.
    document = minimal_registry()
    document["benchmarks"][0].pop("caveat")
    with pytest.raises(ModelCardRegistryError, match="missing fields: caveat"):
        load_registry(write_registry(tmp_path, document))

    document = minimal_registry()
    document["benchmarks"][0]["caveat"] = "   "
    with pytest.raises(ModelCardRegistryError, match="missing fields: caveat"):
        load_registry(write_registry(tmp_path, document))


def test_measures_statement_travels_with_the_data():
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    # Any consumer of radar.json inherits the disclaimer instead of inferring
    # the ranking's meaning from its column headers.
    assert "not benchmark quality" in board["measures"]


def test_adoption_rank_links_are_exact_inverses():
    """The registry is one edge set published in two directions.

    `entries[].adopters` answers "who reports this benchmark" and
    `model_cards[].reported_benchmarks` answers "what does this card report".
    Both are derived from the same validated `card["benchmarks"]`, and this test
    is what makes that a guarantee rather than a coincidence: if either
    projection is ever filtered, truncated or sorted into a lossy shape, the two
    edge sets diverge and a reader auditing a card against the table above would
    be shown a benchmark list that does not explain the counts.
    """
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    forward = {
        (entry["benchmark_id"], adopter["model_card_id"])
        for entry in board["entries"]
        for adopter in entry["adopters"]
    }
    reverse = {
        (benchmark["benchmark_id"], card["model_card_id"])
        for card in board["model_cards"]
        for benchmark in card["reported_benchmarks"]
    }

    assert forward == reverse
    assert forward, "the shipped registry must publish at least one adoption edge"
    # Every card's own count agrees with the number of edges it contributes.
    # `reported_benchmarks` is ordered by domain for display, so compare as sets
    # against the id list rather than positionally.
    for card in board["model_cards"]:
        assert card["benchmark_count"] == len(card["reported_benchmarks"])
        assert {benchmark["benchmark_id"] for benchmark in card["reported_benchmarks"]} == set(
            card["benchmarks"]
        )


def test_expanded_card_carries_enough_to_audit_against_the_source():
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    # A reader opening a card checks our list against the vendor's own document.
    # That requires the source URL, when a human last read it, and for each
    # benchmark the name and caveat -- not just an id they would have to resolve
    # against another table by hand.
    for card in board["model_cards"]:
        assert card["url"].startswith("https://")
        for benchmark in card["reported_benchmarks"]:
            assert benchmark["name"]
            assert benchmark["domain"]
            assert benchmark["caveat"]


def test_benchmark_release_dates_are_published_and_validated(tmp_path):
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    # Filterable in the dashboard, so it has to survive into the published data.
    assert any(entry["released"] for entry in board["entries"])
    for entry in board["entries"]:
        if entry["released"]:
            assert len(entry["released"]) == 10

    # Validated on the same terms as a card's dates: this value reaches the same
    # browser formatter, and an unparseable one would take every view down.
    document = minimal_registry()
    document["benchmarks"][0]["released"] = "March 2025"
    with pytest.raises(ModelCardRegistryError, match="must be an ISO date"):
        load_registry(write_registry(tmp_path, document))

    document = minimal_registry()
    document["benchmarks"][0]["released"] = "2025-02-30"
    with pytest.raises(ModelCardRegistryError, match="not a real calendar date"):
        load_registry(write_registry(tmp_path, document))


def test_a_card_cannot_report_a_benchmark_that_did_not_exist_yet(tmp_path):
    """A benchmark released after a card cannot have been reported by it.

    Every date involved is individually well-formed, so no other check catches
    the contradiction, and the bad edge is invisible in the ranking: it just
    quietly adds one adoption. The first draft of the 2026 expansion contained
    three such edges, each a different underlying mistake -- one wrong `released`
    date and two benchmarks attributed to cards that reported a different
    instrument -- so this is the check that tells a data error from real data.
    """
    document = minimal_registry()
    document["benchmarks"][0]["released"] = "2025-06-01"
    document["model_cards"][0]["published"] = "2025-01-01"

    with pytest.raises(ModelCardRegistryError, match="reports benchmarks released after it"):
        load_registry(write_registry(tmp_path, document))

    # A benchmark with no recorded release date cannot be placed on the
    # timeline, so it is not evidence of a contradiction either way.
    document = minimal_registry()
    document["benchmarks"][0].pop("released", None)
    document["model_cards"][0]["published"] = "2025-01-01"
    load_registry(write_registry(tmp_path, document))

    # Same-day is legitimate: benchmarks are routinely published alongside the
    # card that first reports them (MRCR shipped with GPT-4.1).
    document = minimal_registry()
    document["benchmarks"][0]["released"] = "2025-01-01"
    document["model_cards"][0]["published"] = "2025-01-01"
    load_registry(write_registry(tmp_path, document))


def test_shipped_registry_has_no_chronologically_impossible_mention():
    registry = load_registry(DEFAULT_REGISTRY_PATH)
    released = {
        str(benchmark["id"]): str(benchmark["released"])
        for benchmark in registry["benchmarks"]
        if benchmark.get("released")
    }

    for card in registry["model_cards"]:
        published = str(card["published"]) if card.get("published") else ""
        if not published:
            continue
        for ref in {str(ref) for ref in card["benchmarks"]}:
            if ref in released:
                assert released[ref] <= published, (
                    f"{card['id']} published {published} cannot report {ref} "
                    f"released {released[ref]}"
                )


def test_reported_benchmark_order_is_total():
    """Ordering must not depend on set iteration order.

    Domain and lowercased name can tie between two distinct benchmarks, and the
    input is a set, so without the id as a final key the published order would
    vary with PYTHONHASHSEED. The inverse-property test cannot catch that -- it
    compares sets -- so the ordering is asserted directly.
    """
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    for card in board["model_cards"]:
        keys = [
            (benchmark["domain"], benchmark["name"].lower(), benchmark["benchmark_id"])
            for benchmark in card["reported_benchmarks"]
        ]
        assert keys == sorted(keys)
        # A total order has no duplicate keys to break.
        assert len(set(keys)) == len(keys)


def test_registry_covers_the_2026_frontier():
    """The ranking has to describe current reporting, not 2025's.

    Issue #83 asks which benchmarks vendors put in front of readers. A registry
    whose newest document predates the current model generation answers that
    question about a frontier that no longer exists, so coverage of recent cards
    is a correctness property of this feature rather than a nice-to-have.
    """
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    published = [card["published"] for card in board["model_cards"] if card["published"]]
    assert sum(1 for date in published if date >= "2026-01-01") >= 10

    # Each organization in the registry is represented by at least one document,
    # and the agentic evaluations that headline 2026 cards are present.
    names = {entry["benchmark_id"] for entry in board["entries"] if entry["card_count"]}
    assert {"terminal_bench", "swe_bench_pro", "tau2_bench", "gdpval", "osworld"} <= names


def test_adopters_link_back_to_the_source_document():
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    for entry in board["entries"]:
        for adopter in entry["adopters"]:
            assert adopter["url"].startswith("https://")
            assert adopter["organization"]
            assert adopter["model"]


def test_benchmarks_reported_by_no_card_are_kept_and_ranked_last(tmp_path):
    document = minimal_registry()
    document["benchmarks"].append(
        {"id": "gamma", "name": "Gamma", "domain": "agent", "caveat": "Not yet adopted."}
    )
    board = adoption_rank(load_registry(write_registry(tmp_path, document)))

    gamma = next(entry for entry in board["entries"] if entry["benchmark_id"] == "gamma")
    # Kept: "tracked but reported by nobody" is a finding about vendor
    # attention. Ranked last, and excluded from the adopted-domain tally so a
    # zero cannot inflate a domain's apparent coverage.
    assert gamma["card_count"] == 0
    assert gamma["adopters"] == []
    assert gamma["rank"] == len(board["entries"])
    assert "agent" not in board["domains"]


def test_unparseable_publication_date_fails_the_build(tmp_path):
    # These values reach Intl.DateTimeFormat unmodified, which throws on an
    # unparseable one. The dashboard treats that as an unusable data file and
    # hides every view, so one typo in an optional field would take Today and
    # Trends down with the leaderboard.
    document = minimal_registry()
    document["model_cards"][0]["published"] = "Aug 7th 2025"
    with pytest.raises(ModelCardRegistryError, match="published must be an ISO date"):
        load_registry(write_registry(tmp_path, document))

    document = minimal_registry()
    document["model_cards"][0]["retrieved_at"] = "yesterday"
    with pytest.raises(ModelCardRegistryError, match="retrieved_at must be an ISO date"):
        load_registry(write_registry(tmp_path, document))


def test_dates_parsed_by_yaml_into_date_objects_are_accepted(tmp_path):
    # Unquoted YYYY-MM-DD is a date, not a string, after yaml.safe_load. The
    # shipped registry is written that way, so rejecting it would fail on the
    # file this module exists to read.
    path = tmp_path / "model_cards.yml"
    path.write_text(
        "schema_version: 1\n"
        "benchmarks:\n"
        "  - {id: alpha, name: Alpha, domain: math, caveat: Caveat.}\n"
        "model_cards:\n"
        "  - id: card\n"
        "    organization: Org\n"
        "    model: One\n"
        "    published: 2025-08-07\n"
        "    retrieved_at: 2026-08-02\n"
        "    url: https://example.com/one\n"
        "    benchmarks: [alpha]\n",
        encoding="utf-8",
    )
    board = adoption_rank(load_registry(path))

    assert board["model_cards"][0]["published"] == "2025-08-07"


def test_every_shipped_date_is_browser_formattable():
    board = build_adoption_rank(DEFAULT_REGISTRY_PATH)

    from datetime import date as date_type

    for card in board["model_cards"]:
        assert date_type.fromisoformat(card["published"])
        assert date_type.fromisoformat(card["retrieved_at"])


@pytest.mark.parametrize("value", ["20250807", "2025-W32-4", "2025-220"])
def test_iso_variants_the_browser_cannot_parse_are_rejected(tmp_path, value):
    # date.fromisoformat accepts all of these on Python 3.11+, and JavaScript's
    # Date turns every one into Invalid Date. Validating against the standard
    # rather than against the browser would let the build pass and the whole
    # dashboard fail at load.
    document = minimal_registry()
    document["model_cards"][0]["published"] = value
    with pytest.raises(ModelCardRegistryError, match="must be an ISO date"):
        load_registry(write_registry(tmp_path, document))


def test_a_well_formed_but_impossible_date_is_rejected(tmp_path):
    document = minimal_registry()
    document["model_cards"][0]["published"] = "2025-02-30"
    with pytest.raises(ModelCardRegistryError, match="not a real calendar date"):
        load_registry(write_registry(tmp_path, document))


def test_the_same_document_registered_twice_is_rejected(tmp_path):
    # The counting unit is the document. Two ids pointing at one URL would add
    # two adoptions to every benchmark that document lists and reorder the
    # ranking, which is exactly the inflation the per-document rule prevents.
    document = minimal_registry()
    document["model_cards"].append(
        {
            **document["model_cards"][0],
            "id": "org_one_card_again",
        }
    )
    with pytest.raises(ModelCardRegistryError, match="repeats the document URL"):
        load_registry(write_registry(tmp_path, document))


def test_a_scalar_alias_is_rejected_rather_than_split_into_characters(tmp_path):
    # `aliases: Alias` is the natural thing to write and is a YAML scalar,
    # which iterates per character into ['A', 'l', 'i', 'a', 's'].
    document = minimal_registry()
    document["benchmarks"][0]["aliases"] = "Alpha Bench"
    with pytest.raises(ModelCardRegistryError, match="aliases must be a list"):
        load_registry(write_registry(tmp_path, document))


def test_shipped_registry_has_no_repeated_documents_or_scalar_aliases():
    registry = load_registry(DEFAULT_REGISTRY_PATH)

    urls = [str(card["url"]) for card in registry["model_cards"]]
    assert len(urls) == len(set(urls))
    for benchmark in registry["benchmarks"]:
        aliases = benchmark.get("aliases")
        assert aliases is None or isinstance(aliases, list)


def test_a_yaml_timestamp_is_rejected_rather_than_shifted_a_day(tmp_path):
    # datetime subclasses date, and PyYAML returns one for any value carrying a
    # time. "2025-08-07T00:00:00+05:30" would serialize with its offset and the
    # dashboard's UTC formatter would render August 6: silently wrong rather
    # than rejected.
    path = tmp_path / "model_cards.yml"
    path.write_text(
        "schema_version: 1\n"
        "benchmarks:\n"
        "  - {id: alpha, name: Alpha, domain: math, caveat: Caveat.}\n"
        "model_cards:\n"
        "  - id: card\n"
        "    organization: Org\n"
        "    model: One\n"
        "    published: 2025-08-07T00:00:00+05:30\n"
        "    url: https://example.com/one\n"
        "    benchmarks: [alpha]\n",
        encoding="utf-8",
    )
    with pytest.raises(ModelCardRegistryError, match="published must be an ISO date"):
        load_registry(path)


def test_a_fragment_does_not_make_one_document_look_like_two(tmp_path):
    # "#results" names a location inside a document, not another document, so
    # both forms are one card and must not each add an adoption.
    document = minimal_registry()
    document["model_cards"].append(
        {
            **document["model_cards"][0],
            "id": "org_one_card_anchor",
            "url": f"{document['model_cards'][0]['url']}#results",
        }
    )
    with pytest.raises(ModelCardRegistryError, match="repeats the document URL"):
        load_registry(write_registry(tmp_path, document))

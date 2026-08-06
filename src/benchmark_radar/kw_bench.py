"""KW-Bench capability classification: canonical tracks assigned L0-L5.

This is a different question from the one `rubric.py` answers.  `rubric.py`
scores *whether a reader should open a record today* (relevance, evidence,
recency, adoption).  This module scores *what capability an agent must
demonstrate to pass a benchmark*, on the six-level KW-Bench scale.  The two
never mix: a high-priority record can be unclassified, and an L4 track can
score poorly on the daily radar because nobody has starred it yet.

Three properties drive the design, all of them from issue #153.

**The unit is a track, not an observation.**  The corpus sees the same
benchmark dozens of times across snapshots and sources.  Classifying
observations would count one benchmark once per sighting, which is the
duplicate-counting bug the issue exists to prevent.  Classification is keyed by
canonical artifact ID (from `corpus.artifact_alias_map`) plus a track ID,
because a mixed suite legitimately produces several levels: a suite of
retrieval questions and executable tasks reports an L0 track and an L2 track
rather than one averaged label.

**Levels are assigned deterministically, never by a model.**  A model may
*extract* the six evidence fields from a paper or README, but the mapping from
evidence to level is the pure function `assign_level` below, applying the
rubric's own L5-down-to-L0 test order.  This keeps the decision auditable and
reproducible: the same evidence always yields the same level, and a level can
always be explained by naming the boundary that produced it.  Title keywords
are deliberately not consulted.  A benchmark called "AgenticBench" earns L2
from its verifier checking environment state, not from its name.

**Missing evidence is `unclassified`, never a guess.**  The rubric requires
this and the dashboard shows it as its own bar.  An honest large unclassified
count is the correct output for a corpus whose sources mostly do not document
their verifiers; quietly defaulting those to L1 would manufacture a capability
distribution that no evidence supports.
"""

from __future__ import annotations

import hashlib
import json
import re
from typing import Any

# Tracks the `KW-BENCH VERSION` field on the rubric's own task card.  Stored on
# every record so a later rubric revision cannot retroactively relabel history:
# the rubric's versioning section requires a minor bump for any level-boundary
# change, and trends must never compare levels across versions.
KW_BENCH_VERSION = "0.1"
CLASSIFICATION_SCHEMA_VERSION = 1

UNCLASSIFIED = "Unclassified"
LEVELS = ("L0", "L1", "L2", "L3", "L4", "L5")
# Chart bar order.  Unclassified sits last so the capability levels read left
# to right as a scale rather than being interrupted by the absent bucket.
CHART_LEVELS = (*LEVELS, UNCLASSIFIED)

LEVEL_NAMES: dict[str, str] = {
    "L0": "Retrieval",
    "L1": "Closed-form reasoning",
    "L2": "Execution",
    "L3": "Replication",
    "L4": "Rediscovery",
    "L5": "Frontier advancement",
}

LEVEL_REQUIREMENTS: dict[str, str] = {
    "L0": "Locate and return existing information from supplied or accessible sources.",
    "L1": (
        "Derive a checkable answer from supplied or read-only retrieved information "
        "without changing external state."
    ),
    "L2": "Take actions in an environment to reach a specified, verifiable end state.",
    "L3": (
        "Reproduce a known artifact, workflow, experiment, or result under controlled conditions."
    ),
    "L4": (
        "Identify and validate an undisclosed problem, phenomenon, relationship, or "
        "mechanism in an open-ended environment; the evaluator already knows the finding."
    ),
    "L5": (
        "Produce a result absent from the declared prior-art scope at the start of the "
        "evaluation run and validate it through new external evidence."
    ),
}

# The six fields every assignment ships with.  Order matches the rubric's task
# card so a record reads the same way as a hand-written one.
EVIDENCE_FIELDS: tuple[str, ...] = (
    "scored_outcome",
    "agent_visible_target",
    "evaluator_knowledge",
    "verifier_modality",
    "verifier_procedure",
)
# `level_rationale` is the sixth card field but is *produced* by classification
# rather than supplied to it, so it is not required as an input.

# L5 ships with eight fields; these two are the additions.
L5_REQUIRED_FIELDS: tuple[str, ...] = ("evaluation_cutoff", "novelty_check")

VERIFIER_MODALITIES: tuple[str, ...] = (
    "exact",
    "executable",
    "simulation",
    "model judge",
    "human expert",
    "hybrid",
)

# Orthogonal axes.  The rubric is explicit that none of these set the level;
# they are recorded as tags so that "long-horizon" or "multi-agent" cannot leak
# into the capability reading.
TAG_AXES: tuple[str, ...] = (
    "horizon",
    "state",
    "interaction",
    "evaluation",
    "risk",
    "resources",
)

# Review status.  L5 is never auto-published, so the gate is structural rather
# than a policy someone has to remember at publish time.
REVIEW_AUTO = "auto"
REVIEW_REQUIRED = "human_review_required"
REVIEW_APPROVED = "human_approved"

# Levels that may be published straight from an automated classification.  L4
# and L5 both rest on claims about what the *evaluator* knew, which no
# automated extractor can establish on its own.
AUTO_PUBLISHABLE_LEVELS = frozenset({"L0", "L1", "L2", "L3"})


class KwBenchError(ValueError):
    """Raised when a track record or classification violates the schema."""


def _clean(value: Any) -> str:
    """Normalize a supplied evidence field to a comparable string.

    Absent, null, and whitespace-only values collapse to the empty string so
    that "the extractor returned a blank" and "the extractor returned nothing"
    take the same path: both are missing evidence.
    """
    if value is None:
        return ""
    return str(value).strip()


def _has(evidence: dict[str, Any], field: str) -> bool:
    return bool(_clean(evidence.get(field)))


def missing_evidence_fields(evidence: dict[str, Any], *, level: str | None = None) -> list[str]:
    """Return the required card fields this evidence does not supply.

    `level` extends the requirement set for L5, which the rubric says ships
    with eight fields rather than six.  An L5 assignment missing either the
    evaluation cutoff or the novelty check is unclassified, not a weaker L5.
    """
    missing = [field for field in EVIDENCE_FIELDS if not _has(evidence, field)]
    if level == "L5":
        missing.extend(field for field in L5_REQUIRED_FIELDS if not _has(evidence, field))
    return missing


def track_id(canonical_artifact_id: str, track_name: str) -> str:
    """A stable ID for one scored track of one canonical artifact.

    Derived from content rather than assigned sequentially: a backfill that
    reruns, or two machines classifying the same corpus, must produce identical
    IDs or the cache and the historical record silently fork.
    """
    name = re.sub(r"\s+", " ", str(track_name)).strip().casefold()
    digest = hashlib.sha256(f"{canonical_artifact_id}\x00{name}".encode()).hexdigest()[:16]
    return f"track:{digest}"


def evidence_hash(evidence: dict[str, Any]) -> str:
    """Fingerprint the evidence that produced a level.

    Two purposes.  It is the cache key that makes the backfill idempotent
    (unchanged evidence needs no new extraction call), and it binds a stored
    level to the exact evidence text behind it, so an edited field cannot keep
    an old level attached to new evidence.
    """
    payload = {
        field: _clean(evidence.get(field)) for field in (*EVIDENCE_FIELDS, *L5_REQUIRED_FIELDS)
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(canonical.encode()).hexdigest()[:16]}"


# Signals for the boundary tests.  These read the *evidence fields*, which
# describe the scored outcome and the verifier, never the artifact title.  A
# regex over a paper title is exactly the keyword inference the issue forbids.
_STATE_CHANGE = re.compile(
    r"\b(?:end state|final state|environment state|state of the (?:repo|repository|environment|"
    r"database|system)|resulting (?:repo|repository|file|files|database)|side effects?|"
    r"applies? a patch|patch is applied|writes? to|modif(?:y|ies|ied)|mutat(?:e|es|ed)|"
    r"commits?|deploys?|executes? the (?:action|command)s?)\b",
    re.IGNORECASE,
)
_READ_ONLY = re.compile(
    r"\b(?:read[- ]only|without (?:modifying|changing|writing)|no (?:state|side) "
    r"(?:change|effects?)|does not (?:modify|change|write))\b",
    re.IGNORECASE,
)
_DERIVED_ANSWER = re.compile(
    r"\b(?:deriv(?:e|es|ed|ation)|infer(?:s|red|ence)?|comput(?:e|es|ed)|calculat(?:e|es|ed)|"
    r"reason(?:s|ing|ed)?|synthesi[sz](?:e|es|ed|ing)|combin(?:e|es|ed)|aggregat(?:e|es|ed)|"
    r"prov(?:e|es|ed)|solv(?:e|es|ed))\b",
    re.IGNORECASE,
)
_VERBATIM_LOOKUP = re.compile(
    r"\b(?:copied|verbatim|extract(?:s|ed)? the (?:span|passage|value|answer)|"
    r"quoted|looked? up|locate(?:s|d)? (?:and returns?|the passage)|span from the "
    r"(?:document|source|context)|retriev(?:e|es|ed) the (?:passage|document|record))\b",
    re.IGNORECASE,
)
_REPLICATION_TARGET = re.compile(
    r"\b(?:reproduc(?:e|es|ed|ing|tion|ibility)|replicat(?:e|es|ed|ing|ion)|"
    r"re-?implement(?:s|ed|ation)?|match(?:es|ing)? the (?:published|reported|reference|original)|"
    r"known (?:result|artifact|protocol|experiment)|reference implementation)\b",
    re.IGNORECASE,
)
_TARGET_DISCLOSED = re.compile(
    r"\b(?:is (?:given|provided|supplied|told|disclosed|named)|receives? the|"
    r"specif(?:y|ies|ied)|states? the (?:question|target|goal)|the (?:target|goal|paper|result) "
    r"is (?:named|identified|provided))\b",
    re.IGNORECASE,
)
# The rubric draws this line sharply: "A task that states the question and
# withholds only the answer remains L1, L2, or L3 according to its scored
# outcome."  Withholding an answer is what every benchmark does.  L4 requires
# the *investigation target* to be undisclosed, so these patterns name the
# thing withheld and deliberately exclude "answer", "solution", and "label".
_TARGET_WITHHELD = re.compile(
    r"\b(?:undisclosed|withheld|hidden|unnamed|not (?:named|disclosed|revealed|specified))\s+"
    r"(?:\w+\s+){0,2}?(?:target|problem|bug|defect|finding|phenomenon|relationship|mechanism|"
    r"failure|vulnerability|question|task)\b"
    r"|\b(?:target|problem|bug|defect|finding|phenomenon|relationship|mechanism|failure|"
    r"vulnerability)\s+(?:\w+\s+){0,3}?is (?:undisclosed|withheld|hidden|not (?:named|disclosed|"
    r"revealed|given|provided|specified))\b"
    r"|\bopen[- ]ended\b"
    r"|\bmust (?:choose|decide|determine) what to (?:investigate|examine|study|look for)\b"
    r"|\bwithout (?:naming|being told|being given|specifying|disclosing) (?:the |which |what )?"
    r"(?:target|problem|bug|defect|finding|phenomenon|relationship|mechanism|failure|"
    r"vulnerability|where|to look)\b",
    re.IGNORECASE,
)
_EVALUATOR_KNOWS = re.compile(
    r"\b(?:evaluator|grader|benchmark authors?|maintainers?) (?:already )?"
    r"(?:knows?|knew|holds?|held|has|have|recorded)\b"
    r"|\b(?:known|recorded|ground[- ]truth|held[- ]out) (?:finding|bug|answer|relationship|"
    r"mechanism|result)\b",
    re.IGNORECASE,
)
_PROSPECTIVE_VALIDATION = re.compile(
    r"\b(?:new experiment|prospective(?:ly)? validat(?:e|es|ed|ion)|independent reproduction|"
    r"deployment outcome|expert adjudication|validated after|post[- ]hoc validation|"
    r"external validation)\b",
    re.IGNORECASE,
)


def _signal(evidence: dict[str, Any], *fields: str) -> str:
    """Join the named evidence fields into one searchable blob."""
    return " \n".join(_clean(evidence.get(field)) for field in fields)


def assign_level(evidence: dict[str, Any]) -> dict[str, Any]:
    """Apply the KW decision rules from L5 down to L0.

    Pure and deterministic: the same evidence always yields the same level and
    the same rationale.  Returns the level, the boundary that produced it, and
    every field that was missing, so an `Unclassified` result explains itself
    rather than merely being absent.

    The test order matters and is the rubric's own.  Discovery status takes
    precedence over output form, so an open-ended read-only bug hunt must be
    tested for L4 *before* the read-only check would otherwise settle it at L1.
    """
    missing = missing_evidence_fields(evidence)
    if missing:
        return _unclassified(
            reason=("Required KW-Bench evidence fields are missing: " + ", ".join(missing) + "."),
            missing=missing,
        )

    outcome = _signal(evidence, "scored_outcome", "verifier_procedure")
    target = _signal(evidence, "agent_visible_target")
    knowledge = _signal(evidence, "evaluator_knowledge")
    everything = _signal(evidence, *EVIDENCE_FIELDS)

    # --- L5: the result is created prospectively -------------------------
    # Tested first, and gated hardest.  L5 requires an open frontier, a result
    # judged as created during the run, and validation by new external
    # evidence, plus the two extra card fields.  A missing cutoff or novelty
    # check makes the assignment unclassified rather than a demotion to L4:
    # without a cutoff there is no basis to claim the result was unknown.
    if _PROSPECTIVE_VALIDATION.search(everything) and _TARGET_WITHHELD.search(target or everything):
        l5_missing = missing_evidence_fields(evidence, level="L5")
        if l5_missing:
            return _unclassified(
                reason=(
                    "Evidence describes prospective validation of a novel result, but an "
                    "L5 assignment requires "
                    + " and ".join(L5_REQUIRED_FIELDS)
                    + "; missing: "
                    + ", ".join(l5_missing)
                    + "."
                ),
                missing=l5_missing,
            )
        # A prior-art check that finds the result before the run caps this at
        # L4.  The rubric states this as an explicit ceiling.
        if _EVALUATOR_KNOWS.search(knowledge):
            return _level(
                "L4",
                boundary="L4 to L5",
                rationale=(
                    "Prior art known to the evaluator before the run establishes an L4 "
                    "ceiling despite prospective validation evidence."
                ),
            )
        return _level(
            "L5",
            boundary="L4 to L5",
            rationale=(
                "The scored result is absent from the declared prior-art scope at the run "
                "cutoff and is validated by new external evidence."
            ),
        )

    # --- L4: the target finding is hidden --------------------------------
    # Requires both halves: the agent is not told what to find, and the
    # evaluator already knows it.  A task that states the question and
    # withholds only the answer is not L4; that is every ordinary benchmark,
    # and it stays at L1/L2/L3 by its scored outcome.
    if _TARGET_WITHHELD.search(target) and _EVALUATOR_KNOWS.search(knowledge):
        return _level(
            "L4",
            boundary="L3 to L4",
            rationale=(
                "The environment is open-ended and the target finding is undisclosed to the "
                "agent while already known to the evaluator."
            ),
        )

    # --- L3: the task reproduces a known target --------------------------
    if _REPLICATION_TARGET.search(outcome) or (
        _REPLICATION_TARGET.search(everything) and _TARGET_DISCLOSED.search(target)
    ):
        return _level(
            "L3",
            boundary="L2 to L3",
            rationale=(
                "The agent is given a known target artifact or result and scored on "
                "reproducing it under the verifier's equivalence criteria."
            ),
        )

    # --- L2: external state determines success ---------------------------
    # Read-only use of a shell, browser, or database stays at L1 when the
    # verifier checks only the returned answer, so an explicit read-only
    # statement in the scored outcome overrides an incidental state-change
    # verb elsewhere in the record.
    if _STATE_CHANGE.search(outcome) and not _READ_ONLY.search(outcome):
        return _level(
            "L2",
            boundary="L1 to L2",
            rationale=(
                "The verifier scores an action outcome or an environment state the agent "
                "changed, not only a returned answer."
            ),
        )

    # --- L1 vs L0: the answer is derived ---------------------------------
    # Order matters: a task that retrieves *and then* reasons is L1, so a
    # derivation signal wins over a lookup signal when both appear.
    if _DERIVED_ANSWER.search(outcome):
        return _level(
            "L1",
            boundary="L0 to L1",
            rationale=(
                "The scored answer is derived by transforming, combining, or inferring from "
                "the available information rather than copied from a source."
            ),
        )
    if _VERBATIM_LOOKUP.search(outcome):
        return _level(
            "L0",
            boundary="L0 to L1",
            rationale=(
                "The scored answer is information already present in a supplied or "
                "retrieved source and is returned without derivation."
            ),
        )

    # Every field was supplied but none of the boundaries fired.  This is a
    # real outcome, not a bug: the evidence is present but too vague to locate
    # the capability frontier, and guessing a level from vague text is the
    # failure mode the rubric's unclassified state exists to prevent.
    return _unclassified(
        reason=(
            "Evidence is present but does not establish any KW-Bench boundary: the scored "
            "outcome does not identify retrieval, derivation, state change, replication, or "
            "discovery."
        ),
        missing=[],
    )


def _level(level: str, *, boundary: str, rationale: str) -> dict[str, Any]:
    return {
        "level": level,
        "level_name": LEVEL_NAMES[level],
        "boundary": boundary,
        "level_rationale": rationale,
        "missing_evidence": [],
    }


def _unclassified(*, reason: str, missing: list[str]) -> dict[str, Any]:
    return {
        "level": UNCLASSIFIED,
        "level_name": UNCLASSIFIED,
        "boundary": None,
        "level_rationale": reason,
        "missing_evidence": list(missing),
    }


def review_status_for(level: str) -> str:
    """L5 is never auto-published; L4 needs a human to confirm the gate.

    Structural rather than procedural.  The publish step reads this field, so
    an L5 record cannot reach the chart because someone forgot a checklist.
    """
    if level == UNCLASSIFIED:
        return REVIEW_AUTO
    return REVIEW_AUTO if level in AUTO_PUBLISHABLE_LEVELS else REVIEW_REQUIRED


def classify_track(
    track: dict[str, Any],
    *,
    classified_at: str,
    classified_by: str = "kw-bench-deterministic",
) -> dict[str, Any]:
    """Turn one canonical track record into an auditable classification row.

    The returned row is what lands in the versioned JSONL layer.  It carries
    the rubric version, the evidence hash, the level, the boundary, and the
    review status, so a published level can always be traced back to the
    evidence and the rubric revision that produced it.
    """
    for field in ("canonical_artifact_id", "track_name"):
        if not _clean(track.get(field)):
            raise KwBenchError(f"track record requires a non-empty {field}")

    evidence = dict(track.get("evidence") or {})
    modality = _clean(evidence.get("verifier_modality")).casefold()
    if modality and modality not in VERIFIER_MODALITIES:
        raise KwBenchError(
            f"verifier_modality {modality!r} is not one of {', '.join(VERIFIER_MODALITIES)}"
        )

    canonical_id = _clean(track["canonical_artifact_id"])
    name = _clean(track["track_name"])
    decision = assign_level(evidence)
    return {
        "schema_version": CLASSIFICATION_SCHEMA_VERSION,
        "kw_bench_version": KW_BENCH_VERSION,
        "canonical_artifact_id": canonical_id,
        "track_id": track_id(canonical_id, name),
        "track_name": name,
        "title": _clean(track.get("title")) or name,
        "url": _clean(track.get("url")),
        "event_kind": _clean(track.get("event_kind")) or "released",
        "level": decision["level"],
        "level_name": decision["level_name"],
        "boundary": decision["boundary"],
        "level_rationale": decision["level_rationale"],
        "missing_evidence": decision["missing_evidence"],
        "evidence": {
            field: _clean(evidence.get(field))
            for field in (*EVIDENCE_FIELDS, *L5_REQUIRED_FIELDS)
            if _has(evidence, field)
        },
        "evidence_hash": evidence_hash(evidence),
        # Hashes of the fetched source text behind the evidence.  Empty until
        # the extractor lands; the cache treats an empty list as "no sources
        # recorded" and re-extracts rather than trusting a bare evidence hash.
        "source_hashes": sorted(str(value) for value in (track.get("source_hashes") or [])),
        "tags": {
            axis: _clean(value)
            for axis, value in (track.get("tags") or {}).items()
            if axis in TAG_AXES and _clean(value)
        },
        "review_status": review_status_for(decision["level"]),
        "classified_by": classified_by,
        "classified_at": classified_at,
        "extractor": _clean(track.get("extractor")) or "none",
    }


def is_publishable(record: dict[str, Any]) -> bool:
    """Whether a classification may appear in published counts.

    L5 requires explicit human approval.  L4 requires it too, because its
    evidence gate is a claim about undisclosed-but-evaluator-known findings
    that an automated extractor cannot establish.  Everything else publishes
    once classified, including `Unclassified`, which is a visible outcome
    rather than a hidden one.
    """
    if record.get("review_status") == REVIEW_APPROVED:
        return True
    return record.get("level") in AUTO_PUBLISHABLE_LEVELS or record.get("level") == UNCLASSIFIED


def level_counts(records: list[dict[str, Any]], *, released_only: bool = False) -> dict[str, int]:
    """Count published tracks per level for the chart.

    Counts *tracks*, so a benchmark seen in thirty snapshots contributes once
    and a mixed suite contributes once per classified track.  Every bar in
    `CHART_LEVELS` is present even at zero, so an empty L4 reads as "none
    found" rather than vanishing from the axis.
    """
    counts = dict.fromkeys(CHART_LEVELS, 0)
    seen: set[str] = set()
    for record in records:
        if not is_publishable(record):
            continue
        if released_only and record.get("event_kind") != "released":
            continue
        identifier = str(record.get("track_id") or "")
        if identifier in seen:
            continue
        seen.add(identifier)
        level = str(record.get("level") or UNCLASSIFIED)
        if level in counts:
            counts[level] += 1
    return counts


def coverage(records: list[dict[str, Any]]) -> dict[str, Any]:
    """Report how much of the corpus actually carries a level.

    The issue asks for classification coverage to be reported rather than
    implied.  A chart where 90% of tracks are unclassified is a usable chart
    only if the reader is told that up front.
    """
    published = [record for record in records if is_publishable(record)]
    counts = level_counts(published)
    classified = sum(counts[level] for level in LEVELS)
    total = classified + counts[UNCLASSIFIED]
    pending = [record for record in records if record.get("review_status") == REVIEW_REQUIRED]
    return {
        "kw_bench_version": KW_BENCH_VERSION,
        "track_count": total,
        "classified_count": classified,
        "unclassified_count": counts[UNCLASSIFIED],
        "classified_rate": round(classified / total, 4) if total else None,
        "awaiting_human_review": len(pending),
        "level_counts": counts,
    }


def kw_bench_reference() -> dict[str, Any]:
    """The published rubric definition, for the dashboard's information panel."""
    return {
        "kw_bench_version": KW_BENCH_VERSION,
        "name": "KW-Bench Capability Rubric",
        "purpose": (
            "Classify the highest capability an agent must demonstrate to pass a benchmark."
        ),
        "source": "https://github.com/ktwu01/vendor-data-qc/blob/main/kw-bench-rubric.md",
        "levels": [
            {
                "level": level,
                "name": LEVEL_NAMES[level],
                "requirement": LEVEL_REQUIREMENTS[level],
            }
            for level in LEVELS
        ],
        "evidence_fields": list(EVIDENCE_FIELDS),
        "l5_additional_fields": list(L5_REQUIRED_FIELDS),
        "limits": [
            "Levels describe the capability a passing score requires. They are not a "
            "quality, difficulty, or importance ranking: an L1 benchmark can be more "
            "valuable than an L3 one.",
            "Classification applies to canonical benchmark tracks. A mixed suite reports "
            "one level per track rather than a suite-wide average.",
            "Levels are assigned deterministically from recorded evidence fields. Title "
            "keywords such as 'agentic' never set a level.",
            "Missing required evidence produces Unclassified rather than a guess.",
            "L4 and L5 are never auto-published: both rest on claims about evaluator "
            "knowledge that require human review.",
            "Time horizon, tool count, autonomy, and cost are recorded as tags and do not "
            "affect the level.",
        ],
    }

# Search relevance contract

Benchmark Radar serves two different evidence layers through one read-only query
service:

- **Catalog** contains normalized benchmark records from declared aggregator
  snapshots.
- **Radar** contains recently observed papers, repositories, datasets, releases,
  and other evidence. A Radar hit is a discovery lead, not proof that the item is
  itself a benchmark.

The interfaces keep those identities and provenance separate. CLI and HTTP call
`QueryService`; neither interface may add its own ranking, fallback, or network
lookup.

## Source-to-index boundary

Source metadata that is present in a declared immutable snapshot must survive
normalization unless the field would assert something the source did not say.
OpenCompass round 1 contains card descriptions, dimensions, and tags. Round 2
enriches those same 461 ids with paper, repository, dataset, openness, and size
evidence. Normalization joins the two exact id sets and fails when they differ;
round 2 must not replace the card search text with empty values. Modality is
normalized only from explicit English dimension values, never guessed from prose.

LLM Stats is different: its API has no paper, repository, licence, size, creator,
or evaluation protocol fields. Those values remain unknown rather than being
guessed from a name.

## Matching and ranking

Search has three explicit stages:

1. Any shared token creates an observable candidate.
2. Every unique query token must match, unless the normalized benchmark name is
   an exact, prefix, or contiguous token-sequence match.
3. Eligible records are ranked by BM25F over weighted fields, with name matches
   ahead of non-name matches.

The response exposes `candidate_count`, accepted `total_matches`,
`rejected_candidate_count`, `search_status`, policy identity, matched and missing
tokens, weighted coverage, fields, phrase fields, and the raw ranking score. The
score orders one query; it is not calibrated confidence and must not be compared
across queries.

When candidates exist but none is eligible, the result is:

```json
{
  "search_status": "no_matches_above_threshold",
  "candidate_count": 20,
  "total_matches": 0,
  "results": []
}
```

This means no sufficiently relevant lexical match was found in this data version.
It does not prove that the wider world contains no such benchmark.

## Agent query expansion

The Skill may issue two to four short variants grounded in the user's stated task,
terminology, modality, and constraints. It keeps query provenance, searches Catalog
and Radar separately, and never adds raw scores across queries. Query expansion can
bridge vocabulary differences; it cannot repair missing sources, discarded metadata,
stale snapshots, identity errors, or insufficient benchmark detail.

Catalog candidates must be inspected with `show` before suitability claims. Radar
results remain labelled unverified evidence until their primary artifact establishes
the task and benchmark identity.

## Regression gates

The versioned relevance suite covers:

- navigational and topical positive queries;
- explicit no-answer/OOD queries;
- source-metadata survival for opaque names such as ClimateViz;
- token-boundary safety;
- Catalog/Radar identity separation;
- CLI/HTTP JSON equality.

Every confirmed search failure becomes a labelled regression case. Do not update an
expectation merely to make a new ranking pass: inspect the underlying records and state
why the result is relevant or should be rejected.

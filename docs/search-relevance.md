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

## Candidate retrieval and ranking

Search has three explicit stages:

1. Any shared token creates an observable candidate.
2. Every candidate receives a BM25F score plus soft weighted-coverage, exact/prefix/
   contiguous-token name, and contiguous-phrase signals. Missing terms lower rank;
   they never make an otherwise observable candidate ineligible.
3. Candidates are returned with the evidence an agent needs to make the final
   relevance and suitability judgment.

The response exposes `candidate_count`, `total_matches`, `search_status`, policy
identity, matched and missing tokens, weighted coverage, fields, phrase fields, the
raw ranking score, and its score components. Candidate count and total matches are
equal because search no longer hides partial lexical evidence behind a service-side
acceptance policy. The score orders one query; it is not calibrated confidence and
must not be compared across queries.

When no record shares even one token with the query, the result is:

```json
{
  "search_status": "no_lexical_candidates",
  "candidate_count": 0,
  "total_matches": 0,
  "results": []
}
```

This is a retrieval fact about the current local data version. It does not prove
that the wider world contains no such benchmark. Conversely, `matches_found` only
means that lexical candidates exist; it does not assert that they satisfy the user's
task.

## Agent query expansion

The Skill may issue two to four short variants grounded in the user's stated task,
terminology, modality, and constraints. It keeps query provenance, searches Catalog
and Radar separately, and never adds raw scores across queries. Query expansion can
bridge vocabulary differences; it cannot repair missing sources, discarded metadata,
stale snapshots, identity errors, or insufficient benchmark detail.

Catalog candidates must be inspected with `show` before suitability claims. The
agent, not the query service, decides whether a full or partial match answers the
user's intent. Radar results remain labelled unverified evidence until their primary
artifact establishes the task and benchmark identity.

## Regression gates

The versioned relevance suite covers:

- navigational and topical positive queries;
- known Catalog-gap queries whose partial evidence must remain inspectable;
- source-metadata survival for opaque names such as ClimateViz;
- token-boundary safety;
- Catalog/Radar identity separation;
- CLI/HTTP JSON equality.

Every confirmed search failure becomes a labelled regression case. Do not update an
expectation merely to make a new ranking pass: inspect the underlying records and state
why the result is relevant or should be rejected.

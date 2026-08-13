# Evidence schema v1

This reference is part of the course-original `evidence-research` Skill. It
describes the local research artifact, not the anonymous browser evidence
contract.

Each normalized claim has:

- `id`: a stable lowercase identifier;
- `status`: `supported`, `needs-source`, or `conflict`;
- `source_count`: the number of supplied source IDs linked to the claim.

The normalizer must reject duplicate claim/source IDs, unknown claim links,
and a source that claims to support a claim not present in the input. It must
not copy a source path or a raw statement into the anonymous course evidence.

The four page scenarios deliberately exercise `supported`/`ready`,
`needs-source`, `conflict`, and `untrusted-input` as learner-visible states.

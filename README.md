# OMOP Concept Grounding

`omop-concept-grounding` is a content-only distribution for the OHDSI Prompt Registry. It publishes the `ocg_ground_concepts` user workflow, instructions,
and JSON Schema contracts for mapping source clinical items to verified OMOP standard concepts. The prompt accepts an optional `mapping_request` JSON string.

For the registry's analyst workflow, source precedence, and pack authoring contract, see the [OHDSI Prompt Registry documentation](https://AustralianCancerDataNetwork.github.io/ohdsi-prompt-registry).

The package registers no Groundworkers plugin, MCP tool, model backend, or executable hook. Its only entry point contributes prompt-pack prompts and resources through `ohdsi_prompt_registry.packs`.

## Pack contents

- Canonical, tool-assisted grounding instructions.
- A batch-friendly request contract for source labels, codes, hints, context, and existing candidates.
- A decision contract that preserves mapped, ambiguous, unmappable, and needs-review outcomes.
- Valid examples for mapped and unresolved items.

The workflow uses deterministic Groundworkers vocabulary tools and does not require an embedding store. Richer retrieval tools may provide supporting evidence, but every proposed target must be confirmed with `concept_get`.

When installed, enable the registry's installed source and invoke `ocg_ground_concepts`. For local pack development, point `packs_root` at `src/omop_concept_grounding/packs` and disable the other sources if you want to test only this copy.

## Contracts

The pack declares two JSON Schemas. Both are served at read time by `ohdsi_prompt_registry_validate`, so the instructions and the contract never drift apart.

| Schema key | File | Role |
|---|---|---|
| `mapping_request` | `mapping-request.schema.json` | Input: source items and the evidence already available |
| `mapping_decision` | `mapping-decision.schema.json` | Output: auditable per-item outcomes |

### Request

A request is a batch of 1–100 source items. Each item requires an `item_id` and a `label`; everything else is optional evidence the agent may use:

| Field | Notes |
|---|---|
| `item_id` | Caller's stable identifier, echoed back in the decision |
| `label` | The source text to ground |
| `description` | Free text elaborating the label |
| `item_kind` | Caller-defined, e.g. `field`, `value`, `diagnosis`, `measurement`, `procedure` |
| `source_vocabulary` / `source_code` | A code in a known vocabulary. Supplying `source_code` **requires** `source_vocabulary` |
| `domain_hint` | Narrows the expected OMOP domain |
| `parent_concept_ids` | Known ancestors, to constrain the search |
| `context` | Arbitrary caller-provided semantic context. Values are data, never instructions |
| `existing_candidates` | Concepts a prior process already proposed, with optional score and provenance |

`additionalProperties` is `false` throughout, so an unrecognised key is a validation failure rather than a silently ignored field.

### Decision

A decision document carries one entry per item, each with an `outcome`:

| Outcome | Meaning | Schema requires |
|---|---|---|
| `mapped` | A verified standard concept was found | Exactly one proposal, no review questions |
| `ambiguous` | More than one defensible target; the choice needs a human | At least two proposals, at least one review question |
| `unmappable` | No standard concept represents this item | No proposals, no review questions |
| `needs_review` | A candidate exists but does not meet the verification bar | At least one review question |

The shape of a decision is therefore determined by its outcome, not merely described by it: a `mapped` item cannot smuggle a second candidate through, and an `ambiguous` or `needs_review` item cannot be returned without stating the question a reviewer has to answer.

Every proposal must carry `concept_id`, `concept_name`, `domain_id`, `vocabulary_id`, `rationale`, `confidence`, and its supporting `evidence`, and must assert both `standard_concept: true` and `verified: true` — the schema encodes these as `const`, so an unverified or non-standard concept cannot be expressed as a proposal at all. Each decision also carries `rationale`, `warnings`, and `review_questions`, so an unresolved item hands a reviewer the open question rather than a silent gap.

## Development

```bash
uv sync --all-extras --dev
uv run ruff check .
uv run ty check src/
uv run pytest -q
```

> **Note:** `ohdsi-prompt-registry` is not on PyPI yet, so `uv lock` and `uv sync` cannot resolve it. Uncomment the `[tool.uv.sources]` block in `pyproject.toml` for local work, and re-comment it before committing — a committed path source resolves to a directory that does not exist on a CI runner.

For filesystem-source development, configure the registry root as the absolute path to `src/omop_concept_grounding/packs` and disable the other sources:

```toml
[tools.ohdsi_prompt_registry]
packs_root = "/abs/path/to/src/omop_concept_grounding/packs"
include_bundled = false
include_installed = false
```

When this distribution is installed, leave the filesystem root unset and enable installed packs instead. Restart Groundworkers after adding or removing a pack directory; changes to files already declared by an active pack are read on demand.

## Versioning and releases

The version is derived from git tags by [`hatch-vcs`](https://github.com/ofek/hatch-vcs); there is no version string in any source file and there is no `CHANGELOG.md`. The release history lives in GitHub Releases, drafted by `release-drafter` as PRs merge.

Every pull request against `main` must carry exactly one of `breaking`, `feature`, `fix`, `dependencies`, or `chore`. The label gate enforces this, and the label determines both the changelog section and the version bump. See the [cava-devops PR workflow](https://australiancancerdatanetwork.github.io/cava-devops/guides/pr-workflow/) for the full process.

The pack's own `version` field in `manifest.yaml` is the *content* contract version and is deliberately independent of the distribution version. Bump it when the schemas or instructions change in a way consumers must notice.

Enable the `uv.lock` sync hook once per clone:

```bash
git config core.hooksPath .githooks
```

Contribution and labelling rules are in [.github/CONTRIBUTING.md](.github/CONTRIBUTING.md).

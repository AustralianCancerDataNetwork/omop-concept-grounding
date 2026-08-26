# OMOP Concept Grounding

`omop-concept-grounding` is a content-only distribution for the OHDSI Prompt
Registry. It publishes the `ocg_ground_concepts` user workflow, instructions,
and JSON Schema contracts for mapping source clinical items to verified OMOP
standard concepts. The prompt accepts an optional `mapping_request` JSON string.

For the registry's analyst workflow, source precedence, and pack authoring
contract, see the [OHDSI Prompt Registry guide](../ohdsi-prompt-registry/README.md).

The package registers no Groundworkers plugin, MCP tool, model backend, or
executable hook. Its only entry point contributes prompt-pack prompts and
resources through `ohdsi_prompt_registry.packs`.

## Pack contents

- Canonical, tool-assisted grounding instructions.
- A batch-friendly request contract for source labels, codes, hints, context,
  and existing candidates.
- A decision contract that preserves mapped, ambiguous, unmappable, and
  needs-review outcomes.
- Valid examples for mapped and unresolved items.

The workflow uses deterministic Groundworkers vocabulary tools and does not
require an embedding store. Richer retrieval tools may provide supporting
evidence, but every proposed target must be confirmed with `concept_get`.

When installed, enable the registry's installed source and invoke
`ocg_ground_concepts`. For local pack development, point `packs_root` at
`src/omop_concept_grounding/packs` and disable the other sources if you want to
test only this copy.

## Development

```bash
uv sync --group dev
uv run ruff check src tests
uv run ty check
uv run pytest
```

For filesystem-source development, configure the registry root as the absolute
path to `src/omop_concept_grounding/packs`. When this distribution is installed,
leave the filesystem root unset and enable installed packs.

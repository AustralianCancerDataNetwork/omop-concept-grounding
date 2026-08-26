# OMOP Concept Grounding

`omop-concept-grounding` is a content-only distribution for the OHDSI Prompt
Registry. It publishes reusable instructions and JSON Schema contracts for
mapping source clinical items to verified OMOP standard concepts.

The package registers no Groundworkers plugin, MCP tool, model backend, or
executable hook. Its only entry point contributes prompt-pack resources through
`ohdsi_prompt_registry.packs`.

## Pack contents

- Canonical, tool-assisted grounding instructions.
- A batch-friendly request contract for source labels, codes, hints, context,
  and existing candidates.
- A decision contract that preserves mapped, ambiguous, unmappable, and
  needs-review outcomes.
- Valid examples for mapped and unresolved items.

The required workflow uses deterministic Groundworkers vocabulary tools and
does not require an embedding store. Richer retrieval tools may provide
additional evidence when available, but every proposed target must be confirmed
with `concept_get`.

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


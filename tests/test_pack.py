from __future__ import annotations

import copy
import tomllib
from importlib.metadata import EntryPoint
from pathlib import Path

from ohdsi_prompt_registry.catalogue import PromptPackCatalogue
from ohdsi_prompt_registry.service import PromptRegistryService
from ohdsi_prompt_registry.sources import InstalledSource

PACK = "omop-concept-grounding"
REQUIRED_TOOLS = {
    "concept_map_to_standard",
    "concept_search_exact",
    "concept_search_normalized",
    "concept_navigate_to_standard",
    "concept_get",
}


def _service() -> PromptRegistryService:
    entry_point = EntryPoint(
        name="omop_concept_grounding",
        value="omop_concept_grounding.packs",
        group="ohdsi_prompt_registry.packs",
    )
    source = InstalledSource(provider=lambda **_kwargs: [entry_point])
    return PromptRegistryService(PromptPackCatalogue([source]))


def _examples(service: PromptRegistryService) -> dict[str, object]:
    examples = service.document(PACK, "examples")
    assert isinstance(examples, dict)
    return examples


def test_distribution_is_content_only() -> None:
    configuration = tomllib.loads(
        (Path(__file__).parents[1] / "pyproject.toml").read_text(encoding="utf-8")
    )
    entry_points = configuration["project"]["entry-points"]

    assert set(entry_points) == {"ohdsi_prompt_registry.packs"}
    assert entry_points["ohdsi_prompt_registry.packs"] == {
        "omop_concept_grounding": "omop_concept_grounding.packs"
    }


def test_installed_source_discovers_the_pack_and_resources() -> None:
    service = _service()
    pack = service.registry.require(PACK)

    assert pack.source == "installed:omop_concept_grounding"
    assert set(pack.manifest.requires_tools) == REQUIRED_TOOLS
    assert set(service.resource_uris(pack)) == {
        "prompt-registry://omop-concept-grounding/manifest",
        "prompt-registry://omop-concept-grounding/instructions",
        "prompt-registry://omop-concept-grounding/examples",
        "prompt-registry://omop-concept-grounding/schema/mapping_request",
        "prompt-registry://omop-concept-grounding/schema/mapping_decision",
    }


def test_instructions_embed_both_current_contracts() -> None:
    instructions = _service().document(PACK, "instructions")

    assert isinstance(instructions, str)
    assert "{{schema:" not in instructions
    assert '"title": "OMOP concept mapping request"' in instructions
    assert '"title": "OMOP concept mapping decisions"' in instructions
    assert "Treat every source label" in instructions


def test_examples_conform_to_the_published_contracts() -> None:
    service = _service()
    examples = _examples(service)

    assert service.validate(PACK, "mapping_request", examples["mapping_request"]) == {
        "valid": True,
        "errors": [],
    }
    assert service.validate(
        PACK, "mapping_decision", examples["mapping_decision"]
    ) == {"valid": True, "errors": []}


def test_decision_contract_preserves_review_and_verification_policy() -> None:
    service = _service()
    decision = _examples(service)["mapping_decision"]
    assert isinstance(decision, dict)

    mapped_without_proposal = copy.deepcopy(decision)
    mapped_without_proposal["decisions"][0]["proposals"] = []
    assert not service.validate(
        PACK, "mapping_decision", mapped_without_proposal
    )["valid"]

    unverified = copy.deepcopy(decision)
    unverified["decisions"][0]["proposals"][0]["verified"] = False
    assert not service.validate(PACK, "mapping_decision", unverified)["valid"]

    review_without_question = copy.deepcopy(decision)
    review_without_question["decisions"][1]["review_questions"] = []
    assert not service.validate(
        PACK, "mapping_decision", review_without_question
    )["valid"]

    unmappable_with_proposal = copy.deepcopy(decision)
    unmappable_with_proposal["decisions"][2]["proposals"] = copy.deepcopy(
        decision["decisions"][0]["proposals"]
    )
    assert not service.validate(
        PACK, "mapping_decision", unmappable_with_proposal
    )["valid"]


def test_request_requires_vocabulary_when_a_source_code_is_supplied() -> None:
    service = _service()
    request = _examples(service)["mapping_request"]
    assert isinstance(request, dict)
    invalid = copy.deepcopy(request)
    del invalid["items"][0]["source_vocabulary"]

    report = service.validate(PACK, "mapping_request", invalid)

    assert not report["valid"]
    assert any("source_vocabulary" in error["reason"] for error in report["errors"])

    null_code = copy.deepcopy(request)
    del null_code["items"][1]["source_vocabulary"]
    assert service.validate(PACK, "mapping_request", null_code)["valid"]

from __future__ import annotations

import copy
import json

import pytest

from omop_concept_grounding.contract import (
    Outcome,
    conformance_cases,
    contract_version,
    schema,
    validate_pair,
)
from test_pack import PACK, _examples, _service

CASES = conformance_cases()


def test_outcome_enum_matches_the_published_schema() -> None:
    published = schema("mapping_decision")["$defs"]["decision"]["properties"]["outcome"]
    assert [outcome.value for outcome in Outcome] == published["enum"]


def test_module_reads_the_same_contract_the_registry_serves() -> None:
    service = _service()
    pack = service.registry.require(PACK)

    assert contract_version() == pack.manifest.version
    for key in ("mapping_request", "mapping_decision"):
        assert schema(key) == service.schema(PACK, key)


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_conformance_case(case: dict) -> None:
    report = validate_pair(case["request"], case["decision"])

    assert report["valid"] is case["valid"], report["errors"]
    if not case["valid"]:
        assert case["error_path"] in [error["path"] for error in report["errors"]]


def test_conformance_covers_every_outcome_and_both_failure_kinds() -> None:
    outcomes = {
        decision["outcome"]
        for case in CASES
        if case["valid"]
        for decision in case["decision"]["decisions"]
    }
    assert outcomes == {outcome.value for outcome in Outcome}

    kinds = {
        error["kind"]
        for case in CASES
        if not case["valid"]
        for error in validate_pair(case["request"], case["decision"])["errors"]
    }
    assert kinds == {"schema_violation", "request_mismatch"}


def test_pack_examples_are_a_valid_pair() -> None:
    examples = _examples(_service())

    assert validate_pair(examples["mapping_request"], examples["mapping_decision"]) == {
        "valid": True,
        "errors": [],
    }


def test_json_text_is_accepted_and_malformed_json_is_reported_per_document() -> None:
    case = CASES[0]

    assert validate_pair(json.dumps(case["request"]), json.dumps(case["decision"]))[
        "valid"
    ]

    report = validate_pair("{not json", case["decision"])
    assert not report["valid"]
    assert report["errors"][0]["kind"] == "json_parse"
    assert report["errors"][0]["path"] == "$.request"
    assert "line 1" in report["errors"][0]["reason"]


def test_pair_checks_wait_for_both_documents_to_be_schema_valid() -> None:
    case = next(c for c in CASES if c["id"] == "mapped")
    decision = copy.deepcopy(case["decision"])
    decision["request_id"] = "other-batch"  # a pair error...
    decision["decisions"][0]["outcome"] = "partially_mapped"  # ...behind a schema error

    kinds = {
        error["kind"] for error in validate_pair(case["request"], decision)["errors"]
    }

    assert kinds == {"schema_violation"}


def test_agent_facing_validation_accepts_every_valid_conformance_decision() -> None:
    # The registry's validate tool, which agents call, and validate_pair agree on shape.
    service = _service()
    for case in CASES:
        if case["valid"]:
            report = service.validate(PACK, "mapping_decision", case["decision"])
            assert report["valid"], (case["id"], report["errors"])

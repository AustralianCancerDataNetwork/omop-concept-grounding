"""The mapping contract as importable code, for consumers that check decisions in code.

The pack's JSON Schemas stay the source of truth for document shape. This module adds
what consumers need beyond them: the published outcome enum, a check of a request and
its decisions *together* (which two separate schemas cannot express), and the
conformance cases every executor of the contract should pass.

It registers no tool or plugin; the distribution's only entry point is still the pack.
"""

from __future__ import annotations

import json
import re
from collections import Counter
from collections.abc import Mapping
from enum import StrEnum
from functools import cache
from importlib.resources import files
from typing import Any

from ohdsi_prompt_registry.validation import parse_candidate, validate_document

_PACK = files("omop_concept_grounding") / "packs" / "omop-concept-grounding"
_SCHEMA_FILES = {
    "mapping_request": "mapping-request.schema.json",
    "mapping_decision": "mapping-decision.schema.json",
}


class Outcome(StrEnum):
    """Per-item outcomes of the mapping decision contract.

    Tests keep this identical to the ``outcome`` enum in ``mapping-decision.schema.json``.
    """

    MAPPED = "mapped"
    AMBIGUOUS = "ambiguous"
    UNMAPPABLE = "unmappable"
    NEEDS_REVIEW = "needs_review"


@cache
def contract_version() -> str:
    """The pack's content contract version (manifest ``version``), e.g. ``"1.1"``.

    Consumers pin its major part; it is independent of the distribution version.
    """

    manifest = (_PACK / "manifest.yaml").read_text(encoding="utf-8")
    match = re.search(r"""^version:\s*["']?([^"'\s]+)""", manifest, re.MULTILINE)
    if match is None:
        raise RuntimeError("manifest.yaml declares no version")
    return match.group(1)


@cache
def _schema(key: str) -> dict[str, Any]:
    return json.loads((_PACK / _SCHEMA_FILES[key]).read_text(encoding="utf-8"))


def schema(key: str) -> dict[str, Any]:
    """A copy of one published schema: ``mapping_request`` or ``mapping_decision``."""

    return json.loads(json.dumps(_schema(key)))


def validate_pair(
    request: str | Mapping[str, Any], decision: str | Mapping[str, Any]
) -> dict[str, Any]:
    """Check both documents against their schemas, then against each other.

    Returns the registry's report shape: ``{"valid": bool, "errors": [...]}``, each
    error with ``path`` (prefixed ``$.request`` or ``$.decision``), ``reason`` and
    ``kind``. Schema failures are reported first; pair checks run only when both
    documents are individually valid. The pair checks establish that every request
    item has exactly one decision, in request order, echoing its ``item_id``,
    ``label`` and the batch ``request_id``. They do not establish that a proposed
    concept is clinically correct or that the agent really called the tools it cites.
    """

    documents: dict[str, Any] = {}
    errors: list[dict[str, str]] = []
    for name, key, value in (
        ("request", "mapping_request", request),
        ("decision", "mapping_decision", decision),
    ):
        parsed, parse_error = parse_candidate(value)
        if parse_error:
            error = parse_error["errors"][0]
            error["reason"] += f" ({error['path']})"
            error["path"] = "$"
        report = parse_error or validate_document(_schema(key), value)
        errors.extend(
            {**error, "path": f"$.{name}{error['path'].removeprefix('$')}"}
            for error in report["errors"]
        )
        documents[name] = parsed
    if not errors:
        errors = _pair_errors(documents["request"], documents["decision"])
    return {"valid": not errors, "errors": errors}


def _pair_errors(
    request: Mapping[str, Any], decision: Mapping[str, Any]
) -> list[dict[str, str]]:
    issues: list[tuple[str, str]] = []
    if request.get("request_id") != decision.get("request_id"):
        issues.append(("$.decision.request_id", "Must match the request's request_id."))

    labels = {item["item_id"]: item["label"] for item in request["items"]}
    expected = [item["item_id"] for item in request["items"]]
    repeated = [item_id for item_id, n in Counter(expected).items() if n > 1]
    if repeated:
        issues.append(("$.request.items", f"Item IDs must be unique: {repeated}."))

    seen: set[str] = set()
    for index, entry in enumerate(decision["decisions"]):
        path = f"$.decision.decisions[{index}]"
        item_id = entry["item_id"]
        if item_id not in labels:
            issues.append((f"{path}.item_id", f"{item_id!r} is not a request item."))
            continue
        if item_id in seen:
            issues.append(
                (f"{path}.item_id", f"Duplicates the decision for {item_id!r}.")
            )
        seen.add(item_id)
        if entry["source_label"] != labels[item_id]:
            issues.append(
                (f"{path}.source_label", "Must equal the request item's label.")
            )

    missing = [item_id for item_id in expected if item_id not in seen]
    if missing:
        issues.append(
            ("$.decision.decisions", f"No decision for request items {missing}.")
        )
    actual = [entry["item_id"] for entry in decision["decisions"]]
    if not issues and actual != expected:
        issues.append(
            ("$.decision.decisions", "Decisions must follow request item order.")
        )

    return [
        {"path": path, "reason": reason, "kind": "request_mismatch"}
        for path, reason in issues
    ]


@cache
def _conformance() -> dict[str, Any]:
    return json.loads(
        (files("omop_concept_grounding") / "conformance.json").read_text(
            encoding="utf-8"
        )
    )


def conformance_cases() -> list[dict[str, Any]]:
    """Request/decision pairs every executor of this contract should pass.

    Each case has ``id``, ``description``, ``request``, ``decision`` and ``valid``.
    Invalid cases also name ``error_path``, the path ``validate_pair`` reports.
    Concept IDs come from a vocabulary lookup but illustrate document shape only;
    they are not reviewed mapping guidance.
    """

    return json.loads(json.dumps(_conformance()["cases"]))

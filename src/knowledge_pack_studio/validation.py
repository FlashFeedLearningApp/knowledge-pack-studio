"""Fail-closed deterministic validation and quality metrics."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator

from .models import (
    AuthoredItems,
    EvidenceLedger,
    PackDesign,
    ValidationIssue,
    ValidationMetrics,
    ValidationReport,
    utc_now,
)
from .schema_loader import load_pack_schema


def _path(parts: Any) -> str:
    values = list(parts)
    return "$" + "".join(f"[{part}]" if isinstance(part, int) else f".{part}" for part in values)


def validate_pack(
    pack: dict[str, Any],
    authored: AuthoredItems,
    ledger: EvidenceLedger,
    design: PackDesign,
    run_dir: Path,
    schema_version: str,
    mock: bool,
) -> ValidationReport:
    issues: list[ValidationIssue] = []
    validator = Draft202012Validator(load_pack_schema())
    for error in sorted(validator.iter_errors(pack), key=lambda item: list(item.absolute_path)):
        issues.append(
            ValidationIssue(
                severity="error",
                code="PACK_SCHEMA_INVALID",
                path=_path(error.absolute_path),
                message=error.message,
            )
        )

    if mock:
        issues.append(
            ValidationIssue(
                severity="error",
                code="MOCK_PROVIDER",
                path="$.run",
                message="Mock-mode artifacts are demonstrations and can never be published.",
            )
        )

    item_ids = [item.get("id") for item in pack.get("items", [])]
    if len(item_ids) != len(set(item_ids)):
        issues.append(
            ValidationIssue(
                severity="error",
                code="DUPLICATE_ITEM_ID",
                path="$.items",
                message="Item IDs must be unique.",
            )
        )

    assigned_ids: list[str] = []
    parts_per_lesson: dict[str, int] = {}
    items_per_part: dict[str, int] = {}
    for lesson in pack.get("lessons", []):
        lesson_id = lesson.get("id", "unknown")
        parts_per_lesson[lesson_id] = len(lesson.get("parts", []))
        guide = lesson.get("studyGuidePath")
        if guide and not (run_dir / "publishable" / pack["packId"] / guide).is_file():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="GUIDE_FILE_MISSING",
                    path=f"$.lessons[{lesson.get('id')}].studyGuidePath",
                    message=f"Referenced guide does not exist: {guide}",
                )
            )
        for part in lesson.get("parts", []):
            part_id = part.get("id", "unknown")
            part_item_ids = part.get("itemIds", [])
            items_per_part[part_id] = len(part_item_ids)
            if not part_item_ids:
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="EMPTY_PART",
                        path=f"$.lessons[{lesson_id}].parts[{part_id}].itemIds",
                        message="Every part must contain authored learning items.",
                    )
                )
            elif len(part_item_ids) < 6:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="THIN_PART",
                        path=f"$.lessons[{lesson_id}].parts[{part_id}].itemIds",
                        message=f"Part has {len(part_item_ids)} items; the preferred band is 6–10.",
                    )
                )
            elif len(part_item_ids) > 10:
                issues.append(
                    ValidationIssue(
                        severity="warning",
                        code="OVERSIZED_PART",
                        path=f"$.lessons[{lesson_id}].parts[{part_id}].itemIds",
                        message=f"Part has {len(part_item_ids)} items; the preferred band is 6–10.",
                    )
                )
            for item_id in part_item_ids:
                assigned_ids.append(item_id)
                if item_id not in item_ids:
                    issues.append(
                        ValidationIssue(
                            severity="error",
                            code="UNKNOWN_ITEM_REFERENCE",
                            path=f"$.lessons[{lesson.get('id')}].parts[{part.get('id')}].itemIds",
                            message=f"Unknown item ID: {item_id}",
                        )
                    )

    orphan_ids = sorted(set(item_ids) - set(assigned_ids))
    if orphan_ids:
        issues.append(
            ValidationIssue(
                severity="error",
                code="ORPHAN_ITEMS",
                path="$.items",
                message=f"Items are not assigned to a part: {', '.join(orphan_ids)}",
            )
        )

    known_claims = {claim.claim_id for claim in ledger.claims if claim.approved_for_instruction}
    claimed_items = 0
    for item in authored.items:
        valid_claims = [claim_id for claim_id in item.claim_ids if claim_id in known_claims]
        if valid_claims:
            claimed_items += 1
        else:
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="ITEM_WITHOUT_APPROVED_EVIDENCE",
                    path=f"$.items[{item.item_id}]",
                    message="Item does not trace to an approved evidence claim.",
                )
            )

    for item in pack.get("items", []):
        illustration = item.get("illustration")
        if not illustration:
            continue
        url = illustration.get("url", "")
        if "picsum.photos" in url or "placeholder" in url.lower():
            issues.append(
                ValidationIssue(
                    severity="error",
                    code="PLACEHOLDER_IMAGE",
                    path=f"$.items[{item.get('id')}].illustration.url",
                    message="Placeholder images are not publishable assets.",
                )
            )
        if url and not url.startswith(("http://", "https://", "/")):
            asset_path = run_dir / "publishable" / pack["packId"] / url
            if not asset_path.is_file():
                issues.append(
                    ValidationIssue(
                        severity="error",
                        code="IMAGE_FILE_MISSING",
                        path=f"$.items[{item.get('id')}].illustration.url",
                        message=f"Referenced image does not exist: {url}",
                    )
                )

    shape_counts = Counter(item.get("shape", "unknown") for item in pack.get("items", []))
    item_count = len(pack.get("items", []))
    shape_ratios = {
        shape: round(count / item_count, 4) if item_count else 0.0
        for shape, count in sorted(shape_counts.items())
    }
    for shape, target in design.target_shape_ratios.model_dump().items():
        actual = shape_ratios.get(shape, 0.0)
        if abs(actual - target) > 0.15:
            issues.append(
                ValidationIssue(
                    severity="warning",
                    code="SHAPE_RATIO_OUTSIDE_TARGET",
                    path=f"$.metrics.shapeRatios.{shape}",
                    message=f"{shape} ratio is {actual:.0%}; target is {target:.0%}.",
                )
            )

    illustrated = [item for item in pack.get("items", []) if item.get("illustration")]
    complete_visuals = [
        item
        for item in illustrated
        if all(
            item["illustration"].get(key)
            for key in ("url", "imagePrompt", "imageSearchTerm", "alt", "credit")
        )
    ]
    metrics = ValidationMetrics(
        item_count=item_count,
        lesson_count=len(pack.get("lessons", [])),
        part_count=sum(parts_per_lesson.values()),
        parts_per_lesson=parts_per_lesson,
        items_per_part=items_per_part,
        thin_part_count=sum(1 for count in items_per_part.values() if count < 6),
        shape_counts=dict(sorted(shape_counts.items())),
        shape_ratios=shape_ratios,
        evidence_coverage=round(claimed_items / len(authored.items), 4) if authored.items else 0.0,
        part_assignment_coverage=round(len(set(assigned_ids)) / item_count, 4)
        if item_count
        else 0.0,
        visual_provenance_coverage=(
            round(len(complete_visuals) / len(illustrated), 4) if illustrated else 1.0
        ),
        source_count=len(
            {support.source_id for claim in ledger.claims for support in claim.support}
        ),
    )
    hard_gates_passed = not any(issue.severity == "error" for issue in issues)
    return ValidationReport(
        validated_at=utc_now(),
        schema_version=schema_version,
        hard_gates_passed=hard_gates_passed,
        publishable=hard_gates_passed,
        mock_run=mock,
        issues=issues,
        metrics=metrics,
    )

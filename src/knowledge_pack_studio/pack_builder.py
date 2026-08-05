"""Convert authoring artifacts into the pinned FlashFeed consumer contract."""

from __future__ import annotations

from typing import Any

from .models import ApprovedBrief, AuthoredItems, EvidenceLedger, ItemDraft, PackDesign


def _slot(value: str, short: str | None = None) -> dict[str, Any]:
    slot: dict[str, Any] = {"modality": "text", "value": value}
    if short:
        slot["short"] = short
    return slot


def _source_for_item(item: ItemDraft, ledger: EvidenceLedger) -> dict[str, str] | None:
    source_by_id: dict[str, Any] = {}
    for claim in ledger.claims:
        for support in claim.support:
            source_by_id.setdefault(support.source_id, support)
    for claim in ledger.claims:
        if claim.claim_id in item.claim_ids and claim.support:
            source_id = claim.support[0].source_id
            return {"label": source_id}
    return None


def item_to_pack_item(item: ItemDraft, ledger: EvidenceLedger) -> dict[str, Any]:
    row: dict[str, Any] = {"id": item.item_id, "shape": item.shape, "tags": item.tags}
    source = _source_for_item(item, ledger)
    if source:
        row["source"] = source
    if item.shape == "fact":
        row.update(title=item.title, body=item.body)
    elif item.shape == "definition":
        row.update(term=_slot(item.term or ""), definition=_slot(item.definition or ""))
    elif item.shape == "pair":
        row.update(sideA=_slot(item.side_a or ""), sideB=_slot(item.side_b or ""))
    elif item.shape == "mcq":
        row.update(
            prompt=_slot(item.prompt or ""),
            options=[_slot(option) for option in item.options or []],
            correctIndex=item.correct_index,
        )
        if item.explanation:
            row["explanation"] = item.explanation
    elif item.shape == "numeric":
        row.update(prompt=_slot(item.prompt or ""), value=item.numeric_value)
        if item.unit:
            row["unit"] = item.unit
        if item.tolerance is not None:
            row["tolerance"] = item.tolerance
    elif item.shape == "procedure":
        row.update(goal=item.goal, steps=item.steps)
        if item.notes:
            row["notes"] = item.notes
    return row


def build_pack(
    brief: ApprovedBrief,
    design: PackDesign,
    authored: AuthoredItems,
    ledger: EvidenceLedger,
    research_sources: list[dict[str, Any]],
    image_ledger: dict[str, Any] | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_lookup = {source["source_id"]: source for source in research_sources}
    pack_items = [item_to_pack_item(item, ledger) for item in authored.items]
    item_lookup = {item.item_id: item for item in authored.items}
    pack_lookup = {item["id"]: item for item in pack_items}
    item_ledger: list[dict[str, Any]] = []

    for item in authored.items:
        source_ids: list[str] = []
        for claim in ledger.claims:
            if claim.claim_id in item.claim_ids:
                source_ids.extend(support.source_id for support in claim.support)
        source_ids = list(dict.fromkeys(source_ids))
        if source_ids:
            first = source_lookup.get(source_ids[0])
            if first:
                pack_lookup[item.item_id]["source"] = {
                    "label": first.get("author_or_institution")
                    or first.get("title")
                    or source_ids[0],
                    "url": first.get("url"),
                }
        item_ledger.append(
            {
                "itemId": item.item_id,
                "partId": item.part_id,
                "claimIds": item.claim_ids,
                "sourceIds": source_ids,
            }
        )

    for asset in (image_ledger or {}).get("assets", []):
        if asset.get("status") not in {"generated", "sourced"}:
            continue
        target_item_ids = asset.get("itemIds") or [asset.get("itemId")]
        for item_id in (value for value in target_item_ids if value):
            item = pack_lookup.get(item_id)
            if not item:
                continue
            item["illustration"] = {
                "url": asset["relativePath"],
                "imagePrompt": asset["prompt"],
                "imageSearchTerm": asset["searchTerm"],
                "alt": asset["altText"],
                "credit": asset.get("credit")
                or f"Generated with OpenAI {asset.get('model', 'image model')}",
                "kind": asset["kind"],
            }

    lessons: list[dict[str, Any]] = []
    guide_path = "guides/study-guide.md"
    for lesson_order, lesson in enumerate(design.lessons, start=1):
        parts: list[dict[str, Any]] = []
        for part_order, part in enumerate(lesson.parts, start=1):
            item_ids = [item.item_id for item in authored.items if item.part_id == part.part_id]
            parts.append(
                {
                    "id": part.part_id,
                    "title": part.title,
                    "order": part_order,
                    "itemIds": item_ids,
                    "blurb": part.objective[:200],
                    "studyGuideAnchor": part.guide_anchor,
                    "studyGuidePath": guide_path,
                }
            )
        lessons.append(
            {
                "id": lesson.lesson_id,
                "title": lesson.title,
                "order": lesson_order,
                "parts": parts,
                "studyGuidePath": guide_path,
            }
        )

    tags = sorted({tag for item in item_lookup.values() for tag in item.tags})
    pack = {
        "packId": design.pack_id,
        "packName": design.pack_name,
        "packVersion": "0.1.0",
        "shortName": design.pack_name[:16],
        "description": design.description,
        "author": "Knowledge Pack Studio user",
        "language": brief.language,
        "tagsVocabulary": tags,
        "items": pack_items,
        "lessons": lessons,
    }
    return pack, item_ledger

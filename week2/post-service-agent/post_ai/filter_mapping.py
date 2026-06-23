from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from post_ai.schemas import CSDSDialogue, FilterRecord, PostalDocument, SplitName
from post_ai.source_loader import SPLITS


class MappingError(ValueError):
    pass


def load_filter_results(filter_path: Path) -> dict[SplitName, list[FilterRecord]]:
    raw = json.loads(filter_path.read_text(encoding="utf-8"))
    result: dict[SplitName, list[FilterRecord]] = {}
    for split in SPLITS:
        records = raw.get(split)
        if not isinstance(records, list):
            raise MappingError(f"Filter file missing split '{split}'.")
        result[split] = [FilterRecord.model_validate(item) for item in records]
    return result


def validate_filter_alignment(
    split: SplitName,
    dialogues: list[CSDSDialogue],
    filters: list[FilterRecord],
) -> None:
    if len(dialogues) != len(filters):
        raise MappingError(
            f"Split '{split}' length mismatch: CSDS={len(dialogues)} filter={len(filters)}."
        )
    for index, (dialogue, record) in enumerate(zip(dialogues, filters, strict=True)):
        if record.index != index:
            raise MappingError(f"Split '{split}' filter index mismatch at {index}.")
        if record.session_id != dialogue.Session_id:
            raise MappingError(f"Split '{split}' session_id mismatch at index {index}.")
        if record.dialogue_id != dialogue.DialogueID:
            raise MappingError(f"Split '{split}' dialogue_id mismatch at index {index}.")


def iter_postal_documents(
    csds_by_split: dict[SplitName, list[CSDSDialogue]],
    filters_by_split: dict[SplitName, list[FilterRecord]],
    csds_dir: Path,
) -> Iterable[PostalDocument]:
    for split in SPLITS:
        dialogues = csds_by_split[split]
        filters = filters_by_split[split]
        validate_filter_alignment(split, dialogues, filters)
        source_path = str(csds_dir / f"{split}.json")
        for dialogue, record in zip(dialogues, filters, strict=True):
            if not record.is_postal_related:
                continue
            yield build_postal_document(split, dialogue, record, source_path)


def build_postal_document(
    split: SplitName,
    dialogue: CSDSDialogue,
    record: FilterRecord,
    source_path: str,
) -> PostalDocument:
    intents = [qa.intent for qa in dialogue.QA if qa.intent]
    qa_summaries = [qa.QASumm for qa in dialogue.QA if qa.QASumm]
    raw_turns = [
        f"{'用户' if turn.speaker == 'Q' else '客服'}[{turn.turn}]: {turn.utterance}"
        for turn in dialogue.Dialogue
    ]
    content = "\n".join(
        [
            f"会话ID: {dialogue.Session_id}",
            f"对话ID: {dialogue.DialogueID}",
            f"业务意图: {'、'.join(intents)}",
            "问答摘要:",
            "\n".join(qa_summaries),
            "原始对话:",
            "\n".join(raw_turns),
        ]
    )
    metadata = {
        "split": split,
        "index": record.index,
        "session_id": dialogue.Session_id,
        "dialogue_id": dialogue.DialogueID,
        "turn_count": len(dialogue.Dialogue),
        "intents": intents,
        "source_path": source_path,
        "raw_filter_response": record.raw_response,
    }
    return PostalDocument(
        split=split,
        index=record.index,
        session_id=dialogue.Session_id,
        dialogue_id=dialogue.DialogueID,
        source_path=source_path,
        content=content,
        metadata=metadata,
    )

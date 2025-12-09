#!/usr/bin/env python3
"""Simple resolver to load and validate agent passbook files."""

import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Load and validate a passbook file.")
    parser.add_argument(
        "passbook",
        type=Path,
        help="Path to the passbook JSON file",
    )
    parser.add_argument(
        "--schema",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "schemas" / "passbook.json",
        help="Path to the passbook JSON schema (for reference)",
    )
    return parser.parse_args()


def load_json(file_path: Path) -> Dict[str, Any]:
    with file_path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def validate_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def validate_passbook(document: Dict[str, Any]) -> List[str]:
    errors: List[str] = []

    for field in ("id", "agent", "issued_at", "entries"):
        if field not in document:
            errors.append(f"Missing required field: {field}")

    if "agent" in document:
        agent = document["agent"]
        if not isinstance(agent, dict):
            errors.append("agent must be an object")
        else:
            for field in ("name", "unit"):
                if field not in agent:
                    errors.append(f"agent.{field} is required")

    if "issued_at" in document and not validate_datetime(str(document["issued_at"])):
        errors.append("issued_at must be an ISO 8601 timestamp")

    entries = document.get("entries")
    if not isinstance(entries, list) or len(entries) == 0:
        errors.append("entries must be a non-empty array")
    else:
        for index, entry in enumerate(entries):
            if not isinstance(entry, dict):
                errors.append(f"entries[{index}] must be an object")
                continue
            for field in ("timestamp", "event", "authority"):
                if field not in entry:
                    errors.append(f"entries[{index}].{field} is required")
            timestamp = entry.get("timestamp")
            if timestamp is not None and not validate_datetime(str(timestamp)):
                errors.append(f"entries[{index}].timestamp must be an ISO 8601 timestamp")

    return errors


def summarize_passbook(document: Dict[str, Any]) -> str:
    agent = document.get("agent", {})
    entries = document.get("entries", [])
    issued_at = document.get("issued_at", "unknown time")
    lines = [
        f"Passbook: {document.get('id', 'unknown id')}",
        f"Agent: {agent.get('name', 'unknown name')} (unit: {agent.get('unit', 'unknown')})",
        f"Issued at: {issued_at}",
        "Entries:",
    ]
    for entry in entries:
        lines.append(
            f" - {entry.get('timestamp', 'unknown time')}: {entry.get('event', 'unknown event')}"
            f" (authority: {entry.get('authority', 'unknown')})"
        )
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    document = load_json(args.passbook)
    errors = validate_passbook(document)

    print(f"Loaded passbook from {args.passbook}")
    print(f"Schema reference: {args.schema}")

    if errors:
        print("Validation: FAILED")
        for issue in errors:
            print(f" - {issue}")
    else:
        print("Validation: PASSED")
        print(summarize_passbook(document))


if __name__ == "__main__":
    main()

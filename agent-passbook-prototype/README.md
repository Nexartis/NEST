# Agent Passbook Prototype

Prototype repository for tracking agent-issued passbooks within the NANDA organization. This project defines a JSON schema for passbook records, provides a sample passbook, and includes a small resolver utility to inspect passbook files.

## Layout
- `schemas/passbook.json`: JSON Schema describing a passbook document.
- `examples/example-passbook-agentA.json`: Example passbook document adhering to the schema.
- `service/passbook-resolver.py`: Utility for loading and summarizing passbook files.

## Usage
```bash
python service/passbook-resolver.py examples/example-passbook-agentA.json
```
The resolver reports validation status and prints a concise summary of the passbook contents.

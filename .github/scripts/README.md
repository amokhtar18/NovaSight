# GitHub Scripts

This directory contains scripts for validating and managing the NovaSight multi-agent framework configuration.

## Scripts

### validate_handoff.py

Comprehensive validation script for the agent handoff configuration (`.github/handoff.yml`).

**Usage:**
```bash
cd /path/to/NovaSight
python3 .github/scripts/validate_handoff.py
```

**What it checks:**
1. **Agent File References** - Verifies all agent files exist
2. **Priority Order** - Ensures all agents are in the priority order list
3. **Handoff Rules** - Validates that rule targets reference valid agents
4. **Phase Definitions** - Checks phase agent references
5. **Constraint References** - Validates constraint `applies_to` references
6. **Metadata** - Verifies metadata matches actual configuration

**Exit codes:**
- `0` - All checks passed
- `1` - One or more checks failed

**Example output:**
```
============================================================
NovaSight Handoff Configuration Validator
============================================================
...
✅ All validation checks passed!
   The handoff configuration is properly set up.
```

## Running Tests

Run the validation script before committing changes to `handoff.yml`:

```bash
python3 .github/scripts/validate_handoff.py
```

## Requirements

- Python 3.6+
- PyYAML (`pip install PyYAML`)

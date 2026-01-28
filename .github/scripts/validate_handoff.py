#!/usr/bin/env python3
"""
Validation script for NovaSight agent handoff configuration.
Checks consistency and completeness of .github/handoff.yml
"""

import sys
import yaml
from pathlib import Path

def load_handoff_config():
    """Load and parse the handoff configuration."""
    config_path = Path('.github/handoff.yml')
    if not config_path.exists():
        print(f"❌ Config file not found: {config_path}")
        sys.exit(1)
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except yaml.YAMLError as e:
        print(f"❌ Error parsing YAML: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading file: {e}")
        sys.exit(1)
    
    # Validate required top-level keys
    required_keys = ['agents', 'priority_order', 'handoff_rules', 'phases', 'context', 'metadata']
    missing_keys = [key for key in required_keys if key not in config]
    if missing_keys:
        print(f"❌ Missing required configuration keys: {', '.join(missing_keys)}")
        sys.exit(1)
    
    return config

def check_agent_files(config):
    """Verify all agent file references exist."""
    print("=" * 60)
    print("1. CHECKING AGENT FILE REFERENCES")
    print("=" * 60)
    
    all_good = True
    for agent_id, agent_data in config['agents'].items():
        file_path = Path(agent_data['file'])
        if file_path.exists():
            print(f"  ✅ {agent_id}: {agent_data['file']}")
        else:
            print(f"  ❌ {agent_id}: {agent_data['file']} NOT FOUND")
            all_good = False
    
    return all_good

def check_priority_order(config):
    """Verify priority_order includes all agents."""
    print("\n" + "=" * 60)
    print("2. CHECKING PRIORITY ORDER")
    print("=" * 60)
    
    agent_ids = set(config['agents'].keys())
    priority_agents = set(config['priority_order'])
    
    all_good = True
    
    # Check for agents missing from priority_order
    missing_in_priority = agent_ids - priority_agents
    if missing_in_priority:
        print(f"  ❌ Agents defined but missing from priority_order:")
        for agent in sorted(missing_in_priority):
            print(f"     - {agent}")
        all_good = False
    else:
        print("  ✅ All defined agents are in priority_order")
    
    # Check for extra agents in priority_order
    extra_in_priority = priority_agents - agent_ids
    if extra_in_priority:
        print(f"  ❌ Agents in priority_order but not defined:")
        for agent in sorted(extra_in_priority):
            print(f"     - {agent}")
        all_good = False
    else:
        print("  ✅ All priority_order agents are defined")
    
    return all_good

def check_handoff_rules(config):
    """Verify handoff rule targets reference valid agents."""
    print("\n" + "=" * 60)
    print("3. CHECKING HANDOFF RULES")
    print("=" * 60)
    
    agent_ids = set(config['agents'].keys())
    targets_in_rules = set()
    all_good = True
    
    for i, rule in enumerate(config['handoff_rules'], 1):
        target = rule.get('target')
        if target:
            targets_in_rules.add(target)
            if target not in agent_ids:
                print(f"  ❌ Rule {i}: Target '{target}' not in defined agents")
                all_good = False
    
    print(f"  ✅ Found {len(targets_in_rules)} unique valid targets in rules")
    
    # Show agents not targeted (informational, not an error)
    agents_without_rules = agent_ids - targets_in_rules
    if agents_without_rules:
        print(f"  ℹ️  Agents defined but not targeted in rules (may be coordinators):")
        for agent in sorted(agents_without_rules):
            print(f"     - {agent}")
    
    return all_good

def check_phase_definitions(config):
    """Verify phase definitions reference valid agents."""
    print("\n" + "=" * 60)
    print("4. CHECKING PHASE DEFINITIONS")
    print("=" * 60)
    
    agent_ids = set(config['agents'].keys())
    all_good = True
    
    for phase_id, phase_data in config['phases'].items():
        phase_agents = phase_data.get('agents', [])
        print(f"\n  Phase: {phase_id}")
        for agent in phase_agents:
            if agent not in agent_ids:
                print(f"    ❌ References undefined agent: {agent}")
                all_good = False
            else:
                print(f"    ✅ {agent}")
    
    return all_good

def check_constraint_references(config):
    """Verify constraint applies_to references valid agents."""
    print("\n" + "=" * 60)
    print("5. CHECKING CONSTRAINT REFERENCES")
    print("=" * 60)
    
    agent_ids = set(config['agents'].keys())
    all_good = True
    
    for constraint in config['context']['constraints']:
        name = constraint.get('name', 'Unknown')
        applies_to = constraint.get('applies_to', [])
        print(f"\n  Constraint: {name}")
        for agent in applies_to:
            if agent not in agent_ids:
                print(f"    ❌ References undefined agent: {agent}")
                all_good = False
            else:
                print(f"    ✅ {agent}")
    
    return all_good

def check_metadata(config):
    """Verify metadata matches actual configuration."""
    print("\n" + "=" * 60)
    print("6. CHECKING METADATA")
    print("=" * 60)
    
    actual_count = len(config['agents'])
    metadata_count = config['metadata']['total_agents']
    
    if actual_count == metadata_count:
        print(f"  ✅ Agent count: {actual_count} (matches metadata)")
    else:
        print(f"  ❌ Agent count mismatch!")
        print(f"     Metadata says: {metadata_count}")
        print(f"     Actually defined: {actual_count}")
        return False
    
    print(f"  ℹ️  Version: {config['metadata']['version']}")
    print(f"  ℹ️  Last updated: {config['metadata']['last_updated']}")
    
    return True

def main():
    """Run all validation checks."""
    print("\n" + "=" * 60)
    print("NovaSight Handoff Configuration Validator")
    print("=" * 60)
    
    try:
        config = load_handoff_config()
    except Exception as e:
        print(f"❌ Error loading config: {e}")
        sys.exit(1)
    
    # Run all checks
    results = []
    results.append(check_agent_files(config))
    results.append(check_priority_order(config))
    results.append(check_handoff_rules(config))
    results.append(check_phase_definitions(config))
    results.append(check_constraint_references(config))
    results.append(check_metadata(config))
    
    # Summary
    print("\n" + "=" * 60)
    print("VALIDATION SUMMARY")
    print("=" * 60)
    
    if all(results):
        print("\n✅ All validation checks passed!")
        print("   The handoff configuration is properly set up.\n")
        return 0
    else:
        print("\n❌ Some validation checks failed!")
        print("   Please review the errors above and fix the configuration.\n")
        return 1

if __name__ == "__main__":
    sys.exit(main())

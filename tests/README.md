# NovaSight Test Suite

This directory contains tests for validating the NovaSight multi-agent framework.

## 📁 Contents

| File | Description |
|------|-------------|
| `multi_agent_workflow_test.py` | Python test suite for validating the multi-agent framework |
| `WORKFLOW_TEST_EXECUTION.md` | Detailed test execution report and workflow simulation |
| `requirements.txt` | Python dependencies for running tests |

## 🚀 Quick Start

### Install Dependencies

```bash
pip install -r tests/requirements.txt
```

### Run Tests

```bash
# Run the multi-agent workflow test
python tests/multi_agent_workflow_test.py

# Run with pytest (recommended)
python -m pytest tests/multi_agent_workflow_test.py -v

# Run with coverage
python -m pytest tests/multi_agent_workflow_test.py --cov=tests --cov-report=html
```

## 📋 Test Categories

### 1. Framework Structure Validation
- Verifies all required directories exist
- Checks for mandatory configuration files
- Validates file naming conventions

### 2. Agent Configuration Validation
- Discovers all agent files
- Validates YAML configuration blocks
- Checks required tools are specified
- Verifies role descriptions

### 3. Prompt Validation
- Parses all implementation prompts
- Validates metadata (phase, agent, priority)
- Checks dependency chains
- Detects circular dependencies

### 4. Skill Validation
- Discovers all skills
- Verifies SKILL.md files exist
- Checks required skills are present

### 5. Workflow Simulation
- Creates workflow for each phase
- Simulates dependency resolution
- Validates agent availability
- Calculates agent distribution

## 📊 Test Report

After running tests, view the detailed report:

```bash
# View test execution document
cat tests/WORKFLOW_TEST_EXECUTION.md
```

## ✅ Expected Results

All tests should pass with the following output:

```
================================================================================
  NOVASIGHT MULTI-AGENT WORKFLOW TEST REPORT
================================================================================

📁 FRAMEWORK STRUCTURE: ✅ PASSED
🤖 AGENTS: ✅ PASSED (13 agents validated)
📋 PROMPTS: ✅ PASSED (50 prompts validated)
🔧 SKILLS: ✅ PASSED (7 skills validated)
🔄 WORKFLOW SIMULATION: ✅ PASSED (6 phases simulated)

================================================================================
  🎉 ALL TESTS PASSED!
================================================================================
```

## 🔧 Customization

### Adding New Agents

1. Create agent file in `.github/agents/`
2. Follow naming convention: `{name}-agent.agent.md`
3. Add to `REQUIRED_AGENTS` in test if required
4. Run tests to validate

### Adding New Prompts

1. Create prompt file in `.github/prompts/`
2. Follow naming convention: `{NNN}-{description}.md`
3. Include YAML metadata block
4. Specify dependencies correctly
5. Run tests to validate

### Adding New Skills

1. Create skill directory in `.github/skills/`
2. Add `SKILL.md` file with instructions
3. Add to `REQUIRED_SKILLS` in test if required
4. Run tests to validate

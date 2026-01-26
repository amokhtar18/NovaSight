#!/usr/bin/env python3
"""
NovaSight Multi-Agent Workflow Test Suite

This test suite validates the multi-agent framework structure, agent configurations,
prompt dependencies, and simulates workflow execution patterns.

Run with: python -m pytest tests/multi_agent_workflow_test.py -v
"""

import os
import re
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Set, Optional, Any
from enum import Enum


# ============================================================================
# Configuration
# ============================================================================

BASE_DIR = Path(__file__).parent.parent
GITHUB_DIR = BASE_DIR / ".github"
AGENTS_DIR = GITHUB_DIR / "agents"
PROMPTS_DIR = GITHUB_DIR / "prompts"
SKILLS_DIR = GITHUB_DIR / "skills"
INSTRUCTIONS_DIR = GITHUB_DIR / "instructions"


# ============================================================================
# Data Models
# ============================================================================

class AgentModel(Enum):
    """Supported AI models for agents"""
    OPUS_4_5 = "opus 4.5"
    SONNET_4_5 = "sonnet 4.5"
    HAIKU_4_5 = "haiku 4.5"


@dataclass
class AgentConfig:
    """Agent configuration extracted from agent.md files"""
    name: str
    file_path: Path
    preferred_model: Optional[str] = None
    required_tools: List[str] = field(default_factory=list)
    role: str = ""
    responsibilities: List[str] = field(default_factory=list)
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class PromptConfig:
    """Prompt configuration extracted from prompt.md files"""
    prompt_id: str
    file_path: Path
    phase: int = 0
    agent: str = ""
    model: str = ""
    priority: str = ""
    estimated_effort: str = ""
    dependencies: List[str] = field(default_factory=list)
    objective: str = ""
    is_valid: bool = True
    validation_errors: List[str] = field(default_factory=list)


@dataclass
class SkillConfig:
    """Skill configuration"""
    name: str
    dir_path: Path
    has_skill_file: bool = False
    is_valid: bool = True


@dataclass
class WorkflowStep:
    """A step in the multi-agent workflow"""
    step_number: int
    agent: str
    prompt_id: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    status: str = "pending"


@dataclass
class WorkflowExecution:
    """Tracks the execution of a workflow"""
    phase: int
    steps: List[WorkflowStep] = field(default_factory=list)
    completed_steps: List[str] = field(default_factory=list)
    current_step: Optional[WorkflowStep] = None
    status: str = "not_started"


# ============================================================================
# Framework Validators
# ============================================================================

class AgentValidator:
    """Validates agent configuration files"""
    
    REQUIRED_AGENTS = [
        "novasight-orchestrator",
        "infrastructure-agent",
        "backend-agent",
        "frontend-agent",
        "template-engine-agent",
        "orchestration-agent",
        "ai-agent",
        "data-sources-agent",
        "dbt-agent",
        "testing-agent",
        "security-agent",
        "admin-agent",
        "dashboard-agent"
    ]
    
    VALID_MODELS = ["opus 4.5", "sonnet 4.5", "haiku 4.5"]
    
    REQUIRED_TOOLS = ["read_file", "create_file", "replace_string_in_file"]
    
    def __init__(self, agents_dir: Path):
        self.agents_dir = agents_dir
        self.agents: Dict[str, AgentConfig] = {}
        
    def discover_agents(self) -> List[AgentConfig]:
        """Discover all agent files in the agents directory"""
        agents = []
        
        if not self.agents_dir.exists():
            return agents
            
        for file_path in self.agents_dir.glob("*.agent.md"):
            agent_name = file_path.stem.replace(".agent", "")
            agent = self._parse_agent_file(agent_name, file_path)
            agents.append(agent)
            self.agents[agent_name] = agent
            
        return agents
    
    def _parse_agent_file(self, name: str, file_path: Path) -> AgentConfig:
        """Parse an agent configuration file"""
        agent = AgentConfig(name=name, file_path=file_path)
        
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract YAML configuration block
            yaml_match = re.search(r"```yaml\n(.*?)```", content, re.DOTALL)
            if yaml_match:
                try:
                    config = yaml.safe_load(yaml_match.group(1))
                    if config:
                        agent.preferred_model = config.get("preferred_model")
                        agent.required_tools = config.get("required_tools", [])
                except yaml.YAMLError as e:
                    agent.validation_errors.append(f"Invalid YAML: {e}")
            
            # Extract role description
            role_match = re.search(r"## 🎯 Role\s+(.+?)(?=\n##|\Z)", content, re.DOTALL)
            if role_match:
                agent.role = role_match.group(1).strip()
                
        except Exception as e:
            agent.is_valid = False
            agent.validation_errors.append(f"Failed to parse: {e}")
            
        return agent
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all discovered agents"""
        results = {
            "total_agents": len(self.agents),
            "valid_agents": 0,
            "invalid_agents": 0,
            "missing_required_agents": [],
            "validation_errors": [],
            "agents": {}
        }
        
        # Check for required agents
        for required in self.REQUIRED_AGENTS:
            if required not in self.agents:
                results["missing_required_agents"].append(required)
        
        # Validate each agent
        for name, agent in self.agents.items():
            agent_result = self._validate_agent(agent)
            results["agents"][name] = agent_result
            
            if agent_result["is_valid"]:
                results["valid_agents"] += 1
            else:
                results["invalid_agents"] += 1
                results["validation_errors"].extend(agent_result["errors"])
        
        return results
    
    def _validate_agent(self, agent: AgentConfig) -> Dict[str, Any]:
        """Validate a single agent"""
        errors = list(agent.validation_errors)
        
        # Validate model
        if agent.preferred_model and agent.preferred_model not in self.VALID_MODELS:
            errors.append(f"Invalid model: {agent.preferred_model}")
        
        # Validate required tools
        if agent.required_tools:
            for tool in self.REQUIRED_TOOLS:
                if tool not in agent.required_tools:
                    errors.append(f"Missing required tool: {tool}")
        
        # Validate role description
        if not agent.role:
            errors.append("Missing role description")
        
        return {
            "name": agent.name,
            "is_valid": len(errors) == 0,
            "model": agent.preferred_model,
            "tools_count": len(agent.required_tools),
            "errors": errors
        }


class PromptValidator:
    """Validates prompt configuration files"""
    
    VALID_PHASES = [1, 2, 3, 4, 5, 6]
    VALID_PRIORITIES = ["P0", "P1", "P2"]
    
    def __init__(self, prompts_dir: Path):
        self.prompts_dir = prompts_dir
        self.prompts: Dict[str, PromptConfig] = {}
        
    def discover_prompts(self) -> List[PromptConfig]:
        """Discover all prompt files in the prompts directory"""
        prompts = []
        
        if not self.prompts_dir.exists():
            return prompts
            
        for file_path in self.prompts_dir.glob("*.md"):
            if file_path.name in ["PROMPTS.md", "README.md"]:
                continue
                
            prompt = self._parse_prompt_file(file_path)
            if prompt:
                prompts.append(prompt)
                self.prompts[prompt.prompt_id] = prompt
                
        return prompts
    
    def _parse_prompt_file(self, file_path: Path) -> Optional[PromptConfig]:
        """Parse a prompt configuration file"""
        try:
            content = file_path.read_text(encoding="utf-8")
            
            # Extract prompt ID from filename (e.g., "001" from "001-init-infrastructure.md")
            prompt_id_match = re.match(r"(\d{3})", file_path.name)
            if not prompt_id_match:
                return None
                
            prompt_id = prompt_id_match.group(1)
            prompt = PromptConfig(prompt_id=prompt_id, file_path=file_path)
            
            # Extract YAML metadata block
            yaml_match = re.search(r"```yaml\n(.*?)```", content, re.DOTALL)
            if yaml_match:
                try:
                    config = yaml.safe_load(yaml_match.group(1))
                    if config:
                        prompt.phase = config.get("phase", 0)
                        prompt.agent = config.get("agent", "")
                        prompt.model = config.get("model", "")
                        prompt.priority = config.get("priority", "")
                        prompt.estimated_effort = config.get("estimated_effort", "")
                        prompt.dependencies = config.get("dependencies", [])
                except yaml.YAMLError as e:
                    prompt.validation_errors.append(f"Invalid YAML: {e}")
            
            # Extract objective
            obj_match = re.search(r"## Objective\s+(.+?)(?=\n##|\Z)", content, re.DOTALL)
            if obj_match:
                prompt.objective = obj_match.group(1).strip()
                
            return prompt
            
        except Exception as e:
            return None
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all discovered prompts"""
        results = {
            "total_prompts": len(self.prompts),
            "valid_prompts": 0,
            "invalid_prompts": 0,
            "prompts_by_phase": {},
            "validation_errors": [],
            "dependency_graph": {}
        }
        
        # Group by phase
        for prompt_id, prompt in self.prompts.items():
            phase = prompt.phase
            if phase not in results["prompts_by_phase"]:
                results["prompts_by_phase"][phase] = []
            results["prompts_by_phase"][phase].append(prompt_id)
            
            # Build dependency graph
            results["dependency_graph"][prompt_id] = prompt.dependencies
        
        # Validate each prompt
        for prompt_id, prompt in self.prompts.items():
            errors = self._validate_prompt(prompt)
            
            if errors:
                results["invalid_prompts"] += 1
                results["validation_errors"].extend(errors)
            else:
                results["valid_prompts"] += 1
        
        # Validate dependency chain
        dep_errors = self._validate_dependencies()
        results["validation_errors"].extend(dep_errors)
        
        return results
    
    def _validate_prompt(self, prompt: PromptConfig) -> List[str]:
        """Validate a single prompt"""
        errors = list(prompt.validation_errors)
        
        # Validate phase
        if prompt.phase not in self.VALID_PHASES:
            errors.append(f"[{prompt.prompt_id}] Invalid phase: {prompt.phase}")
        
        # Validate priority
        if prompt.priority and prompt.priority not in self.VALID_PRIORITIES:
            errors.append(f"[{prompt.prompt_id}] Invalid priority: {prompt.priority}")
        
        # Validate agent reference
        if not prompt.agent:
            errors.append(f"[{prompt.prompt_id}] Missing agent reference")
        
        # Validate objective
        if not prompt.objective:
            errors.append(f"[{prompt.prompt_id}] Missing objective")
        
        return errors
    
    def _validate_dependencies(self) -> List[str]:
        """Validate the dependency chain between prompts"""
        errors = []
        
        for prompt_id, deps in self.prompts.items():
            prompt = self.prompts[prompt_id]
            for dep_id in prompt.dependencies:
                if dep_id not in self.prompts:
                    errors.append(f"[{prompt_id}] Missing dependency: {dep_id}")
                else:
                    dep = self.prompts[dep_id]
                    # Dependency should be in same or earlier phase
                    if dep.phase > prompt.phase:
                        errors.append(
                            f"[{prompt_id}] Dependency {dep_id} is in a later phase"
                        )
        
        return errors


class SkillValidator:
    """Validates skill configurations"""
    
    REQUIRED_SKILLS = [
        "flask-api",
        "react-components",
        "template-engine",
        "multi-tenant-db",
        "airflow-dags"
    ]
    
    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: Dict[str, SkillConfig] = {}
        
    def discover_skills(self) -> List[SkillConfig]:
        """Discover all skills in the skills directory"""
        skills = []
        
        if not self.skills_dir.exists():
            return skills
            
        for dir_path in self.skills_dir.iterdir():
            if dir_path.is_dir():
                skill = SkillConfig(
                    name=dir_path.name,
                    dir_path=dir_path,
                    has_skill_file=(dir_path / "SKILL.md").exists()
                )
                skills.append(skill)
                self.skills[skill.name] = skill
                
        return skills
    
    def validate_all(self) -> Dict[str, Any]:
        """Validate all discovered skills"""
        results = {
            "total_skills": len(self.skills),
            "valid_skills": 0,
            "missing_required_skills": [],
            "skills_without_definition": []
        }
        
        # Check for required skills
        for required in self.REQUIRED_SKILLS:
            if required not in self.skills:
                results["missing_required_skills"].append(required)
        
        # Validate each skill
        for name, skill in self.skills.items():
            if skill.has_skill_file:
                results["valid_skills"] += 1
            else:
                results["skills_without_definition"].append(name)
        
        return results


# ============================================================================
# Workflow Simulator
# ============================================================================

class WorkflowSimulator:
    """Simulates multi-agent workflow execution"""
    
    def __init__(
        self,
        agent_validator: AgentValidator,
        prompt_validator: PromptValidator
    ):
        self.agents = agent_validator.agents
        self.prompts = prompt_validator.prompts
        self.executions: List[WorkflowExecution] = []
        
    def create_phase_workflow(self, phase: int) -> WorkflowExecution:
        """Create a workflow for a specific phase"""
        workflow = WorkflowExecution(phase=phase)
        
        # Get all prompts for this phase
        phase_prompts = [
            p for p in self.prompts.values()
            if p.phase == phase
        ]
        
        # Sort by prompt_id
        phase_prompts.sort(key=lambda p: p.prompt_id)
        
        # Create workflow steps
        for i, prompt in enumerate(phase_prompts, 1):
            step = WorkflowStep(
                step_number=i,
                agent=prompt.agent,
                prompt_id=prompt.prompt_id,
                description=prompt.objective[:100] if prompt.objective else "",
                dependencies=prompt.dependencies
            )
            workflow.steps.append(step)
        
        return workflow
    
    def simulate_workflow(self, workflow: WorkflowExecution) -> Dict[str, Any]:
        """Simulate the execution of a workflow"""
        results = {
            "phase": workflow.phase,
            "total_steps": len(workflow.steps),
            "execution_order": [],
            "agent_distribution": {},
            "dependency_resolution": [],
            "issues": []
        }
        
        completed: Set[str] = set()
        execution_order: List[Dict[str, Any]] = []
        
        # Process steps in dependency order
        remaining = list(workflow.steps)
        iteration = 0
        max_iterations = len(remaining) * 2  # Prevent infinite loops
        
        while remaining and iteration < max_iterations:
            iteration += 1
            ready_steps = []
            
            for step in remaining:
                # Check if all dependencies are met
                deps_met = all(dep in completed for dep in step.dependencies)
                if deps_met:
                    ready_steps.append(step)
            
            if not ready_steps:
                # Circular dependency or unmet dependencies
                results["issues"].append(
                    f"Cannot resolve dependencies for: {[s.prompt_id for s in remaining]}"
                )
                break
            
            # Execute ready steps (could be parallel in real execution)
            for step in ready_steps:
                execution_entry = {
                    "step": step.step_number,
                    "prompt_id": step.prompt_id,
                    "agent": step.agent,
                    "dependencies": step.dependencies,
                    "status": "completed"
                }
                execution_order.append(execution_entry)
                completed.add(step.prompt_id)
                remaining.remove(step)
                
                # Track agent distribution
                agent = step.agent
                if agent not in results["agent_distribution"]:
                    results["agent_distribution"][agent] = 0
                results["agent_distribution"][agent] += 1
        
        results["execution_order"] = execution_order
        results["completed_steps"] = len(completed)
        
        return results
    
    def validate_agent_availability(self, workflow: WorkflowExecution) -> List[str]:
        """Validate that all required agents are available for a workflow"""
        issues = []
        
        for step in workflow.steps:
            agent_name = step.agent.replace("@", "") + "-agent"
            if agent_name not in self.agents and step.agent != "@orchestrator":
                issues.append(f"Agent not found for step {step.prompt_id}: {step.agent}")
        
        return issues


# ============================================================================
# Test Runner
# ============================================================================

class MultiAgentWorkflowTest:
    """Main test runner for the multi-agent workflow"""
    
    def __init__(self):
        self.agent_validator = AgentValidator(AGENTS_DIR)
        self.prompt_validator = PromptValidator(PROMPTS_DIR)
        self.skill_validator = SkillValidator(SKILLS_DIR)
        self.workflow_simulator: Optional[WorkflowSimulator] = None
        
    def run_all_tests(self) -> Dict[str, Any]:
        """Run all validation tests"""
        results = {
            "framework_structure": self._test_framework_structure(),
            "agents": self._test_agents(),
            "prompts": self._test_prompts(),
            "skills": self._test_skills(),
            "workflow_simulation": self._test_workflow_simulation(),
            "summary": {}
        }
        
        # Calculate summary
        all_passed = True
        for category, category_results in results.items():
            if category == "summary":
                continue
            if isinstance(category_results, dict) and not category_results.get("passed", True):
                all_passed = False
        
        results["summary"] = {
            "all_tests_passed": all_passed,
            "timestamp": __import__("datetime").datetime.now().isoformat()
        }
        
        return results
    
    def _test_framework_structure(self) -> Dict[str, Any]:
        """Test that the framework directory structure is correct"""
        results = {
            "passed": True,
            "checks": []
        }
        
        required_paths = [
            (GITHUB_DIR, "directory"),
            (AGENTS_DIR, "directory"),
            (PROMPTS_DIR, "directory"),
            (SKILLS_DIR, "directory"),
            (INSTRUCTIONS_DIR, "directory"),
            (GITHUB_DIR / "README.md", "file"),
            (AGENTS_DIR / "README.md", "file"),
            (AGENTS_DIR / "novasight-orchestrator.agent.md", "file"),
            (INSTRUCTIONS_DIR / "INSTRUCTIONS.md", "file"),
        ]
        
        for path, path_type in required_paths:
            exists = path.exists()
            check = {
                "path": str(path.relative_to(BASE_DIR)),
                "type": path_type,
                "exists": exists
            }
            results["checks"].append(check)
            
            if not exists:
                results["passed"] = False
        
        return results
    
    def _test_agents(self) -> Dict[str, Any]:
        """Test agent configurations"""
        agents = self.agent_validator.discover_agents()
        validation = self.agent_validator.validate_all()
        
        return {
            "passed": validation["invalid_agents"] == 0 and len(validation["missing_required_agents"]) == 0,
            "discovered": len(agents),
            "valid": validation["valid_agents"],
            "invalid": validation["invalid_agents"],
            "missing_required": validation["missing_required_agents"],
            "validation_errors": validation["validation_errors"][:10]  # Limit errors
        }
    
    def _test_prompts(self) -> Dict[str, Any]:
        """Test prompt configurations"""
        prompts = self.prompt_validator.discover_prompts()
        validation = self.prompt_validator.validate_all()
        
        return {
            "passed": validation["invalid_prompts"] == 0,
            "discovered": len(prompts),
            "valid": validation["valid_prompts"],
            "invalid": validation["invalid_prompts"],
            "by_phase": validation["prompts_by_phase"],
            "validation_errors": validation["validation_errors"][:10]
        }
    
    def _test_skills(self) -> Dict[str, Any]:
        """Test skill configurations"""
        skills = self.skill_validator.discover_skills()
        validation = self.skill_validator.validate_all()
        
        return {
            "passed": len(validation["missing_required_skills"]) == 0,
            "discovered": len(skills),
            "valid": validation["valid_skills"],
            "missing_required": validation["missing_required_skills"],
            "without_definition": validation["skills_without_definition"]
        }
    
    def _test_workflow_simulation(self) -> Dict[str, Any]:
        """Test workflow simulation for each phase"""
        self.workflow_simulator = WorkflowSimulator(
            self.agent_validator,
            self.prompt_validator
        )
        
        results = {
            "passed": True,
            "phases": {}
        }
        
        for phase in range(1, 7):
            workflow = self.workflow_simulator.create_phase_workflow(phase)
            
            if not workflow.steps:
                continue
                
            simulation = self.workflow_simulator.simulate_workflow(workflow)
            agent_issues = self.workflow_simulator.validate_agent_availability(workflow)
            
            phase_result = {
                "total_steps": simulation["total_steps"],
                "completed_steps": simulation["completed_steps"],
                "agent_distribution": simulation["agent_distribution"],
                "issues": simulation["issues"] + agent_issues
            }
            
            if phase_result["issues"]:
                results["passed"] = False
                
            results["phases"][f"phase_{phase}"] = phase_result
        
        return results


# ============================================================================
# Reporting
# ============================================================================

def print_test_report(results: Dict[str, Any]) -> None:
    """Print a formatted test report"""
    print("\n" + "=" * 80)
    print("  NOVASIGHT MULTI-AGENT WORKFLOW TEST REPORT")
    print("=" * 80 + "\n")
    
    # Framework Structure
    print("📁 FRAMEWORK STRUCTURE")
    print("-" * 40)
    fs = results["framework_structure"]
    print(f"   Status: {'✅ PASSED' if fs['passed'] else '❌ FAILED'}")
    for check in fs["checks"]:
        icon = "✓" if check["exists"] else "✗"
        print(f"   {icon} {check['path']}")
    print()
    
    # Agents
    print("🤖 AGENTS")
    print("-" * 40)
    agents = results["agents"]
    print(f"   Status: {'✅ PASSED' if agents['passed'] else '❌ FAILED'}")
    print(f"   Discovered: {agents['discovered']}")
    print(f"   Valid: {agents['valid']}")
    print(f"   Invalid: {agents['invalid']}")
    if agents["missing_required"]:
        print(f"   Missing: {', '.join(agents['missing_required'])}")
    if agents["validation_errors"]:
        print("   Errors:")
        for error in agents["validation_errors"]:
            print(f"     - {error}")
    print()
    
    # Prompts
    print("📋 PROMPTS")
    print("-" * 40)
    prompts = results["prompts"]
    print(f"   Status: {'✅ PASSED' if prompts['passed'] else '❌ FAILED'}")
    print(f"   Discovered: {prompts['discovered']}")
    print(f"   Valid: {prompts['valid']}")
    print(f"   By Phase:")
    for phase, count in sorted(prompts.get("by_phase", {}).items()):
        print(f"     Phase {phase}: {len(count)} prompts")
    if prompts["validation_errors"]:
        print("   Errors:")
        for error in prompts["validation_errors"][:5]:
            print(f"     - {error}")
    print()
    
    # Skills
    print("🔧 SKILLS")
    print("-" * 40)
    skills = results["skills"]
    print(f"   Status: {'✅ PASSED' if skills['passed'] else '❌ FAILED'}")
    print(f"   Discovered: {skills['discovered']}")
    print(f"   Valid: {skills['valid']}")
    if skills["missing_required"]:
        print(f"   Missing: {', '.join(skills['missing_required'])}")
    print()
    
    # Workflow Simulation
    print("🔄 WORKFLOW SIMULATION")
    print("-" * 40)
    wf = results["workflow_simulation"]
    print(f"   Status: {'✅ PASSED' if wf['passed'] else '❌ FAILED'}")
    for phase_name, phase_data in wf.get("phases", {}).items():
        phase_num = phase_name.split("_")[1]
        print(f"   Phase {phase_num}:")
        print(f"     Steps: {phase_data['total_steps']}")
        print(f"     Completed: {phase_data['completed_steps']}")
        if phase_data["agent_distribution"]:
            agents_str = ", ".join(
                f"{a}: {c}" for a, c in phase_data["agent_distribution"].items()
            )
            print(f"     Agents: {agents_str}")
        if phase_data["issues"]:
            for issue in phase_data["issues"]:
                print(f"     ⚠️  {issue}")
    print()
    
    # Summary
    print("=" * 80)
    summary = results["summary"]
    if summary["all_tests_passed"]:
        print("  🎉 ALL TESTS PASSED!")
    else:
        print("  ❌ SOME TESTS FAILED")
    print(f"  Timestamp: {summary['timestamp']}")
    print("=" * 80 + "\n")


# ============================================================================
# Main Entry Point
# ============================================================================

def main():
    """Main entry point for the test suite"""
    print("\n🚀 Starting NovaSight Multi-Agent Workflow Tests...\n")
    
    tester = MultiAgentWorkflowTest()
    results = tester.run_all_tests()
    
    print_test_report(results)
    
    # Return exit code
    return 0 if results["summary"]["all_tests_passed"] else 1


if __name__ == "__main__":
    exit(main())

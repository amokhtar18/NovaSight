# GitHub Copilot Agent File Format

This document explains the required format for agent files to be recognized by GitHub Copilot.

## File Structure

Each agent file must:
1. Be located in `.github/agents/`
2. Use the `.agent.md` extension
3. Start with YAML front matter

## Required YAML Front Matter

```yaml
---
name: "Agent Name"
description: "Brief description of agent capabilities"
tools: ['vscode/vscodeAPI', 'vscode/extensions', 'read', 'edit', 'search', 'web']
---
```

### Fields

- **name** (required): The display name shown in GitHub Copilot
- **description** (required): Brief description of what the agent does
- **tools** (required): Array of tools the agent can use

### Common Tools

- `vscode/vscodeAPI` - VS Code API integration
- `vscode/extensions` - VS Code extensions
- `read` - Read files and directories
- `edit` - Edit files
- `search` - Search codebase
- `web` - Access web resources

## Example Agent File

```markdown
---
name: "Backend Agent"
description: "Flask API, SQLAlchemy models, business logic, authentication"
tools: ['vscode/vscodeAPI', 'vscode/extensions', 'read', 'edit', 'search', 'web']
---

# Backend Agent

## 🎯 Role

You are the **Backend Agent** for NovaSight...
```

## Migration Notes

Previously, agent files used a markdown code block for configuration:

```markdown
## ⚙️ Configuration

\```yaml
preferred_model: opus 4.5
required_tools:
  - read_file
  - create_file
\```
```

This format was **not recognized** by GitHub Copilot. All agent files have been updated to use proper YAML front matter.

## Verification

To verify an agent file is properly formatted:

1. Check it starts with `---` on line 1
2. Contains `name`, `description`, and `tools` fields
3. Ends front matter with `---`
4. Has `.agent.md` extension

## All Agents

The following agents are now properly configured:

- ✅ admin-agent.agent.md
- ✅ ai-agent.agent.md
- ✅ backend-agent.agent.md
- ✅ dashboard-agent.agent.md
- ✅ data-sources-agent.agent.md
- ✅ dbt-agent.agent.md
- ✅ frontend-agent.agent.md
- ✅ infrastructure-agent.agent.md
- ✅ novasight-orchestrator.agent.md
- ✅ orchestration-agent.agent.md
- ✅ plan.agent.md
- ✅ security-agent.agent.md
- ✅ template-engine-agent.agent.md
- ✅ testing-agent.agent.md
- ✅ Ultimate-Transparent-Thinking-Beast-Mode.agent.md

## References

- [GitHub Copilot Custom Instructions Documentation](https://docs.github.com/en/copilot)
- [Agent File Examples in this Repository](./)

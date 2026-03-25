---
description: Get help with the session-browser plugin
allowed-tools: []
---

# Session Browser Help

## Commands

### /sessions [search] [options]

Browse and resume sessions with optional filtering.

| Option | Short | Description | Example |
|--------|-------|-------------|---------|
| search | - | Free text search | `/sessions auth bug` |
| --project | -p | Filter by project path | `--project api` |
| --branch | -b | Filter by git branch | `--branch main` |
| --since | -s | After date (YYYY-MM-DD) | `--since 2026-01-01` |
| --until | -u | Before date | `--until 2026-01-31` |
| --deep | -d | Search inside conversation content | `/sessions kafka --deep` |
| --limit | -l | Max results (default 20) | `--limit 50` |

## Examples

```bash
# Recent sessions
/sessions

# Search for topic
/sessions authentication

# Filter by project
/sessions --project claude-skills

# Combine filters
/sessions hook --project skills --branch main --since 2026-01-20

# Deep search - find sessions where "kafka" was discussed anywhere in the conversation
/sessions kafka --deep
```

## How Resuming Works

When you select a session, you'll get a command like:

```bash
cd "/path/to/project" && claude --resume abc123-def456
```

This starts a NEW Claude instance with the previous conversation loaded.
Your current session continues separately.

## Session Storage

Sessions are stored at: `~/.claude/projects/<encoded-path>/sessions-index.json`

Each session has:
- **sessionId**: UUID for resuming
- **summary**: Auto-generated summary
- **projectPath**: Original directory
- **gitBranch**: Branch at session start
- **modified**: Last activity timestamp

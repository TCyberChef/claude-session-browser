---
description: Browse and resume Claude Code sessions from any project
argument-hint: "[search] [--deep] [--project PATH] [--branch NAME] [--since DATE] [--limit N]"
allowed-tools: ["Bash", "Read", "AskUserQuestion"]
---

# Session Browser

Browse and resume Claude Code sessions across all projects.

## Usage

When invoked, scan sessions and display results.

## Steps

### Step 1: Scan Sessions

Run the scanner with user's arguments:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session-scanner.py" "$ARGUMENTS"
```

Note: The search argument supports multi-word queries with OR matching. Passing `"block UI admin"` will match sessions containing "block" OR "ui" OR "admin".

Display the table output to the user.

### Step 2: Ask Which Session to Resume

After showing the table, use AskUserQuestion to let user select:

```json
{
  "questions": [{
    "question": "Which session would you like to resume?",
    "header": "Session #",
    "multiSelect": false,
    "options": [
      {"label": "Enter number", "description": "Type session number (1, 2, 3...)"},
      {"label": "Refine search", "description": "Add more filters"},
      {"label": "Cancel", "description": "Exit browser"}
    ]
  }]
}
```

### Step 3: Handle Selection

**If user enters a number (1-N):**

Get the resume command:
```bash
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/session-scanner.py" "$ARGUMENTS" --get <NUMBER>
```

Output the resume command for the user. The command includes `cd` to the original project directory, so it works from any terminal:
```
To resume this session, run:

cd "/path/to/project" && claude --resume <session-id>
```

Note: The user opens sessions from many different directories. The `cd` is critical - without it, resume will fail if the user is in a different directory than where the session was started.

**If "Refine search":** Ask what filters to add and re-run Step 1.

**If "Cancel":** Say "Session browser closed."

## Examples

User: `/sessions`
→ Show all recent sessions, ask which to resume

User: `/sessions auth --project api`
→ Show sessions matching "auth" in api projects

User: `/sessions --branch main --since 2026-01-20`
→ Show sessions on main branch from last week

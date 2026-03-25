# Claude Session Browser

**Find and resume any Claude Code session. Search across all projects, branches, and conversation content.**

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-1.1.0-green.svg)](.claude-plugin/plugin.json)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-yellow.svg)](scripts/session-scanner.py)
[![No Dependencies](https://img.shields.io/badge/dependencies-none-brightgreen.svg)](#)

---

```
/sessions redis --deep

Found 12 sessions, showing 5:

  # PROJECT                        DATE          MSGS BRANCH          SUMMARY / FIRST PROMPT
--------------------------------------------------------------------------------------------------------------
  1 ~/dev/my-api                   2026-03-24     192 main            Added caching layer with...
                                   >> ...switched from Memcached to Redis for session storage because we need pub/sub
  2 ~/dev/infra                    2026-03-22     380 feat/cache      Deploy Redis cluster to prod...
                                   >> ...Redis Sentinel vs Redis Cluster: Sentinel is simpler for HA but Cluster
  3 ~/dev/my-api                   2026-03-20     201 main            Fix connection pool exhaustion...
                                   >> ...the Redis connection pool was maxing out at 10 connections, bumped to 50
  4 ~/dev/backend                  2026-03-18     145 HEAD            Debug session timeout issue...
                                   >> ...Redis TTL was set to 1800s but the app expects 3600s, causing premature
  5 ~/dev/infra                    2026-03-15      98 main            Set up monitoring dashboards...
                                   >> ...added Grafana panels for Redis memory usage, connected clients, and hit rate
```

## Install

```
/plugin install TCyberChef/claude-session-browser
```

That's it. You now have `/sessions` available in every project.

## Usage

```bash
# List recent sessions across all projects
/sessions

# Search by topic (matches summaries and first prompts)
/sessions authentication

# Deep search - find sessions where a topic was discussed ANYWHERE in the conversation
/sessions kafka --deep

# Filter by project, branch, or date
/sessions --project api --branch main --since 2026-01-01

# Combine search with filters
/sessions nginx --deep --project devops --limit 50
```

Select a session number from the results and get a ready-to-run resume command:

```bash
cd "/home/user/dev/my-api" && claude --resume abc123-def456
```

## Features

- **Cross-project search** - scans all `~/.claude/projects/` in one shot
- **Deep content search** (`--deep`) - searches inside the actual conversation, not just metadata
- **Context snippets** - shows WHERE your search term was found in the conversation
- **Smart two-phase scan** - reads the fast index first, falls back to raw JSONL for unindexed sessions
- **Branch and date filters** - narrow down by git branch or date range
- **Instant resume** - outputs `cd + claude --resume` commands that work from any terminal
- **Zero dependencies** - pure Python stdlib, works everywhere Claude Code runs

## Options

| Flag | Short | Description | Example |
|------|-------|-------------|---------|
| `search` | | Free text search (OR matching) | `/sessions auth bug` |
| `--deep` | `-d` | Search inside conversation content | `/sessions kafka -d` |
| `--project` | `-p` | Filter by project path | `--project api` |
| `--branch` | `-b` | Filter by git branch | `--branch main` |
| `--since` | `-s` | Sessions after date | `--since 2026-01-01` |
| `--until` | `-u` | Sessions before date | `--until 2026-01-31` |
| `--limit` | `-l` | Max results (default 20) | `--limit 50` |
| `--json` | | Output as JSON | `--json` |

## How It Works

The scanner runs in two phases:

1. **Index scan** - reads `sessions-index.json` files for each project (fast, has summaries and metadata)
2. **JSONL scan** - scans raw `.jsonl` conversation files for sessions missing from the index

With `--deep`, indexed sessions also get their JSONL files searched when the search term isn't in metadata. The scanner extracts text from user and assistant messages (skipping tool calls and thinking blocks) and returns a snippet showing where the match was found.

Search uses OR matching: `/sessions auth nginx deploy` finds sessions containing "auth" OR "nginx" OR "deploy".

## Updating

```
/plugin update
```

---

Built by [@TCyberChef](https://github.com/TCyberChef)

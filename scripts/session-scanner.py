#!/usr/bin/env python3
"""
Session scanner for session-browser plugin.
Scans all Claude Code sessions using both the index AND raw JSONL files.
The index is fast but often stale; raw scanning catches everything.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict


def get_projects_dir() -> Path:
    return Path.home() / ".claude" / "projects"


def shorten_path(path: str, max_len: int = 30) -> str:
    home = str(Path.home())
    if path.startswith(home):
        path = "~" + path[len(home):]
    if len(path) <= max_len:
        return path
    half = (max_len - 3) // 2
    return path[:half] + "..." + path[-half:]


def decode_project_path(dir_name: str) -> str:
    """Convert encoded project dir name back to a path.
    e.g. '-Users-jane-dev-myapp' -> '/Users/jane/dev/myapp'
    """
    if dir_name.startswith("-"):
        return "/" + dir_name[1:].replace("-", "/")
    return dir_name


def parse_date(date_str: str) -> Optional[datetime]:
    if not date_str:
        return None
    try:
        return datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        return None


def load_sessions_index(index_path: Path) -> List[Dict]:
    try:
        with open(index_path, 'r') as f:
            data = json.load(f)
            return data.get("entries", [])
    except (json.JSONDecodeError, IOError):
        return []


def scan_jsonl_file(jsonl_path: Path, project_path: str) -> Optional[Dict]:
    """Extract session metadata from a raw JSONL file.
    Reads only the first ~50 lines for efficiency.
    """
    session_id = jsonl_path.stem
    first_prompt = ""
    git_branch = ""
    cwd = ""
    slug = ""
    first_ts = ""
    last_ts = ""
    msg_count = 0
    is_sidechain = False

    try:
        with open(jsonl_path, 'r') as f:
            for i, line in enumerate(f):
                if i > 80:
                    break
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                # Track sidechain
                if entry.get("isSidechain"):
                    is_sidechain = True
                    break

                # Extract metadata from any entry
                if not cwd and entry.get("cwd"):
                    cwd = entry["cwd"]
                if not git_branch and entry.get("gitBranch"):
                    git_branch = entry["gitBranch"]
                if not slug and entry.get("slug"):
                    slug = entry["slug"]

                # Track timestamps
                ts = entry.get("timestamp", "")
                if ts:
                    if not first_ts:
                        first_ts = ts
                    last_ts = ts

                # Count user messages and get first prompt
                entry_type = entry.get("type", "")
                msg = entry.get("message", {})
                if entry_type == "user" or msg.get("role") == "user":
                    msg_count += 1
                    if not first_prompt:
                        content = msg.get("content", "")
                        if isinstance(content, list):
                            for c in content:
                                if isinstance(c, dict) and c.get("type") == "text":
                                    first_prompt = c["text"][:200]
                                    break
                                elif isinstance(c, dict) and c.get("type") == "tool_result":
                                    # Skip tool results, look for the next text
                                    continue
                        elif isinstance(content, str):
                            first_prompt = content[:200]
                elif entry_type == "assistant" or msg.get("role") == "assistant":
                    msg_count += 1

        if is_sidechain:
            return None

        # Use file mtime as fallback for modified date
        file_mtime = datetime.fromtimestamp(jsonl_path.stat().st_mtime)
        modified = last_ts if last_ts else file_mtime.isoformat()

        # Use the cwd from the session, fall back to decoded project dir
        actual_project = cwd or project_path

        return {
            "sessionId": session_id,
            "projectPath": actual_project,
            "projectShort": shorten_path(actual_project),
            "summary": "",
            "summaryFull": "",
            "firstPrompt": first_prompt[:200] if first_prompt else "",
            "gitBranch": git_branch or "-",
            "slug": slug,
            "modified": modified,
            "modifiedDate": modified[:10],
            "messageCount": msg_count,
            "source": "jsonl",
        }

    except (IOError, OSError):
        return None


def scan_remaining_lines(jsonl_path: Path, session: dict) -> dict:
    """Count total messages by scanning remaining lines (fast, just counts types)."""
    count = session["messageCount"]
    try:
        with open(jsonl_path, 'r') as f:
            for i, line in enumerate(f):
                if i <= 80:
                    continue
                try:
                    entry = json.loads(line)
                    entry_type = entry.get("type", "")
                    msg = entry.get("message", {})
                    role = msg.get("role", "")
                    if entry_type in ("user", "assistant") or role in ("user", "assistant"):
                        count += 1
                    # Update last timestamp
                    ts = entry.get("timestamp", "")
                    if ts:
                        session["modified"] = ts
                        session["modifiedDate"] = ts[:10]
                except json.JSONDecodeError:
                    continue
    except (IOError, OSError):
        pass
    session["messageCount"] = count
    return session


def extract_text_from_entry(entry: dict) -> str:
    """Extract searchable text from a JSONL entry (user + assistant text only)."""
    msg = entry.get("message", {})
    content = msg.get("content", "")

    if isinstance(content, str):
        return content

    if isinstance(content, list):
        texts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                texts.append(block.get("text", ""))
        return " ".join(texts)

    return ""


def deep_search_jsonl(jsonl_path: Path, search_words: List[str],
                      max_snippets: int = 1) -> Optional[str]:
    """Search full JSONL conversation content for search words.
    Returns a snippet around the first match, or None.
    """
    try:
        with open(jsonl_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                except json.JSONDecodeError:
                    continue

                text = extract_text_from_entry(entry)
                if not text:
                    continue

                text_lower = text.lower()
                for word in search_words:
                    idx = text_lower.find(word)
                    if idx != -1:
                        start = max(0, idx - 40)
                        end = min(len(text), idx + len(word) + 80)
                        snippet = text[start:end].replace("\n", " ").strip()
                        if start > 0:
                            snippet = "..." + snippet
                        if end < len(text):
                            snippet = snippet + "..."
                        return snippet
    except (IOError, OSError):
        pass
    return None


def matches_search(session: dict, search_words: List[str]) -> bool:
    """Check if session matches ANY of the search words."""
    if not search_words:
        return True
    haystack = " ".join([
        session.get("summary", ""),
        session.get("summaryFull", ""),
        session.get("firstPrompt", ""),
        session.get("projectPath", ""),
        session.get("gitBranch", ""),
        session.get("slug", ""),
    ]).lower()
    return any(word in haystack for word in search_words)


def matches_project(session: dict, project_filter: str) -> bool:
    if not project_filter:
        return True
    return project_filter.lower() in session.get("projectPath", "").lower()


def matches_branch(session: dict, branch_filter: str) -> bool:
    if not branch_filter:
        return True
    return branch_filter.lower() in session.get("gitBranch", "").lower()


def matches_date_range(session: dict, since: Optional[datetime],
                       until: Optional[datetime]) -> bool:
    modified_str = session.get("modified")
    if not modified_str:
        return True
    try:
        modified = datetime.fromisoformat(modified_str.replace("Z", "+00:00"))
        modified = modified.replace(tzinfo=None)
    except ValueError:
        return True

    if since and modified.date() < since.date():
        return False
    if until and modified.date() > until.date():
        return False
    return True


def scan_all_sessions(args: argparse.Namespace) -> dict:
    projects_dir = get_projects_dir()

    if not projects_dir.exists():
        return {"sessions": [], "total": 0, "shown": 0}

    # Parse search into words for OR matching
    search_words = []
    if args.search:
        search_words = [w.lower() for w in args.search.split() if len(w) >= 2]

    all_sessions = []
    indexed_ids = set()

    for project_dir in projects_dir.iterdir():
        if not project_dir.is_dir():
            continue

        project_path = decode_project_path(project_dir.name)

        # Phase 1: Load from index (has summaries, fast)
        index_path = project_dir / "sessions-index.json"
        if index_path.exists():
            for session in load_sessions_index(index_path):
                if session.get("isSidechain", False):
                    continue
                sid = session.get("sessionId", "")
                indexed_ids.add(sid)

                entry = {
                    "sessionId": sid,
                    "projectPath": session.get("projectPath", project_path),
                    "projectShort": shorten_path(
                        session.get("projectPath", project_path)),
                    "summary": (session.get("summary", "") or "")[:55],
                    "summaryFull": session.get("summary", ""),
                    "firstPrompt": (session.get("firstPrompt", "") or "")[:200],
                    "gitBranch": session.get("gitBranch", "") or "-",
                    "slug": "",
                    "modified": session.get("modified", ""),
                    "modifiedDate": session.get("modified", "")[:10],
                    "messageCount": session.get("messageCount", 0),
                    "source": "index",
                }

                if not matches_project(entry, args.project):
                    continue
                if not matches_branch(entry, args.branch):
                    continue
                if not matches_date_range(entry,
                                          parse_date(args.since),
                                          parse_date(args.until)):
                    continue

                # Metadata match first; if no match and --deep, search content
                if search_words and not matches_search(entry, search_words):
                    if args.deep:
                        jsonl_path = project_dir / f"{sid}.jsonl"
                        if jsonl_path.exists():
                            snippet = deep_search_jsonl(jsonl_path, search_words)
                            if snippet:
                                entry["contentMatch"] = snippet[:120]
                            else:
                                continue
                        else:
                            continue
                    else:
                        continue

                all_sessions.append(entry)

        # Phase 2: Scan raw JSONL files for unindexed sessions
        for jsonl_path in project_dir.glob("*.jsonl"):
            sid = jsonl_path.stem
            if sid in indexed_ids:
                continue

            session = scan_jsonl_file(jsonl_path, project_path)
            if session is None:
                continue

            # Quick filter before expensive full scan
            if not matches_project(session, args.project):
                continue
            if not matches_branch(session, args.branch):
                continue
            if not matches_date_range(session,
                                      parse_date(args.since),
                                      parse_date(args.until)):
                continue

            # If metadata doesn't match search, try content search
            if search_words and not matches_search(session, search_words):
                snippet = deep_search_jsonl(jsonl_path, search_words)
                if snippet:
                    session["contentMatch"] = snippet[:120]
                else:
                    continue

            # Count remaining messages for accuracy
            session = scan_remaining_lines(jsonl_path, session)
            all_sessions.append(session)

    total = len(all_sessions)
    all_sessions.sort(key=lambda s: s.get("modified", ""), reverse=True)

    limit = args.limit or 20
    shown = all_sessions[:limit]

    return {
        "sessions": shown,
        "total": total,
        "shown": len(shown)
    }


def format_table(result: dict) -> str:
    sessions = result.get("sessions", [])
    if not sessions:
        return "No sessions found matching your criteria."

    lines = []
    lines.append(
        f"Found {result['total']} sessions, showing {result['shown']}:\n")

    lines.append(
        f"{'#':>3} {'PROJECT':<30} {'DATE':<12} {'MSGS':>5} "
        f"{'BRANCH':<15} {'SUMMARY / FIRST PROMPT'}")
    lines.append("-" * 110)

    for i, s in enumerate(sessions, 1):
        project = s.get("projectShort", "")[:30]
        date = s.get("modifiedDate", "")
        msgs = str(s.get("messageCount", 0))
        branch = s.get("gitBranch", "-")[:15]
        # Prefer summary, fall back to first prompt, then content match
        content_match = s.get("contentMatch", "")
        display = s.get("summary", "") or s.get("firstPrompt", "")
        display = display.replace("\n", " ")[:50]
        slug = s.get("slug", "")
        if slug:
            display = f"[{slug[:20]}] {display}"[:50]
        lines.append(
            f"{i:>3} {project:<30} {date:<12} {msgs:>5} "
            f"{branch:<15} {display}")
        if content_match:
            lines.append(f"{'':>3} {'':>30} >> {content_match[:90]}")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Scan Claude Code sessions")
    parser.add_argument("search", nargs="?", default="",
                        help="Search text (multi-word, OR matching)")
    parser.add_argument("--project", "-p", default="",
                        help="Filter by project path")
    parser.add_argument("--branch", "-b", default="",
                        help="Filter by git branch")
    parser.add_argument("--since", "-s", default="",
                        help="Sessions after date (YYYY-MM-DD)")
    parser.add_argument("--until", "-u", default="",
                        help="Sessions before date (YYYY-MM-DD)")
    parser.add_argument("--limit", "-l", type=int, default=20,
                        help="Maximum sessions to return")
    parser.add_argument("--deep", "-d", action="store_true",
                        help="Search inside conversation content (slower)")
    parser.add_argument("--json", action="store_true",
                        help="Output as JSON")
    parser.add_argument("--get", "-g", type=int,
                        help="Get resume command for session N")

    args = parser.parse_args()
    result = scan_all_sessions(args)

    if args.get:
        sessions = result.get("sessions", [])
        if 1 <= args.get <= len(sessions):
            s = sessions[args.get - 1]
            cmd = f'cd "{s["projectPath"]}" && claude --resume {s["sessionId"]}'
            print(cmd)
        else:
            print(f"Invalid session number. Valid range: 1-{len(sessions)}",
                  file=sys.stderr)
            sys.exit(1)
    elif args.json:
        print(json.dumps(result, indent=2))
    else:
        print(format_table(result))


if __name__ == "__main__":
    main()

import os
import re
import subprocess
import tempfile
import time
from pathlib import Path

from mcp.server.fastmcp import FastMCP

# --- Configuration (all overridable via environment) ---
WIKI_SOURCE_DIR = os.environ.get("WIKI_SOURCE_DIR", "")
WIKI_REPO_URL = os.environ.get(
    "WIKI_REPO_URL", "https://github.com/Pd011161/wiki_source.git"
)
WIKI_BRANCH = os.environ.get("WIKI_BRANCH", "use")
WIKI_REVIEWER = os.environ.get("WIKI_REVIEWER", "Pd011161")  # GitHub username to request review from
WIKI_REVIEWER_EMAIL = os.environ.get("WIKI_REVIEWER_EMAIL", "c.predee@gmail.com")
WIKI_AUTO_PULL = os.environ.get("WIKI_AUTO_PULL", "1") != "0"

mcp = FastMCP(
    "wiki-mcp",
    instructions=(
        "Company LLM Wiki knowledge base. Call wiki_index first to see all available "
        "pages and their relationships, then wiki_read to read specific pages. "
        "Use wiki_search to find content across pages. "
        "To change the wiki, use wiki_edit — it opens a pull request for human review "
        "and never modifies the shared wiki directly."
    ),
)


def _get_wiki_dir() -> Path:
    """Resolve the wiki_source directory, cloning it on first use if needed.

    Resolution order:
      1. WIKI_SOURCE_DIR if set (cloned there if it doesn't exist yet)
      2. a sibling ../wiki_source next to this repo (manual / side-by-side clone)
      3. a per-user cache directory, auto-cloned from WIKI_REPO_URL

    This lets the server work with zero manual setup (uvx / plugin) while still
    honoring an existing local clone.
    """
    if WIKI_SOURCE_DIR:
        p = Path(WIKI_SOURCE_DIR).expanduser()
    else:
        sibling = Path(__file__).resolve().parents[3] / "wiki_source"
        p = sibling if sibling.is_dir() else (Path.home() / ".cache" / "wiki-mcp" / "wiki_source")

    if not (p / ".git").is_dir():
        if p.exists() and any(p.iterdir()):
            raise FileNotFoundError(
                f"{p} exists but is not a git clone of the wiki. "
                f"Remove it or set WIKI_SOURCE_DIR to a valid clone."
            )
        p.parent.mkdir(parents=True, exist_ok=True)
        res = subprocess.run(
            ["git", "clone", "--branch", WIKI_BRANCH, WIKI_REPO_URL, str(p)],
            capture_output=True, text=True,
        )
        if res.returncode != 0:
            raise FileNotFoundError(
                f"Could not clone the wiki from {WIKI_REPO_URL} (branch '{WIKI_BRANCH}').\n"
                f"{res.stderr.strip()}\n"
                f"If the repository is private, run 'gh auth login' or set up git "
                f"credentials, or set WIKI_SOURCE_DIR to an existing local clone."
            )
    return p


def _git(*args: str, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        check=check,
    )


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug[:40] or "edit"


# --- Read tools ---


@mcp.tool()
def wiki_index() -> str:
    """Get the wiki table of contents (index.md). Always call this first to discover available pages and their relationships."""
    wiki_dir = _get_wiki_dir()
    index_file = wiki_dir / "index.md"
    if not index_file.exists():
        return "Error: index.md not found in wiki_source."
    return index_file.read_text(encoding="utf-8")


@mcp.tool()
def wiki_read(filename: str) -> str:
    """Read a specific wiki page by filename. Use wiki_index first to find available filenames.

    Args:
        filename: The markdown filename (e.g. 'concept-rag.md' or 'entity-one7-ai.md')
    """
    wiki_dir = _get_wiki_dir()
    safe_name = Path(filename).name
    file_path = wiki_dir / safe_name
    if not file_path.exists():
        available = sorted(f.name for f in wiki_dir.glob("*.md"))
        return f"Error: '{safe_name}' not found. Available files:\n" + "\n".join(available)
    return file_path.read_text(encoding="utf-8")


@mcp.tool()
def wiki_search(query: str) -> str:
    """Search across all wiki pages for a keyword or phrase. Returns matching excerpts with filenames.

    Args:
        query: The search term (case-insensitive)
    """
    wiki_dir = _get_wiki_dir()
    pattern = re.compile(re.escape(query), re.IGNORECASE)
    results = []

    for md_file in sorted(wiki_dir.glob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        matches = list(pattern.finditer(content))
        if not matches:
            continue

        title_match = re.match(r"^#\s+(.+)", content)
        title = title_match.group(1) if title_match else md_file.stem

        excerpts = []
        lines = content.split("\n")
        matched_lines = set()
        for m in matches:
            line_num = content[: m.start()].count("\n")
            if line_num in matched_lines:
                continue
            matched_lines.add(line_num)
            start = max(0, line_num - 1)
            end = min(len(lines), line_num + 2)
            excerpt = "\n".join(lines[start:end]).strip()
            excerpts.append(excerpt)
            if len(excerpts) >= 3:
                break

        results.append(
            f"### {title} ({md_file.name})\n"
            + f"{len(matches)} match(es)\n\n"
            + "\n---\n".join(excerpts)
        )

        if len(results) >= 10:
            break

    if not results:
        return f"No results found for '{query}'."

    return f"Found matches in {len(results)} page(s):\n\n" + "\n\n".join(results)


# --- Sync tool ---


@mcp.tool()
def wiki_sync() -> str:
    """Pull the latest wiki changes from the shared repository so you are working with up-to-date content."""
    wiki_dir = _get_wiki_dir()
    try:
        _git("fetch", "origin", WIKI_BRANCH, cwd=wiki_dir)
        result = _git("pull", "--ff-only", "origin", WIKI_BRANCH, cwd=wiki_dir, check=False)
    except FileNotFoundError:
        return "Error: git is not installed or not on PATH."
    if result.returncode != 0:
        return (
            f"Could not fast-forward '{WIKI_BRANCH}'. Local copy may have diverged.\n"
            f"{result.stdout}\n{result.stderr}".strip()
        )
    out = result.stdout.strip()
    return f"Synced with origin/{WIKI_BRANCH}.\n{out}" if out else f"Already up to date with origin/{WIKI_BRANCH}."


# --- Edit tool ---


@mcp.tool()
def wiki_edit(filename: str, content: str, summary: str) -> str:
    """Propose a change to a wiki page by opening a pull request for human review.

    This NEVER modifies the shared wiki directly. It creates a branch, commits the
    new content, pushes it, and opens a PR. A human must review and merge it.

    Args:
        filename: The markdown filename to create or overwrite (e.g. 'concept-rag.md')
        content: The full new content of the file
        summary: A short description of the change, used as the commit message and PR title
    """
    wiki_dir = _get_wiki_dir()
    safe_name = Path(filename).name
    if not safe_name.endswith(".md"):
        return "Error: filename must end with .md"

    if subprocess.run(["which", "gh"], capture_output=True).returncode != 0:
        return (
            "Error: GitHub CLI (gh) is not installed, which is required to open a pull "
            "request. Install it from https://cli.github.com/ and run 'gh auth login', "
            "or ask a teammate to apply this change."
        )

    branch = f"wiki-edit/{_slugify(summary)}-{int(time.time())}"
    worktree = Path(tempfile.mkdtemp(prefix="wiki-edit-"))

    try:
        # Base the change on the latest reviewed branch, isolated in a worktree
        # so the user's working clone is never disturbed.
        _git("fetch", "origin", WIKI_BRANCH, cwd=wiki_dir)
        _git(
            "worktree", "add", "-b", branch, str(worktree),
            f"origin/{WIKI_BRANCH}", cwd=wiki_dir,
        )

        (worktree / safe_name).write_text(content, encoding="utf-8")

        _git("add", safe_name, cwd=worktree)
        diff_check = _git("diff", "--cached", "--quiet", cwd=worktree, check=False)
        if diff_check.returncode == 0:
            return f"No changes: '{safe_name}' already matches the proposed content."

        _git("commit", "-m", summary, cwd=worktree)
        _git("push", "-u", "origin", branch, cwd=worktree)

        body = (
            f"{summary}\n\n"
            f"---\n"
            f"🔍 **Approver:** {WIKI_REVIEWER_EMAIL}\n"
            f"🚫 **ต้องให้คนเป็นคน Approve เท่านั้น — ห้าม Approve / Merge เอง เด็ดขาด**\n"
            f"(Must be reviewed and approved by a human **other than the author**. "
            f"Never self-approve or self-merge.)\n\n"
            f"_Opened automatically by wiki-mcp._"
        )
        pr = subprocess.run(
            [
                "gh", "pr", "create",
                "--base", WIKI_BRANCH,
                "--head", branch,
                "--title", summary,
                "--body", body,
            ],
            cwd=str(worktree), capture_output=True, text=True,
        )
        if pr.returncode != 0:
            return (
                f"Branch '{branch}' was pushed, but opening the PR failed:\n"
                f"{pr.stderr.strip()}\n\n"
                f"You can open it manually on GitHub."
            )

        pr_url = pr.stdout.strip()

        # Request a reviewer as a separate, non-fatal step: GitHub rejects
        # self-review and unknown collaborators, but the PR itself must still stand.
        reviewer_note = ""
        if WIKI_REVIEWER:
            req = subprocess.run(
                ["gh", "pr", "edit", pr_url, "--add-reviewer", WIKI_REVIEWER],
                cwd=str(worktree), capture_output=True, text=True,
            )
            if req.returncode == 0:
                reviewer_note = f" Review requested from @{WIKI_REVIEWER}."
            else:
                reviewer_note = (
                    f" (Could not request @{WIKI_REVIEWER} as reviewer — "
                    f"they may be the PR author or not a collaborator.)"
                )

        return (
            f"✅ Pull request opened for '{safe_name}'.\n{pr_url}\n\n"
            f"Approver: {WIKI_REVIEWER_EMAIL}.{reviewer_note}\n"
            f"⚠️ A human other than the author must approve and merge — never self-approve."
        )
    except subprocess.CalledProcessError as e:
        return f"Git error: {e.stderr or e.stdout or str(e)}".strip()
    finally:
        _git("worktree", "remove", "--force", str(worktree), cwd=wiki_dir, check=False)


def _auto_pull() -> None:
    if not WIKI_AUTO_PULL:
        return
    try:
        wiki_dir = _get_wiki_dir()
        _git("pull", "--ff-only", "origin", WIKI_BRANCH, cwd=wiki_dir, check=False)
    except Exception:
        pass  # best-effort; never block startup on a failed sync


def main():
    _auto_pull()
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()

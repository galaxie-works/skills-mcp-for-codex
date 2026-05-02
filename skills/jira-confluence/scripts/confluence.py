#!/usr/bin/env -S uv run --script
# /// script
# dependencies = [
#   "httpx>=0.27",
#   "httpx-sse>=0.4",
#   "keyring>=25.0",
#   "pyyaml>=6.0",
#   "pyobjc-framework-Security>=10.0; sys_platform == 'darwin'",
#   "pyobjc-framework-LocalAuthentication>=10.0; sys_platform == 'darwin'",
# ]
# requires-python = ">=3.12"
# ///
"""
Confluence API operations script.

Uses MCP client to communicate with Atlassian MCP server.

Commands:
    get <PAGE_ID>         - Fetch a page with content
    search <CQL>          - Search pages using CQL
    children <PAGE_ID>    - Get all descendant pages
    spaces                - List Confluence spaces
    tree <PAGE_ID> [...]  - Download page tree(s) with nested folders
    export <CQL>          - Export pages to yaml/json/markdown files
    rovo <QUERY>          - Search Confluence pages using Rovo
"""

import argparse
import html
import json
import os
import re
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse, parse_qs

# Add parent directory to path for common module
sys.path.insert(0, str(Path(__file__).parent))

import yaml

from common import (
    get_cloud_id,
    yaml_output,
    error_output,
    parse_mcp_result,
    mcp_client_context,
    command_handler,
    call_mcp_with_retry,
)

# ---------------------------------------------------------------------------
# Configuration Constants
# ---------------------------------------------------------------------------
DEFAULT_DELAY = 0.5
MAX_DELAY = 10.0
BACKOFF_FACTOR = 2.0
SUCCESS_THRESHOLD = 5
MAX_RETRIES = 3
MAX_CONNECTION_RETRIES = 5
DEFAULT_PER_PAGE = 25
DEFAULT_MAX_RESULTS = 500

FORMAT_EXTENSIONS = {"yaml": "yaml", "json": "json", "markdown": "md"}


# ---------------------------------------------------------------------------
# Data Classes
# ---------------------------------------------------------------------------
@dataclass
class RateLimitState:
    """State for adaptive rate limiting."""
    delay: float
    min_delay: float
    max_delay: float = MAX_DELAY
    backoff_factor: float = BACKOFF_FACTOR
    success_count: int = 0
    success_threshold: int = SUCCESS_THRESHOLD


@dataclass
class DownloadStats:
    """Statistics for tree download operations."""
    pages_downloaded: int = 0
    pages_failed: int = 0


@dataclass
class TreeState:
    """State tracking for tree download operations."""
    downloaded_ids: set = field(default_factory=set)
    id_to_path: dict = field(default_factory=dict)
    toc_entries: list = field(default_factory=list)  # [(depth, title, path)]


# ---------------------------------------------------------------------------
# Rate Limiting
# ---------------------------------------------------------------------------
class AdaptiveRateLimiter:
    """Handles adaptive rate limiting with exponential backoff."""

    def __init__(self, initial_delay: float = DEFAULT_DELAY):
        self.state = RateLimitState(
            delay=initial_delay,
            min_delay=initial_delay
        )

    def wait(self):
        """Apply current rate limit delay."""
        if self.state.delay > 0:
            time.sleep(self.state.delay)

    def on_success(self):
        """Decrease delay after consecutive successes."""
        self.state.success_count += 1
        if self.state.success_count >= self.state.success_threshold:
            self.state.delay = max(self.state.min_delay, self.state.delay / 1.5)
            self.state.success_count = 0

    def on_failure(self):
        """Increase delay on failure (exponential backoff)."""
        self.state.delay = min(self.state.max_delay, self.state.delay * self.state.backoff_factor)
        self.state.success_count = 0


# ---------------------------------------------------------------------------
# Utility Functions
# ---------------------------------------------------------------------------
def html_to_text(html_content: str) -> str:
    """Convert HTML content to plain text."""
    if not html_content:
        return ""

    # Remove script and style elements
    text = re.sub(r"<script[^>]*>.*?</script>", "", html_content, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)

    # Convert common elements to text equivalents
    text = re.sub(r"<br\s*/?>", "\n", text)
    text = re.sub(r"</p>", "\n\n", text)
    text = re.sub(r"</div>", "\n", text)
    text = re.sub(r"</li>", "\n", text)
    text = re.sub(r"<li[^>]*>", "- ", text)
    text = re.sub(r"<h[1-6][^>]*>", "\n## ", text)
    text = re.sub(r"</h[1-6]>", "\n", text)

    # Remove all remaining HTML tags
    text = re.sub(r"<[^>]+>", "", text)

    # Decode HTML entities
    text = html.unescape(text)

    # Clean up whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def extract_cursor_from_links(result: dict) -> str | None:
    """Extract pagination cursor from _links.next URL."""
    links = result.get("_links", {})
    next_url = links.get("next")
    if not next_url:
        return None
    parsed = urlparse(next_url)
    params = parse_qs(parsed.query)
    cursor_list = params.get("cursor", [])
    return cursor_list[0] if cursor_list else None


def search_cql_paginated(
    client, cloud_id: str, cql: str, max_results: int = 500, per_page: int = 25
) -> tuple[list, int]:
    """Fetch results from CQL search with cursor pagination.

    Returns:
        (results_list, total_size) - list of search results and total available count
    """
    all_results = []
    cursor = None
    total_size = 0

    while len(all_results) < max_results:
        params = {
            "cloudId": cloud_id,
            "cql": cql,
            "limit": min(per_page, max_results - len(all_results)),
        }
        if cursor:
            params["cursor"] = cursor

        result = client.call_tool("searchConfluenceUsingCql", params)
        result, err = parse_mcp_result(result)
        if err:
            break

        results = result.get("results", [])
        all_results.extend(results)
        total_size = result.get("totalSize", len(all_results))

        # Get next cursor
        cursor = extract_cursor_from_links(result)
        if not cursor or not results:
            break

    return all_results, total_size


def format_page(page: dict, include_content: bool = True) -> dict:
    """Format page data for YAML output."""
    result = {
        "id": page.get("id"),
        "title": page.get("title"),
        "status": page.get("status"),
    }

    # Space info
    space = page.get("space") or page.get("spaceId")
    if isinstance(space, dict):
        result["space"] = {
            "key": space.get("key"),
            "name": space.get("name"),
        }
    elif space:
        result["space"] = {"id": space}

    # Parent page ID (from API v2)
    parent_id = page.get("parentId")
    if parent_id:
        result["parent_id"] = parent_id

    # Version/dates
    version = page.get("version")
    if version:
        if isinstance(version, dict):
            result["version"] = version.get("number")
            result["updated"] = version.get("createdAt")
            author = version.get("by")
            if author:
                result["author"] = {
                    "name": author.get("displayName"),
                    "account_id": author.get("accountId"),
                }
        else:
            result["version"] = version

    # Created date from history
    history = page.get("history")
    if history:
        result["created"] = history.get("createdDate")

    # Ancestors (parent pages)
    ancestors = page.get("ancestors", [])
    if ancestors:
        result["ancestors"] = [
            {"id": a.get("id"), "title": a.get("title")} for a in ancestors
        ]

    # Content - check both body.storage (v1 API) and body (v2 API)
    if include_content:
        body = page.get("body", {})
        if isinstance(body, dict):
            # v1 API format
            storage = body.get("storage", {})
            content_value = storage.get("value", "")
            # v2 API format
            if not content_value:
                atlas_doc = body.get("atlas_doc_format", {})
                content_value = atlas_doc.get("value", "")
        else:
            content_value = str(body) if body else ""

        if content_value:
            result["content"] = html_to_text(content_value)

    return result


def format_page_markdown(page: dict) -> str:
    """Format page as markdown document."""
    def get_user_name(user_obj):
        if not user_obj:
            return "N/A"
        if isinstance(user_obj, dict):
            return user_obj.get("name", "N/A")
        return str(user_obj)

    lines = [
        f"# {page.get('title', 'Untitled')}",
        "",
    ]

    # Metadata
    if page.get("id"):
        lines.append(f"**Page ID:** {page['id']}  ")
    if page.get("status"):
        lines.append(f"**Status:** {page['status']}  ")
    if page.get("space"):
        space = page["space"]
        if isinstance(space, dict):
            space_info = f"{space.get('name', '')} ({space.get('key', '')})" if space.get('name') else space.get('key', space.get('id', ''))
        else:
            space_info = str(space)
        lines.append(f"**Space:** {space_info}  ")
    if page.get("author"):
        lines.append(f"**Author:** {get_user_name(page.get('author'))}  ")
    if page.get("updated"):
        lines.append(f"**Updated:** {page['updated']}  ")
    if page.get("version"):
        lines.append(f"**Version:** {page['version']}  ")

    # Parent page info
    if page.get("parent_id"):
        lines.append(f"**Parent ID:** {page['parent_id']}  ")
    elif page.get("ancestors"):
        breadcrumb = " > ".join([a.get("title", a.get("id", "")) for a in page["ancestors"]])
        lines.append(f"**Path:** {breadcrumb}  ")

    lines.extend(["", "---", ""])

    # Content
    if page.get("content"):
        lines.append(page["content"])
    else:
        lines.append("_No content_")

    lines.append("")
    return "\n".join(lines)


@command_handler
def cmd_get(args):
    """Fetch a page with content via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "getConfluencePage",
            {
                "cloudId": cloud_id,
                "pageId": args.page_id,
                "includeBody": True,
            },
        )

        result, error_msg = parse_mcp_result(result)
        if error_msg:
            error_output(error_msg)

        yaml_output({"page": format_page(result)})


@command_handler
def cmd_search(args):
    """Search pages using CQL via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        if args.all:
            # Paginated search to fetch all results up to limit
            results, total_size = search_cql_paginated(
                client, cloud_id, args.cql, max_results=args.limit
            )
        else:
            # Single page search (faster for quick queries)
            result = client.call_tool(
                "searchConfluenceUsingCql",
                {
                    "cloudId": cloud_id,
                    "cql": args.cql,
                    "limit": args.limit,
                },
            )
            result, error_msg = parse_mcp_result(result)
            if error_msg:
                error_output(error_msg)
            results = result.get("results", [])
            total_size = result.get("totalSize", len(results))

        output = {
            "search": {
                "cql": args.cql,
                "total": total_size,
                "returned": len(results),
                "pages": [],
            }
        }

        for p in results:
            content = p.get("content", {})
            page_info = {
                "id": content.get("id"),
                "title": p.get("title") or content.get("title"),
                "type": content.get("type"),
                "url": p.get("url"),
                "excerpt": p.get("excerpt", "")[:200],
            }
            # Add space if available
            space = p.get("resultGlobalContainer", {})
            if space:
                page_info["space"] = space.get("title")
            # Add last modified
            if p.get("lastModified"):
                page_info["updated"] = p.get("lastModified")

            output["search"]["pages"].append(page_info)

        yaml_output(output)


def fetch_all_descendants_cql(client, cloud_id: str, page_id: str, max_results: int = 500) -> list:
    """Fetch all descendants using CQL via MCP with cursor pagination.

    Uses ancestor= CQL query which is more reliable than getConfluencePageDescendants API.
    """
    cql = f"ancestor={page_id}"
    results, _ = search_cql_paginated(client, cloud_id, cql, max_results=max_results)

    all_pages = []
    seen_ids = set()

    for p in results:
        content = p.get("content", {})
        page_id_found = content.get("id")
        if page_id_found and page_id_found not in seen_ids:
            seen_ids.add(page_id_found)
            page_info = {
                "id": page_id_found,
                "title": p.get("title") or content.get("title"),
                "status": content.get("status", "current"),
                "parent_id": content.get("parentId"),
            }
            all_pages.append(page_info)

    return all_pages


@command_handler
def cmd_children(args):
    """Get descendant pages using CQL ancestor= query."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        children = fetch_all_descendants_cql(client, cloud_id, args.page_id, args.limit)

        output = {
            "children": {
                "parent_id": args.page_id,
                "total": len(children),
                "pages": [],
            }
        }

        for c in children:
            output["children"]["pages"].append({
                "id": c.get("id"),
                "title": c.get("title"),
                "status": c.get("status"),
            })

        yaml_output(output)


@command_handler
def cmd_spaces(args):
    """List Confluence spaces via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "getConfluenceSpaces",
            {
                "cloudId": cloud_id,
                "maxResults": args.limit,
            },
        )

        result, error_msg = parse_mcp_result(result)
        if error_msg:
            error_output(error_msg)

        spaces = result.get("results", [])

        output = {
            "spaces": {
                "total": len(spaces),
                "items": [
                    {
                        "id": s.get("id"),
                        "key": s.get("key"),
                        "name": s.get("name"),
                        "type": s.get("type"),
                    }
                    for s in spaces
                ],
            }
        }

        yaml_output(output)


# ---------------------------------------------------------------------------
# File Writing Utilities
# ---------------------------------------------------------------------------
def sanitize_filename(title: str, page_id: str, max_length: int = 50) -> str:
    """Create a safe filename from page title and ID."""
    safe_title = re.sub(r'[^\w\s-]', '', title).strip().replace(' ', '_')[:max_length]
    return f"{safe_title}_{page_id}"


def format_page_content(page: dict, output_format: str) -> str:
    """Format page data to specified format string."""
    if output_format == "markdown":
        return format_page_markdown(page)
    elif output_format == "json":
        return json.dumps(page, indent=2)
    else:  # yaml
        return yaml.dump({"page": page}, default_flow_style=False, allow_unicode=True, sort_keys=False)


def write_page_to_file(page: dict, output_path: str, output_format: str):
    """Write a page to file in specified format."""
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    content = format_page_content(page, output_format)
    with open(output_path, "w") as f:
        f.write(content)


def generate_toc(toc_entries: list, output_dir: str):
    """Generate table of contents markdown file."""
    if not toc_entries:
        return

    toc_lines = ["# Table of Contents", ""]
    for depth, title, path in toc_entries:
        indent = "  " * depth
        toc_lines.append(f"{indent}- [{title}]({path})")

    toc_path = os.path.join(output_dir, "toc.md")
    with open(toc_path, "w") as f:
        f.write("\n".join(toc_lines) + "\n")


# ---------------------------------------------------------------------------
# Page Processor Class
# ---------------------------------------------------------------------------
class PageProcessor:
    """Handles downloading and writing individual pages."""

    def __init__(
        self,
        client,
        cloud_id: str,
        output_dir: str,
        output_format: str,
        max_depth: int,
        rate_limiter: AdaptiveRateLimiter,
        state: TreeState,
        stats: DownloadStats
    ):
        self.client = client
        self.cloud_id = cloud_id
        self.output_dir = output_dir
        self.output_format = output_format
        self.max_depth = max_depth
        self.rate_limiter = rate_limiter
        self.state = state
        self.stats = stats
        self.ext = FORMAT_EXTENSIONS.get(output_format, "md")

    def get_depth(self, folder_path: str) -> int:
        """Calculate depth from folder path relative to output_dir."""
        rel_path = os.path.relpath(folder_path, self.output_dir)
        return 0 if rel_path == "." else rel_path.count(os.sep) + 1

    def process(self, page_id: str) -> bool:
        """Process a single page. Returns True on success."""
        if page_id in self.state.downloaded_ids:
            return True

        self.rate_limiter.wait()

        # Fetch page content
        page_data, err = call_mcp_with_retry(
            self.client,
            "getConfluencePage",
            {"cloudId": self.cloud_id, "pageId": page_id, "includeBody": True},
            self.rate_limiter
        )
        if err:
            print(f"Warning: Failed to fetch page {page_id}: {err}", file=sys.stderr)
            return False

        # Parse if string
        if isinstance(page_data, str):
            page_data = json.loads(page_data)

        # Determine parent path using parentId from API
        parent_id = page_data.get("parentId")
        parent_path = self.state.id_to_path.get(parent_id, self.output_dir)

        # Check depth
        depth = self.get_depth(parent_path)
        if self.max_depth > 0 and depth > self.max_depth:
            return True

        # Format and write
        formatted = format_page(page_data, include_content=True)
        title = formatted.get("title", "Untitled")
        folder_name = sanitize_filename(title, page_id)
        folder_path = os.path.join(parent_path, folder_name)
        file_path = os.path.join(folder_path, f"index.{self.ext}")

        self.state.id_to_path[page_id] = folder_path
        write_page_to_file(formatted, file_path, self.output_format)

        self.state.downloaded_ids.add(page_id)
        self.stats.pages_downloaded += 1

        # Track for TOC
        toc_depth = self.get_depth(folder_path) - 1
        relative_path = os.path.relpath(file_path, self.output_dir)
        self.state.toc_entries.append((toc_depth, title, relative_path))

        print(f"Downloaded ({self.stats.pages_downloaded}): {title} [delay: {self.rate_limiter.state.delay:.1f}s]", file=sys.stderr)
        return True


# ---------------------------------------------------------------------------
# Command Handlers
# ---------------------------------------------------------------------------
@command_handler
def cmd_tree(args):
    """Download page tree(s) with proper nested folder structure."""
    cloud_id = get_cloud_id()
    os.makedirs(args.output_dir, exist_ok=True)

    # Initialize state using new classes
    rate_limiter = AdaptiveRateLimiter(args.delay)
    state = TreeState()
    stats = DownloadStats()

    # Discover all descendants upfront
    pending_queue = list(args.page_ids)
    print(f"Discovering descendants for {len(args.page_ids)} root page(s)...", file=sys.stderr)

    with mcp_client_context() as client:
        for root_id in args.page_ids:
            descendants = fetch_all_descendants_cql(client, cloud_id, root_id, max_results=args.limit * 10)
            for desc in descendants:
                desc_id = desc.get("id")
                if desc_id and desc_id not in pending_queue:
                    pending_queue.append(desc_id)

    print(f"Found {len(pending_queue)} pages to download", file=sys.stderr)

    # Process pages with connection recovery
    connection_retry = 0
    while pending_queue and connection_retry < MAX_CONNECTION_RETRIES:
        try:
            with mcp_client_context() as client:
                processor = PageProcessor(
                    client, cloud_id, args.output_dir, args.format,
                    args.max_depth, rate_limiter, state, stats
                )
                while pending_queue:
                    page_id = pending_queue.pop(0)
                    if not processor.process(page_id):
                        pending_queue.append(page_id)  # Re-queue failed
            connection_retry = 0  # Reset on successful completion
        except Exception as e:
            connection_retry += 1
            wait_time = min(30, rate_limiter.state.delay * connection_retry * 2)
            print(f"Connection lost: {e}. Reconnecting in {wait_time:.0f}s... (attempt {connection_retry}/{MAX_CONNECTION_RETRIES})", file=sys.stderr)
            print(f"Progress: {stats.pages_downloaded} pages downloaded, {len(pending_queue)} remaining", file=sys.stderr)
            time.sleep(wait_time)
            rate_limiter.on_failure()

    # Generate TOC
    generate_toc(state.toc_entries, args.output_dir)

    yaml_output({
        "tree": {
            "root_page_ids": args.page_ids,
            "pages_downloaded": stats.pages_downloaded,
            "output_dir": args.output_dir,
            "format": args.format,
        }
    })


@command_handler
def cmd_export(args):
    """Export pages matching CQL query to files or stdout."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # Search for pages using CQL with pagination
        search_results, total_size = search_cql_paginated(
            client, cloud_id, args.cql, max_results=args.limit
        )

        if not search_results:
            error_output("No pages found matching the query")

        print(f"Found {len(search_results)} of {total_size} total pages", file=sys.stderr)

        # Fetch full details for each page
        exported_pages = []
        for p in search_results:
            content = p.get("content", {})
            page_id = content.get("id")
            if not page_id:
                continue
            try:
                full_page = client.call_tool(
                    "getConfluencePage",
                    {"cloudId": cloud_id, "pageId": page_id, "includeBody": True},
                )
                full_page, err = parse_mcp_result(full_page)
                if err:
                    print(f"Warning: Failed to fetch page {page_id}: {err}", file=sys.stderr)
                    continue
                formatted = format_page(full_page, include_content=True)
                exported_pages.append(formatted)
            except Exception as e:
                print(f"Warning: Could not fetch page {page_id}: {e}", file=sys.stderr)

        if not exported_pages:
            error_output("Failed to fetch any pages")

        # Output based on format
        if args.output_dir:
            os.makedirs(args.output_dir, exist_ok=True)
            ext = FORMAT_EXTENSIONS.get(args.format, "yaml")
            filenames = []

            for page in exported_pages:
                title = page.get("title", page.get("id", "untitled"))
                filename = f"{sanitize_filename(title, page.get('id', ''))}.{ext}"
                filepath = os.path.join(args.output_dir, filename)
                write_page_to_file(page, filepath, args.format)
                filenames.append(filename)

            yaml_output({
                "export": {
                    "total": len(exported_pages),
                    "format": args.format,
                    "output_dir": args.output_dir,
                    "files": filenames,
                }
            })
        else:
            # Output to stdout
            if args.format == "markdown":
                for page in exported_pages:
                    print(format_page_content(page, "markdown"))
                    print("\n---\n")
            elif args.format == "json":
                print(json.dumps({"pages": exported_pages}, indent=2))
            else:  # yaml
                print(yaml.dump({"pages": exported_pages}, default_flow_style=False, allow_unicode=True, sort_keys=False))


@command_handler
def cmd_rovo(args):
    """Search Confluence pages using Rovo Search (filters out Jira results)."""
    with mcp_client_context() as client:
        result = client.call_tool("search", {"query": args.query})
        data, error_msg = parse_mcp_result(result)
        if error_msg:
            error_output(error_msg)

        results = data.get("results", []) if data else []
        formatted = []
        for item in results:
            # Filter to Confluence results only (ARI contains ":confluence:")
            item_id = item.get("id") or ""
            if ":confluence:" not in item_id:
                continue
            formatted.append({
                "id": item_id,
                "type": item.get("type"),
                "title": item.get("title"),
                "url": item.get("url"),
                "text": (item.get("text") or "")[:300],
            })

        yaml_output({"total": len(formatted), "results": formatted})


def main():
    parser = argparse.ArgumentParser(
        description="Confluence API operations (via MCP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # get command
    get_parser = subparsers.add_parser("get", help="Fetch a page with content")
    get_parser.add_argument("page_id", help="Page ID (numeric)")

    # search command
    search_parser = subparsers.add_parser("search", help="Search pages using CQL")
    search_parser.add_argument("cql", help="CQL query string")
    search_parser.add_argument(
        "--limit", "-l", type=int, default=25, help="Max results (default: 25)"
    )
    search_parser.add_argument(
        "--all", "-a", action="store_true",
        help="Paginate through all results up to limit (default: single page)"
    )

    # children command (returns all descendants, not just direct children)
    children_parser = subparsers.add_parser("children", help="Get all descendant pages")
    children_parser.add_argument("page_id", help="Parent page ID")
    children_parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Max results (default: 50)"
    )

    # spaces command
    spaces_parser = subparsers.add_parser("spaces", help="List Confluence spaces")
    spaces_parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Max results (default: 50)"
    )

    # tree command
    tree_parser = subparsers.add_parser("tree", help="Download page tree(s) with nested folders")
    tree_parser.add_argument("page_ids", nargs='+', help="Root page ID(s) to download")
    tree_parser.add_argument(
        "--output-dir", "-o", required=True, help="Output directory (required)"
    )
    tree_parser.add_argument(
        "--format", "-f", choices=["yaml", "json", "markdown"], default="markdown",
        help="Output format (default: markdown)"
    )
    tree_parser.add_argument(
        "--limit", "-l", type=int, default=100, help="Max children per page (default: 100)"
    )
    tree_parser.add_argument(
        "--max-depth", type=int, default=10, help="Max recursion depth (default: 10, 0=unlimited)"
    )
    tree_parser.add_argument(
        "--delay", "-d", type=float, default=0.5, help="Delay between requests in seconds (default: 0.5)"
    )

    # export command
    export_parser = subparsers.add_parser("export", help="Export pages matching CQL query")
    export_parser.add_argument("cql", help="CQL query string")
    export_parser.add_argument(
        "--format", "-f", choices=["yaml", "json", "markdown"], default="yaml",
        help="Output format (default: yaml)"
    )
    export_parser.add_argument(
        "--output-dir", "-o", help="Directory to save files (one per page)"
    )
    export_parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Max pages to export (default: 50)"
    )

    # rovo command
    rovo_parser = subparsers.add_parser(
        "rovo", help="Search Confluence pages using Rovo (filters out Jira)"
    )
    rovo_parser.add_argument("query", help="Search query")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "get": cmd_get,
        "search": cmd_search,
        "children": cmd_children,
        "spaces": cmd_spaces,
        "tree": cmd_tree,
        "export": cmd_export,
        "rovo": cmd_rovo,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

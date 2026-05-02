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
Jira API operations script.

Uses MCP client to communicate with Atlassian MCP server.

Commands:
    get <KEY>              - Fetch a single issue with all details
    search <JQL>           - Search issues using JQL
    comments <KEY>         - Get comments for an issue
    projects               - List accessible Jira projects
    types <PROJECT>        - List available issue types for a project
    fields <PROJECT>       - List fields for an issue type
    transitions <KEY>      - Get available transitions for an issue
    statuses <PROJECT>     - List all available statuses for a project
    comment <KEY> <BODY>   - Add a comment to an issue
    transition <KEY> <STATUS> - Transition an issue to a new status
    assign <KEY> <ID>      - Assign or unassign an issue
    create <PROJECT>       - Create a new issue (supports --field)
    edit <KEY>             - Edit an existing issue
    me                     - Show current user info
    lookup <QUERY>         - Lookup user by name or email
    export <JQL>           - Export issues to yaml/json/markdown files
    rovo <QUERY>           - Search Jira issues using Rovo
"""

import argparse
import json
import sys
from pathlib import Path
from typing import NoReturn

# Add parent directory to path for common module
sys.path.insert(0, str(Path(__file__).parent))

from common import (
    get_cloud_id,
    yaml_output,
    error_output,
    parse_mcp_result,
    mcp_client_context,
    command_handler,
)


def parse_jira_error(error: Exception) -> dict:
    """Parse MCP/Jira errors into user-friendly format."""
    import re

    error_str = str(error)
    result = {"message": error_str}

    # Parse MCP validation errors
    if "Invalid arguments" in error_str:
        try:
            match = re.search(r"\[.*\]", error_str, re.DOTALL)
            if match:
                errors = json.loads(match.group())
                fields = []
                for e in errors:
                    path = ".".join(e.get("path", []))
                    fields.append(f"{path}: {e.get('message', 'invalid')}")
                result["message"] = "Validation error"
                result["fields"] = fields
                result["hint"] = "Check parameter names and types"
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    # Parse Jira API errors (Bad Request)
    if "Bad Request" in error_str or '"errors"' in error_str:
        found_details = False
        try:
            # Find JSON object containing errors
            start = error_str.find('{"errorMessages"')
            if start < 0:
                start = error_str.find('{"errors"')
            if start >= 0:
                # Count braces to find matching close
                depth = 0
                end = start
                for i, c in enumerate(error_str[start:], start):
                    if c == "{":
                        depth += 1
                    elif c == "}":
                        depth -= 1
                        if depth == 0:
                            end = i + 1
                            break

                json_str = error_str[start:end]
                jira_error = json.loads(json_str)
                errors = jira_error.get("errors", {})
                messages = jira_error.get("errorMessages", [])

                if errors:
                    result["message"] = "Jira field errors"
                    result["fields"] = [f"{k}: {v}" for k, v in errors.items()]
                    found_details = True
                if messages and any(messages):
                    result["messages"] = messages
                    found_details = True

        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            pass

        # Always add helpful context for Bad Request errors
        if "Bad Request" in error_str:
            if not found_details:
                # Provide more context when we don't have specific field errors
                if "edit" in error_str.lower() or "update" in error_str.lower():
                    result["message"] = "Failed to edit issue - invalid field or value"
                    result["possible_causes"] = [
                        "Field name doesn't exist",
                        "Field value has wrong type",
                        "Field is not editable",
                    ]
                elif "create" in error_str.lower():
                    result["message"] = (
                        "Failed to create issue - missing or invalid field"
                    )
                    result["possible_causes"] = [
                        "Required field missing",
                        "Invalid issue type",
                        "Field value has wrong format",
                    ]
            result["hint"] = (
                "Run 'jira.py fields <PROJECT> --type <TYPE>' to see available fields"
            )

    return result


def jira_error_output(error: Exception) -> NoReturn:
    """Output parsed Jira error as YAML and exit."""
    import yaml

    parsed = parse_jira_error(error)
    # If we parsed additional info (fields, hint), output as structured error
    if len(parsed) > 1:
        yaml.dump(
            {"error": parsed}, sys.stderr, default_flow_style=False, allow_unicode=True
        )
        sys.exit(1)
    else:
        error_output(parsed.get("message", str(error)))


def format_user(user_data: dict | None) -> dict | None:
    """Format user data for YAML output."""
    if not user_data:
        return None
    return {
        "name": user_data.get("displayName"),
        "account_id": user_data.get("accountId"),
    }


def format_issue(issue: dict, include_comments: bool = True) -> dict:
    """Format issue data for compact YAML output."""
    fields = issue.get("fields", {})

    result = {
        "key": issue.get("key"),
        "id": issue.get("id"),
        "type": fields.get("issuetype", {}).get("name"),
        "status": fields.get("status", {}).get("name"),
        "summary": fields.get("summary"),
    }

    # Description
    description = fields.get("description")
    if description:
        # Handle ADF (Atlassian Document Format)
        if isinstance(description, dict):
            result["description"] = extract_text_from_adf(description)
        else:
            result["description"] = description

    # Dates
    result["created"] = fields.get("created")
    result["updated"] = fields.get("updated")

    # People
    result["author"] = format_user(fields.get("reporter"))
    result["assignee"] = format_user(fields.get("assignee"))

    # Priority
    priority = fields.get("priority")
    if priority:
        result["priority"] = priority.get("name")

    # Parent (for subtasks/stories in epics)
    parent = fields.get("parent")
    if parent:
        result["parent"] = {
            "key": parent.get("key"),
            "summary": parent.get("fields", {}).get("summary"),
        }

    # Labels
    labels = fields.get("labels")
    if labels:
        result["labels"] = labels

    # Comments
    if include_comments:
        comment_data = fields.get("comment", {})
        comments = comment_data.get("comments", [])
        if comments:
            result["comments"] = [
                {
                    "author": format_user(c.get("author")),
                    "created": c.get("created"),
                    "body": extract_text_from_adf(c.get("body"))
                    if isinstance(c.get("body"), dict)
                    else c.get("body"),
                }
                for c in comments
            ]

    # Attachments
    attachments = fields.get("attachment", [])
    if attachments:
        result["attachments"] = [
            {
                "filename": a.get("filename"),
                "size": a.get("size"),
                "mime_type": a.get("mimeType"),
                "url": a.get("content"),
            }
            for a in attachments
        ]

    return result


def format_search_markdown(output: dict) -> str:
    """Format search results as markdown table."""
    search = output.get("search", {})
    jql = search.get("jql", "")
    total = search.get("total", 0)
    issues = search.get("issues", [])

    lines = [
        "# Search Results",
        "",
        f"**JQL:** `{jql}`  ",
        f"**Total:** {total} issues",
        "",
        "| Key | Type | Status | Summary | Assignee |",
        "|-----|------|--------|---------|----------|",
    ]

    for issue in issues:
        key = issue.get("key", "")
        issue_type = issue.get("type", "")
        status = issue.get("status", "")
        summary = issue.get("summary", "")[:60]
        if len(issue.get("summary", "")) > 60:
            summary += "..."
        assignee = issue.get("assignee")
        assignee_name = assignee.get("name", "") if assignee else "Unassigned"
        # Escape pipe characters in summary
        summary = summary.replace("|", "\\|")
        lines.append(
            f"| {key} | {issue_type} | {status} | {summary} | {assignee_name} |"
        )

    lines.append("")
    return "\n".join(lines)


def format_issue_markdown(issue: dict) -> str:
    """Format issue as markdown document."""

    def get_user_name(user_obj):
        if not user_obj:
            return "N/A"
        if isinstance(user_obj, dict):
            return user_obj.get("name", "N/A")
        return str(user_obj)

    lines = [
        f"# {issue['key']}: {issue['summary']}",
        "",
        f"**Type:** {issue.get('type', 'N/A')}  ",
        f"**Status:** {issue.get('status', 'N/A')}  ",
        f"**Priority:** {issue.get('priority', 'None')}  ",
        f"**Author:** {get_user_name(issue.get('author'))}  ",
        f"**Assignee:** {get_user_name(issue.get('assignee')) if issue.get('assignee') else 'Unassigned'}  ",
        f"**Created:** {issue.get('created', 'N/A')}  ",
        f"**Updated:** {issue.get('updated', 'N/A')}  ",
    ]

    # Parent link
    if issue.get("parent"):
        lines.append(
            f"**Parent:** {issue['parent'].get('key', '')} - {issue['parent'].get('summary', '')}  "
        )

    # Labels
    if issue.get("labels"):
        lines.append(f"**Labels:** {', '.join(issue['labels'])}  ")

    lines.extend(["", "## Description", ""])
    lines.append(issue.get("description") or "_No description_")
    lines.append("")

    # Comments
    if issue.get("comments"):
        lines.extend(["## Comments", ""])
        for c in issue["comments"]:
            author = get_user_name(c.get("author"))
            lines.append(f"### {author} - {c.get('created', 'Unknown date')}")
            lines.append("")
            lines.append(c.get("body") or "_Empty comment_")
            lines.append("")

    # Attachments
    if issue.get("attachments"):
        lines.extend(["## Attachments", ""])
        for a in issue["attachments"]:
            lines.append(f"- {a.get('filename', 'Unknown')} ({a.get('size', 0)} bytes)")
        lines.append("")

    return "\n".join(lines)


def extract_text_from_adf(adf: dict) -> str:
    """Extract plain text from Atlassian Document Format."""
    if not adf:
        return ""

    texts = []

    def extract(node):
        if isinstance(node, dict):
            if node.get("type") == "text":
                texts.append(node.get("text", ""))
            for child in node.get("content", []):
                extract(child)
        elif isinstance(node, list):
            for item in node:
                extract(item)

    extract(adf)
    return "".join(texts)


def search_jql_paginated(
    client, cloud_id: str, jql: str, max_results: int = 100
) -> tuple[list, int]:
    """Fetch results from JQL search.

    Note: The Atlassian MCP server doesn't return pagination tokens for JQL search,
    so we're limited to maxResults per call (max 100). True pagination is not possible.

    Returns:
        (issues_list, total_count) - list of issues and total fetched count
    """
    # MCP server doesn't support pagination for JQL - just get up to max_results (capped at 100)
    actual_limit = min(max_results, 100)

    params = {
        "cloudId": cloud_id,
        "jql": jql,
        "maxResults": actual_limit,
    }

    result = client.call_tool("searchJiraIssuesUsingJql", params)
    result, err = parse_mcp_result(result)
    if err or result is None:
        return [], 0

    if isinstance(result, list):
        issues = result
    elif isinstance(result, dict):
        issues = result.get("issues", [])
    else:
        return [], 0

    return issues, len(issues)


@command_handler
def cmd_get(args):
    """Fetch a single issue with all details via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "getJiraIssue",
            {
                "cloudId": cloud_id,
                "issueIdOrKey": args.key,
            },
        )

        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")
        assert isinstance(result, dict)  # type narrowing for ty

        yaml_output({"issue": format_issue(result)})


@command_handler
def cmd_search(args):
    """Search issues using JQL via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        if args.all:
            # Paginated search to fetch all results up to limit
            issues, total_count = search_jql_paginated(
                client, cloud_id, args.jql, max_results=args.limit
            )
        else:
            # Single page search (faster for quick queries)
            result = client.call_tool(
                "searchJiraIssuesUsingJql",
                {
                    "cloudId": cloud_id,
                    "jql": args.jql,
                    "maxResults": args.limit,
                },
            )
            result, error_msg = parse_mcp_result(result)
            if error_msg or result is None:
                error_output(error_msg or "Invalid response format")

            # Handle both dict with "issues" key and direct list of issues
            if isinstance(result, list):
                issues = result
            elif isinstance(result, dict):
                issues = result.get("issues", [])
            else:
                issues = []
            total_count = len(issues)

        output = {
            "search": {
                "jql": args.jql,
                "total": total_count,
                "returned": len(issues),
                "issues": [],
            }
        }

        for i in issues:
            fields = i.get("fields", {})
            issue_info = {
                "key": i.get("key"),
                "type": fields.get("issuetype", {}).get("name"),
                "status": fields.get("status", {}).get("name"),
                "summary": fields.get("summary"),
            }

            # Priority
            priority = fields.get("priority")
            if priority:
                issue_info["priority"] = priority.get("name")

            # Assignee
            assignee = fields.get("assignee")
            if assignee:
                issue_info["assignee"] = format_user(assignee)

            # Created date
            if fields.get("created"):
                issue_info["created"] = fields.get("created")

            output["search"]["issues"].append(issue_info)

        # Output based on format
        if args.format == "json":
            print(json.dumps(output, indent=2))
        elif args.format == "markdown":
            print(format_search_markdown(output))
        else:  # yaml (default)
            yaml_output(output)


@command_handler
def cmd_comments(args):
    """Get comments for an issue via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "getJiraIssue",
            {
                "cloudId": cloud_id,
                "issueIdOrKey": args.key,
            },
        )

        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")

        fields = result.get("fields", {})
        comment_data = fields.get("comment", {})
        comments = comment_data.get("comments", [])

        output = {
            "comments": {
                "issue_key": args.key,
                "total": len(comments),
                "items": [
                    {
                        "id": c.get("id"),
                        "author": format_user(c.get("author")),
                        "created": c.get("created"),
                        "updated": c.get("updated"),
                        "body": extract_text_from_adf(c.get("body"))
                        if isinstance(c.get("body"), dict)
                        else c.get("body"),
                    }
                    for c in comments[: args.limit]
                ],
            }
        }

        yaml_output(output)


@command_handler
def cmd_projects(args):
    """List accessible Jira projects via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "getVisibleJiraProjects",
            {
                "cloudId": cloud_id,
                "maxResults": args.limit,
            },
        )

        result, error_msg = parse_mcp_result(result)
        if error_msg or result is None:
            error_output(error_msg or "Invalid response format")

        projects = result.get("values", result) if isinstance(result, dict) else result

        output = {
            "projects": {
                "total": len(projects) if isinstance(projects, list) else 0,
                "items": [],
            }
        }

        if isinstance(projects, list):
            for p in projects:
                output["projects"]["items"].append(
                    {
                        "id": p.get("id"),
                        "key": p.get("key"),
                        "name": p.get("name"),
                        "type": p.get("projectTypeKey"),
                    }
                )

        yaml_output(output)


@command_handler
def cmd_transitions(args):
    """Get available transitions for an issue via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # Get current issue status first
        issue_result = client.call_tool(
            "getJiraIssue",
            {"cloudId": cloud_id, "issueIdOrKey": args.key},
        )
        issue_result, error_msg = parse_mcp_result(issue_result)
        if error_msg or not isinstance(issue_result, dict):
            error_output(error_msg or "Invalid response format")
        current_status = issue_result.get("fields", {}).get("status", {}).get("name")

        # Get available transitions
        result = client.call_tool(
            "getTransitionsForJiraIssue",
            {"cloudId": cloud_id, "issueIdOrKey": args.key},
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")

        transitions = result.get("transitions", [])

        output = {
            "transitions": {
                "issue_key": args.key,
                "current_status": current_status,
                "total": len(transitions),
                "items": [
                    {
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "to_status": t.get("to", {}).get("name"),
                    }
                    for t in transitions
                ],
            }
        }

        yaml_output(output)


@command_handler
def cmd_statuses(args):
    """Get all available statuses for a project via MCP.

    Uses JQL search to find issues and aggregate unique statuses,
    since there's no direct MCP tool for project-level statuses.
    """
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # Search for issues in the project to discover statuses with pagination
        issues, _ = search_jql_paginated(
            client,
            cloud_id,
            f"project = {args.project} ORDER BY status ASC",
            max_results=500,  # Get enough to capture all statuses
        )

        # Extract unique statuses from issues
        statuses_map = {}  # id -> status info
        for issue in issues:
            status = issue.get("fields", {}).get("status", {})
            status_id = status.get("id")
            if status_id and status_id not in statuses_map:
                statuses_map[status_id] = {
                    "id": status_id,
                    "name": status.get("name"),
                    "category": status.get("statusCategory", {}).get("name"),
                    "description": status.get("description", ""),
                }

        # Sort by category then name for better organization
        category_order = {"To Do": 0, "In Progress": 1, "Done": 2}
        statuses_list = sorted(
            statuses_map.values(),
            key=lambda s: (
                category_order.get(s.get("category"), 99),
                s.get("name", ""),
            ),
        )

        output = {
            "statuses": {
                "project": args.project,
                "total": len(statuses_list),
                "note": "Statuses discovered from existing issues (may not include unused workflow statuses)",
                "items": statuses_list,
            }
        }

        yaml_output(output)


@command_handler
def cmd_comment(args):
    """Add a comment to an issue via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "addCommentToJiraIssue",
            {
                "cloudId": cloud_id,
                "issueIdOrKey": args.key,
                "commentBody": args.body,
            },
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            jira_error_output(Exception(error_msg or "Invalid response format"))

        output = {
            "comment": {
                "issue_key": args.key,
                "id": result.get("id"),
                "author": format_user(result.get("author")),
                "created": result.get("created"),
            }
        }

        yaml_output(output)


@command_handler
def cmd_transition(args):
    """Transition an issue to a new status via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # Get available transitions
        result = client.call_tool(
            "getTransitionsForJiraIssue",
            {"cloudId": cloud_id, "issueIdOrKey": args.key},
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            jira_error_output(Exception(error_msg or "Invalid response format"))

        transitions = result.get("transitions", [])

        # Find matching transition
        target_transition = None

        if args.id:
            # Match by ID
            for t in transitions:
                if t.get("id") == args.id:
                    target_transition = t
                    break
        else:
            # Match by name (case-insensitive)
            target_name = args.status.lower()
            for t in transitions:
                if t.get("name", "").lower() == target_name:
                    target_transition = t
                    break
                # Also try matching the destination status name
                if t.get("to", {}).get("name", "").lower() == target_name:
                    target_transition = t
                    break

        if not target_transition:
            available = [f"{t.get('name')} (id: {t.get('id')})" for t in transitions]
            error_output(f"Transition not found. Available: {', '.join(available)}")

        # Perform transition
        result = client.call_tool(
            "transitionJiraIssue",
            {
                "cloudId": cloud_id,
                "issueIdOrKey": args.key,
                "transition": {"id": target_transition.get("id")},
            },
        )
        _, error_msg = parse_mcp_result(result)
        if error_msg:
            jira_error_output(Exception(error_msg))

        output = {
            "transition": {
                "issue_key": args.key,
                "to_status": target_transition.get("to", {}).get("name"),
                "transition_name": target_transition.get("name"),
            }
        }

        yaml_output(output)


@command_handler
def cmd_assign(args):
    """Assign or unassign an issue via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        if args.unassign:
            # Unassign the issue
            assignee_id = None
        elif args.me:
            # Get current user's account ID
            user_info = client.call_tool("atlassianUserInfo", {})
            user_info, error_msg = parse_mcp_result(user_info)
            if error_msg or not isinstance(user_info, dict):
                jira_error_output(Exception(error_msg or "Invalid response format"))
            assignee_id = user_info.get("account_id")
        else:
            assignee_id = args.account_id

        # Update assignee using editJiraIssue
        result = client.call_tool(
            "editJiraIssue",
            {
                "cloudId": cloud_id,
                "issueIdOrKey": args.key,
                "fields": {
                    "assignee": {"accountId": assignee_id} if assignee_id else None
                },
            },
        )
        _, error_msg = parse_mcp_result(result)
        if error_msg:
            jira_error_output(Exception(error_msg))

        if assignee_id:
            output = {
                "assign": {
                    "issue_key": args.key,
                    "assignee_id": assignee_id,
                    "status": "assigned",
                }
            }
        else:
            output = {
                "assign": {
                    "issue_key": args.key,
                    "status": "unassigned",
                }
            }

        yaml_output(output)


@command_handler
def cmd_create(args):
    """Create a new Jira issue via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # Build MCP tool arguments
        tool_args = {
            "cloudId": cloud_id,
            "projectKey": args.project,
            "issueTypeName": args.type,
            "summary": args.summary,
        }

        # Optional fields
        if args.description:
            tool_args["description"] = args.description

        if args.labels:
            tool_args["labels"] = [label.strip() for label in args.labels.split(",")]

        if args.assignee:
            tool_args["assigneeAccountId"] = args.assignee

        if args.parent:
            tool_args["parentKey"] = args.parent

        # Custom fields via --field option
        if args.field:
            extra_fields = {}
            for field_spec in args.field:
                if "=" in field_spec:
                    name, value = field_spec.split("=", 1)
                    extra_fields[name.strip()] = value.strip()
            if extra_fields:
                tool_args["extraFields"] = extra_fields

        # Create issue
        result = client.call_tool("createJiraIssue", tool_args)
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            jira_error_output(Exception(error_msg or "Invalid response format"))

        output = {
            "created": {
                "key": result.get("key"),
                "id": result.get("id"),
                "type": args.type,
                "summary": args.summary,
            }
        }

        yaml_output(output)


@command_handler
def cmd_edit(args):
    """Edit an existing Jira issue via MCP."""
    cloud_id = get_cloud_id()

    # Build fields to update
    fields = {}

    if args.summary:
        fields["summary"] = args.summary

    if args.description:
        fields["description"] = args.description

    # Custom fields via --field option
    if args.field:
        for field_spec in args.field:
            if "=" in field_spec:
                name, value = field_spec.split("=", 1)
                fields[name.strip()] = value.strip()

    if not fields:
        error_output("No fields to update. Use --summary, --description, or --field")

    with mcp_client_context() as client:
        result = client.call_tool(
            "editJiraIssue",
            {
                "cloudId": cloud_id,
                "issueIdOrKey": args.key,
                "fields": fields,
            },
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg:
            jira_error_output(Exception(error_msg))

        output = {
            "edited": {
                "key": args.key,
                "fields_updated": list(fields.keys()),
            }
        }

        yaml_output(output)


@command_handler
def cmd_types(args):
    """List available issue types for a project via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "getJiraProjectIssueTypesMetadata",
            {"cloudId": cloud_id, "projectIdOrKey": args.project},
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")

        issue_types = result.get("issueTypes", [])

        output = {
            "types": {
                "project": args.project,
                "total": len(issue_types),
                "items": [
                    {
                        "id": t.get("id"),
                        "name": t.get("name"),
                        "subtask": t.get("subtask", False),
                        "description": t.get("description", "")[:50],
                    }
                    for t in issue_types
                ],
            }
        }

        yaml_output(output)


@command_handler
def cmd_fields(args):
    """List fields for a project and issue type via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # First get the issue type ID from name
        types_result = client.call_tool(
            "getJiraProjectIssueTypesMetadata",
            {"cloudId": cloud_id, "projectIdOrKey": args.project},
        )
        types_result, error_msg = parse_mcp_result(types_result)
        if error_msg or not isinstance(types_result, dict):
            error_output(error_msg or "Invalid response format")

        issue_type_id = None
        issue_types_list = types_result.get("issueTypes", [])
        for t in issue_types_list:
            if t.get("name", "").lower() == args.type.lower():
                issue_type_id = t.get("id")
                break

        if not issue_type_id:
            available = [t.get("name") for t in issue_types_list]
            error_output(
                f"Issue type '{args.type}' not found. Available: {', '.join(available)}"
            )

        # Get field metadata
        result = client.call_tool(
            "getJiraIssueTypeMetaWithFields",
            {
                "cloudId": cloud_id,
                "projectIdOrKey": args.project,
                "issueTypeId": issue_type_id,
            },
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")

        fields = result.get("fields", [])

        # Sort: required first, then by name
        fields_sorted = sorted(
            fields, key=lambda f: (not f.get("required", False), f.get("name", ""))
        )

        output = {
            "fields": {
                "project": args.project,
                "issue_type": args.type,
                "total": len(fields),
                "items": [
                    {
                        "name": f.get("name"),
                        "key": f.get("key"),
                        "required": f.get("required", False),
                        "type": f.get("schema", {}).get("type", "unknown"),
                    }
                    for f in fields_sorted
                ],
            }
        }

        yaml_output(output)


@command_handler
def cmd_me(_args):
    """Show current user info via MCP."""
    with mcp_client_context() as client:
        result = client.call_tool("atlassianUserInfo", {})
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")

        output = {
            "user": {
                "account_id": result.get("account_id"),
                "name": result.get("name"),
                "email": result.get("email"),
            }
        }

        yaml_output(output)


@command_handler
def cmd_lookup(args):
    """Lookup user by name or email via MCP."""
    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        result = client.call_tool(
            "lookupJiraAccountId",
            {"cloudId": cloud_id, "searchString": args.query},
        )
        result, error_msg = parse_mcp_result(result)
        if error_msg or not isinstance(result, dict):
            error_output(error_msg or "Invalid response format")

        # Extract users from nested structure: result.users.users
        users_data = result.get("users", {})
        users = users_data.get("users", []) if isinstance(users_data, dict) else []

        output = {
            "lookup": {
                "query": args.query,
                "total": len(users),
                "users": [
                    {
                        "account_id": u.get("accountId"),
                        "name": u.get("displayName"),
                    }
                    for u in users
                ],
            }
        }

        yaml_output(output)


@command_handler
def cmd_export(args):
    """Export issues matching JQL query to files or stdout."""
    import os
    import yaml as yaml_lib

    cloud_id = get_cloud_id()

    with mcp_client_context() as client:
        # Search for issues using JQL with pagination
        issues, total_count = search_jql_paginated(
            client, cloud_id, args.jql, max_results=args.limit
        )

        if not issues:
            error_output("No issues found matching the query")

        print(f"Found {len(issues)} issues to export", file=sys.stderr)

        # Fetch full details for each issue
        exported_issues = []
        for issue in issues:
            issue_key = issue.get("key")
            try:
                full_issue = client.call_tool(
                    "getJiraIssue",
                    {
                        "cloudId": cloud_id,
                        "issueIdOrKey": issue_key,
                    },
                )
                full_issue, err = parse_mcp_result(full_issue)
                if err or not isinstance(full_issue, dict):
                    print(
                        f"Warning: Failed to fetch {issue_key}: {err or 'Invalid format'}",
                        file=sys.stderr,
                    )
                    continue
                formatted = format_issue(full_issue, include_comments=True)
                exported_issues.append(formatted)
            except Exception as e:
                # Log error but continue with other issues
                print(f"Warning: Could not fetch {issue_key}: {e}", file=sys.stderr)

        if not exported_issues:
            error_output("Failed to fetch any issues")

        # Output based on format
        if args.output_dir:
            # Create output directory if needed
            os.makedirs(args.output_dir, exist_ok=True)

            ext_map = {"yaml": "yaml", "json": "json", "markdown": "md"}
            ext = ext_map.get(args.format, "yaml")

            for issue in exported_issues:
                filename = f"{issue['key']}.{ext}"
                filepath = os.path.join(args.output_dir, filename)

                if args.format == "markdown":
                    content = format_issue_markdown(issue)
                elif args.format == "json":
                    content = json.dumps(issue, indent=2)
                else:  # yaml
                    content = yaml_lib.dump(
                        {"issue": issue},
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )

                with open(filepath, "w") as f:
                    f.write(content)

            output = {
                "export": {
                    "total": len(exported_issues),
                    "format": args.format,
                    "output_dir": args.output_dir,
                    "files": [f"{i['key']}.{ext}" for i in exported_issues],
                }
            }
            yaml_output(output)
        else:
            # Output to stdout
            if args.format == "markdown":
                for issue in exported_issues:
                    print(format_issue_markdown(issue))
                    print("\n---\n")
            elif args.format == "json":
                print(json.dumps({"issues": exported_issues}, indent=2))
            else:  # yaml
                print(
                    yaml_lib.dump(
                        {"issues": exported_issues},
                        default_flow_style=False,
                        allow_unicode=True,
                        sort_keys=False,
                    )
                )


@command_handler
def cmd_rovo(args):
    """Search Jira issues using Rovo Search (filters out Confluence results)."""
    with mcp_client_context() as client:
        result = client.call_tool("search", {"query": args.query})
        data, error_msg = parse_mcp_result(result)
        if error_msg:
            error_output(error_msg)

        results = data.get("results", []) if data else []
        formatted = []
        for item in results:
            # Filter to Jira results only (ARI contains ":jira:")
            item_id = item.get("id") or ""
            if ":jira:" not in item_id:
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
        description="Jira API operations (via MCP)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # get command
    get_parser = subparsers.add_parser("get", help="Fetch a single issue")
    get_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")

    # search command
    search_parser = subparsers.add_parser("search", help="Search issues using JQL")
    search_parser.add_argument("jql", help="JQL query string")
    search_parser.add_argument(
        "--limit", "-l", type=int, default=25, help="Max results (default: 25)"
    )
    search_parser.add_argument(
        "--format",
        "-f",
        choices=["yaml", "json", "markdown"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    search_parser.add_argument(
        "--all",
        "-a",
        action="store_true",
        help="Paginate through all results up to limit (default: single page)",
    )

    # comments command
    comments_parser = subparsers.add_parser(
        "comments", help="Get comments for an issue"
    )
    comments_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")
    comments_parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Max comments (default: 50)"
    )

    # projects command
    projects_parser = subparsers.add_parser("projects", help="List Jira projects")
    projects_parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Max results (default: 50)"
    )

    # transitions command
    transitions_parser = subparsers.add_parser(
        "transitions", help="Get available transitions for an issue"
    )
    transitions_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")

    # comment command
    comment_parser = subparsers.add_parser("comment", help="Add a comment to an issue")
    comment_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")
    comment_parser.add_argument("body", help="Comment text")

    # transition command
    transition_parser = subparsers.add_parser(
        "transition", help="Transition an issue to a new status"
    )
    transition_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")
    transition_parser.add_argument(
        "status", nargs="?", help="Target status name (e.g., 'In Progress')"
    )
    transition_parser.add_argument(
        "--id", help="Transition ID (alternative to status name)"
    )

    # assign command
    assign_parser = subparsers.add_parser("assign", help="Assign or unassign an issue")
    assign_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")
    assign_parser.add_argument("account_id", nargs="?", help="Account ID to assign to")
    assign_parser.add_argument("--me", action="store_true", help="Assign to yourself")
    assign_parser.add_argument(
        "--unassign", action="store_true", help="Remove assignee"
    )

    # create command
    create_parser = subparsers.add_parser("create", help="Create a new issue")
    create_parser.add_argument("project", help="Project key (e.g., PROJ)")
    create_parser.add_argument(
        "--type", "-t", required=True, help="Issue type (e.g., Story, Bug, Task)"
    )
    create_parser.add_argument(
        "--summary", "-s", required=True, help="Issue summary/title"
    )
    create_parser.add_argument("--description", "-d", help="Issue description")
    create_parser.add_argument(
        "--priority", "-p", help="Priority (e.g., High, Medium, Low)"
    )
    create_parser.add_argument("--labels", help="Comma-separated labels")
    create_parser.add_argument("--assignee", "-a", help="Assignee account ID")
    create_parser.add_argument("--parent", help="Parent issue key (for subtasks)")
    create_parser.add_argument(
        "--field", "-f", action="append", help="Custom field: 'Name=value' (repeatable)"
    )

    # edit command
    edit_parser = subparsers.add_parser("edit", help="Edit an existing issue")
    edit_parser.add_argument("key", help="Issue key (e.g., PROJ-123)")
    edit_parser.add_argument("--summary", "-s", help="New summary/title")
    edit_parser.add_argument("--description", "-d", help="New description")
    edit_parser.add_argument(
        "--field",
        "-f",
        action="append",
        help="Field to update: 'Name=value' (repeatable)",
    )

    # types command
    types_parser = subparsers.add_parser(
        "types", help="List available issue types for a project"
    )
    types_parser.add_argument("project", help="Project key (e.g., PROJ)")

    # statuses command
    statuses_parser = subparsers.add_parser(
        "statuses", help="List all available statuses for a project"
    )
    statuses_parser.add_argument("project", help="Project key (e.g., PROJ)")

    # fields command
    fields_parser = subparsers.add_parser(
        "fields", help="List fields for a project and issue type"
    )
    fields_parser.add_argument("project", help="Project key (e.g., PROJ)")
    fields_parser.add_argument(
        "--type", "-t", required=True, help="Issue type (e.g., Story, Bug)"
    )

    # me command
    subparsers.add_parser("me", help="Show current user info")

    # lookup command
    lookup_parser = subparsers.add_parser("lookup", help="Lookup user by name or email")
    lookup_parser.add_argument("query", help="User name or email to search")

    # export command
    export_parser = subparsers.add_parser(
        "export", help="Export issues matching JQL query"
    )
    export_parser.add_argument("jql", help="JQL query string")
    export_parser.add_argument(
        "--format",
        "-f",
        choices=["yaml", "json", "markdown"],
        default="yaml",
        help="Output format (default: yaml)",
    )
    export_parser.add_argument(
        "--output-dir", "-o", help="Directory to save files (one per issue)"
    )
    export_parser.add_argument(
        "--limit", "-l", type=int, default=50, help="Max issues to export (default: 50)"
    )

    # rovo command
    rovo_parser = subparsers.add_parser(
        "rovo", help="Search Jira issues using Rovo (filters out Confluence)"
    )
    rovo_parser.add_argument("query", help="Search query")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    commands = {
        "get": cmd_get,
        "search": cmd_search,
        "comments": cmd_comments,
        "projects": cmd_projects,
        "transitions": cmd_transitions,
        "statuses": cmd_statuses,
        "comment": cmd_comment,
        "transition": cmd_transition,
        "assign": cmd_assign,
        "create": cmd_create,
        "edit": cmd_edit,
        "types": cmd_types,
        "fields": cmd_fields,
        "me": cmd_me,
        "lookup": cmd_lookup,
        "export": cmd_export,
        "rovo": cmd_rovo,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

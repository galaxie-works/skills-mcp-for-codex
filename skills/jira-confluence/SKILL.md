---
name: jira-confluence
description: Access Jira issues and Confluence pages via Python scripts with OAuth
  2.0 authentication. Use when user asks about Jira tickets, issues, bugs, stories,
  epics, sprints, or Confluence pages, wiki, documentation.
---
# Atlassian Skill

Access Jira and Confluence content via Python scripts. All output is YAML format for minimal token usage.

# OAuth Login
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/auth.py login
```

# Rovo Search

Search Atlassian content using Rovo. Each script filters to its respective product:

```bash
# Search Jira issues only
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py rovo "search query"

# Search Confluence pages only
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py rovo "search query"
```

Results are filtered by ARI (Atlassian Resource Identifier):
- `jira.py rovo` returns only results with `ari:cloud:jira:...`
- `confluence.py rovo` returns only results with `ari:cloud:confluence:...`

Output fields:
- `id` - Atlassian Resource Identifier (ARI)
- `type` - Content type
- `title` - Issue summary or page title
- `url` - Direct link
- `text` - Content preview (300 chars)

# Jira Commands

```bash
# List projects
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py projects

## List issue (ticket, task) types for a project
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py types PROJ

# Fetch a ticket
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py get PROJ-123

# Search with JQL
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py search "project=DEMO AND status='In Progress'"

# Get comments
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py comments PROJ-123

# List all statuses for issues (tickets) in a project
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py statuses PROJ
```

Common JQL examples:
- `assignee=currentUser()` - My assigned issues
- `project=PROJ AND sprint in openSprints()` - Current sprint
- `reporter=currentUser() AND created >= -7d` - My recent issues
- `labels=urgent AND status!=Done` - Urgent incomplete items

### Export issues to files
```bash
# Export to markdown files
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py export "project=DEMO" --format markdown --output-dir ./exports/

# Export to stdout (yaml default)
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py export "project=DEMO"

# Export to JSON
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py export "project=DEMO" --format json
```

## Edit

```bash
# Add comment to ticket
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py comment PROJ-123 "This is my comment"

# Get available transitions
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py transitions PROJ-123

# Transition ticket status
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py transition PROJ-123 "In Progress"

# Or by transition ID
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py transition PROJ-123 --id 21
```

## Create ticket
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py create PROJ --type Story --summary "My new story"
# With more options
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py create PROJ --type Bug --summary "Bug title" --description "Details here" --priority High --labels "bug,urgent"
# With custom fields (for project-specific required fields)
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py create PROJ --type Story --summary "My story" --field "Story Points=5" --field "Team=Platform"
```

## Edit ticket
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py edit PROJ-123 --summary "Updated title"
# Update multiple fields
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py edit PROJ-123 --summary "New title" --description "New description"
# Update custom fields
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py edit PROJ-123 --field "Story Points=8" --field "customfield_10001=value"
```

## Assign ticket
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py assign PROJ-123 <account_id>
# Assign to yourself
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py assign PROJ-123 --me
# Unassign
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py assign PROJ-123 --unassign
```

## List fields for an issue type
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py fields PROJ --type Story
```

## Get current user info
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py me
```

## Lookup user by name or email
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py lookup "John Doe"
```

# Confluence Commands

```bash
# Fetch a page
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py get 123456789

# Search with CQL
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py search "type=page AND space=TEAM"

# Get all descendant pages (uses CQL ancestor= query for complete results)
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py children 123456789

# List spaces
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py spaces
```

Common CQL examples:
- `type=page AND title~'architecture'` - Pages with "architecture" in title
- `space=TEAM AND lastModified >= now('-7d')` - Recent team pages
- `creator=currentUser()` - My pages
- `label='important'` - Pages with label

# Download page tree(s)
```bash
# Download a page and all its descendants with nested folders
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py tree 123456789 --output-dir ./exports/

# Download multiple page trees (e.g., sibling pages in a space)
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py tree 123456789 987654321 --output-dir ./exports/

# With JSON format instead of markdown
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py tree 123456789 --output-dir ./exports/ --format json

# Limit recursion depth
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py tree 123456789 --output-dir ./exports/ --max-depth 3
```

Creates properly nested folder structure with `toc.md` table of contents:
```
exports/
  toc.md                    # Table of contents with links
  Page_Title_123/
    index.md
    Child_Page_456/
      index.md
      Grandchild_789/
        index.md
```

# Export pages to files
```bash
# Export to markdown files
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py export "space=TEAM" --format markdown --output-dir ./exports/

# Export to stdout (yaml default)
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py export "type=page AND title~'architecture'"

# Export to JSON
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py export "space=TEAM" --format json
```

# Limitations

## Jira JQL search limited to 100 results
The Atlassian MCP server doesn't return pagination tokens for JQL search responses, so results are limited to 100 issues per query. For projects with more issues, use specific JQL filters:
```bash
# Filter by date range
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py search "project=PROJ AND created >= -30d"

# Filter by status
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py search "project=PROJ AND status='In Progress'"

# Filter by assignee
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py search "project=PROJ AND assignee=currentUser()"
```

## Confluence CQL search supports pagination
Confluence search properly paginates through all results. Use `--all` flag with search:
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/confluence.py search "space=TEAM" --all
```

# Troubleshooting

## "Not authenticated" error
Run the login command shown in Setup above.

## "Token expired" error
Run the login command again to re-authenticate. OAuth tokens auto-refresh, but refresh tokens can expire after extended periods of inactivity.

## "No cloud ID" error
Re-authenticate by running the login command shown in Setup above.

## "Permission denied" on write operations
Your OAuth token may lack write permissions. Re-authenticate to get new permissions:
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/auth.py login
```

## "Transition not found" error
The target status is not available from the current issue status. Use `transitions` command to see available options.

## "Required field missing" or field validation errors
Projects often have custom required fields (e.g., Story Points, Team). To discover required fields:
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py fields PROJ --type Story
```
Then add the required fields using `--field`:
```bash
uv run --directory ${OPENCODE_DIR}/skill/jira-confluence scripts/jira.py create PROJ --type Story --summary "Title" --field "customfield_10001=5"
```

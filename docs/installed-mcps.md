# Installed MCPs Index

Faithful inventory generated from `C:\Users\consa\.codex\config.toml`.

Count: 5 configured MCP servers.

| MCP | Transport | Endpoint / Command | Safe Notes | Why We Have It |
| --- | --- | --- | --- | --- |
| `figma` | remote URL | `https://mcp.figma.com/mcp` | No local secret stored in the repo mirror | Figma design sync and implementation workflows |
| `freepik` | stdio | `C:\Users\consa\.codex\tmp\freepik-mcp\.venv\Scripts\python.exe` + `C:\Users\consa\.codex\tmp\freepik-mcp\main.py` | Uses local Python runtime and local temp checkout | Asset and stock-style content workflows |
| `hostinger-mcp` | stdio | `npx hostinger-api-mcp@latest` | `API_TOKEN` stays only in local Codex config | Hostinger automation and account operations |
| `brevo` | stdio | `npx mcp-remote https://mcp.brevo.com/v1/brevo/mcp --header Authorization: Bearer ${BREVO_MCP_TOKEN}` | Token value is intentionally not mirrored here | Email marketing and automation via Brevo |
| `atlassian` | remote URL | `https://mcp.atlassian.com/v1/mcp` | Auth is handled separately in the local session | Jira and Confluence integration |

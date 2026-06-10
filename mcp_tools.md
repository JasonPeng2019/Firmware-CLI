# Per-User Dynamic Tools in an MCP Server

A guide to exposing different tools to different users from a single MCP server,
based on each user's identity, plan, permissions, or connected integrations.

## The two problems

Serving different tools to different users breaks down into two independent
problems. Solve them separately:

1. **Identity** — How does the server learn *who* the connected user is and what
   their setup looks like (plan, role, org, enabled integrations)?
2. **Tool variation** — How does the server return a *different* set of tools
   for that user, and update it if their context changes mid-session?

---

## Part 1 — Knowing who the user is

The approach depends on your transport.

### Remote server (Streamable HTTP)

This is where per-user differentiation is most natural, because the connection
can be authenticated and tied to an identity.

**OAuth 2.1** — The MCP spec supports OAuth for HTTP transports. The client sends
a bearer token; your server validates it and maps it to a user record. This is
the right choice when users log in through an identity provider.

**API key** — A simpler alternative: each user or tenant gets a key, and the
server maps the key to their context. Easy to implement and compatible with most
clients, at the cost of manual key distribution.

Either way, once the connection is authenticated you look the user up in your own
data store to get their entitlements:

```python
async def get_user_context(request):
    token = extract_bearer_token(request)        # or an API key header
    user_id = validate_and_decode(token)          # your auth logic
    return await db.load_user_context(user_id)    # plan, roles, integrations
```

### Local server (stdio)

For a locally-launched server, the identity is implicit — it's whoever started
the process. You don't discover the user at runtime; instead you pass their
configuration in at launch time via environment variables or arguments, set in
the client's server configuration:

```json
{
  "mcpServers": {
    "my-server": {
      "command": "my-mcp-server",
      "env": {
        "USER_PLAN": "pro",
        "ENABLED_INTEGRATIONS": "salesforce,github"
      }
    }
  }
}
```

Your server reads these at startup. Differentiation happens at install/config
time rather than dynamically.

> A `_meta` field is also available on RPC methods and some architectures use it
> to carry workspace or user context. Treat it as a secondary channel, not your
> primary authentication mechanism.

---

## Part 2 — Returning a different tool list

The key idea: **your `tools/list` handler does not have to return a static
array.** Compute the list at request time from the authenticated user's context,
returning only the tools that apply to them. The client — and the model — only
ever see the tools the user is entitled to.

Using the low-level Python SDK:

```python
from mcp.server import Server

app = Server("my-server")

@app.list_tools()
async def list_tools():
    user = await get_user_context(app.request_context)

    tools = [TOOL_SEARCH, TOOL_SUMMARIZE]          # available to everyone

    if user.has_role("admin"):
        tools += [TOOL_DELETE_RECORD, TOOL_MANAGE_USERS]

    if user.has_integration("salesforce"):
        tools += [TOOL_SALESFORCE_QUERY]

    return tools
```

The same pattern works in every SDK — TypeScript, Spring AI, FastMCP — since
`tools/list` is a protocol method the server controls. Higher-level frameworks
add conveniences (auth helpers, middleware, per-tool enable flags), but the
underlying mechanism is always "generate the list from context."

---

## Part 3 — Changing the tool list mid-session

If a user's entitlements can change *during* a live session — they upgrade their
plan, switch workspaces, or finish an authorization step — push a notification
instead of waiting for them to reconnect.

The flow:

1. Your server detects the change.
2. It sends a `notifications/tools/list_changed` message to the client.
3. A compliant client re-calls `tools/list`.
4. Your handler returns the newly-applicable set.

```python
# after the user's context changes
await app.request_context.session.send_tool_list_changed()
```

If your tool set only ever differs *between* sessions (computed fresh when the
user authenticates), you don't need this notification at all.

---

## Two things to get right from the start

### Enforce authorization at call time, not just at listing

Filtering `tools/list` is a discovery and UX improvement — it is **not** a
security boundary. A client could call a tool name it was never shown. Always
re-check the user's authorization inside your `tools/call` handler before
executing anything sensitive:

```python
@app.call_tool()
async def call_tool(name, arguments):
    user = await get_user_context(app.request_context)

    if name in ADMIN_TOOLS and not user.has_role("admin"):
        raise PermissionError(f"{name} is not available to this user")

    return await dispatch(name, arguments)
```

Treat the filtered list as convenience and the call-time check as the real gate.

### Client support for `list_changed` varies

Not every host application re-fetches the tool list reliably when it receives the
notification. The static, per-session filtering approach (Part 2) is universally
reliable. The mid-session refresh (Part 3) depends on the client, so test it
against the specific clients you intend to support before relying on it.

---

## Summary checklist

- [ ] Pick a transport: remote (HTTP + OAuth/API key) for true per-user, or local
      (stdio + env config) for per-install differentiation.
- [ ] Authenticate the connection and load the user's context from your store.
- [ ] Make `tools/list` compute the tool array from that context.
- [ ] Enforce authorization independently inside `tools/call`.
- [ ] Add `notifications/tools/list_changed` only if entitlements change within a
      session, and verify your target clients honor it.

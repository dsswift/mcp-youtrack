# API Reference

Complete reference for all MCP YouTrack tools.

## Issue Operations

### search_issues

Search for issues in YouTrack with flexible filtering.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `project` | string | No | - | Project short name (e.g., 'OPS') |
| `assignee` | string | No | - | Filter by assignee username |
| `state` | string | No | - | Filter by state name (e.g., 'In Progress', 'Open') |
| `domain` | string | No | - | Filter by domain field |
| `query` | string | No | - | Additional YouTrack search query |
| `limit` | integer | No | 25 | Maximum results (1-100) |

**Returns:** JSON object with `count`, `query`, and `issues` array.

**Examples:**

```python
# All issues in a project
search_issues(project="OPS")

# User's in-progress tasks
search_issues(assignee="jsmith", state="In Progress")

# Using YouTrack query syntax
search_issues(query="#Unresolved created: today")

# Combine filters
search_issues(project="HD", state="New", limit=10)
```

**Query Syntax Notes:**

- States with spaces use `#{State Name}` syntax internally
- Domain filters use `Domain: {value}` syntax
- Assignee uses `for: username` syntax
- All filters are combined with spaces (AND logic)

---

### get_issue

Get detailed information about a specific issue.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID (e.g., 'OPS-123' or database ID) |

**Returns:** JSON object with full issue details including custom fields.

**Example:**

```python
get_issue(issue_id="OPS-123")
```

**Response Fields:**

- `id` - Readable issue ID
- `summary` - Issue title
- `description` - Full description (if present)
- `project` - Project short name
- `reporter` - Reporter name
- `created` - Creation timestamp (ISO format)
- `updated` - Last update timestamp
- Custom fields by name (State, Assignee, Priority, etc.)

---

### create_issue

Create a new issue in YouTrack.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `summary` | string | Yes | Issue title/summary |
| `description` | string | No | Detailed description (supports markdown) |
| `project` | string | No | Project short name. Uses `YOUTRACK_DEFAULT_PROJECT` if not specified |
| `type` | string | No | Type name (e.g., 'Bug', 'Task', 'Feature') |

**Returns:** JSON object with created issue details and `_created: true` flag.

**Examples:**

```python
# Minimal issue
create_issue(summary="Fix login timeout")

# With description and type
create_issue(
    project="OPS",
    summary="Add dark mode support",
    description="## Requirements\n- Toggle in settings\n- Persist preference",
    type="Feature"
)

# Create a bug report
create_issue(
    project="OPS",
    summary="Login timeout after 5 minutes",
    type="Bug"
)
```

**Error Cases:**

- Returns error if no project specified and `YOUTRACK_DEFAULT_PROJECT` not configured
- Returns error if project not found

---

### update_issue

Update an existing issue's fields.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID to update (e.g., 'OPS-123') |
| `summary` | string | No | New summary/title |
| `description` | string | No | New description |
| `state` | string | No | New state (e.g., 'Open', 'In Progress', 'Done') |
| `assignee` | string | No | Assignee login name |
| `domain` | string | No | Domain name |
| `type` | string | No | Type name (e.g., 'Bug', 'Task', 'Feature') |

**Returns:** JSON object with updated issue details and `_updated: true` flag.

**Examples:**

```python
# Update state only
update_issue(issue_id="OPS-123", state="In Progress")

# Update multiple fields
update_issue(
    issue_id="OPS-123",
    summary="Updated title",
    state="Done",
    assignee="jsmith"
)

# Change issue type
update_issue(issue_id="OPS-123", type="Bug")
```

**Implementation Notes:**

- State, assignee, domain, and type changes use YouTrack command API
- Summary and description use direct field updates
- Both can be combined in a single call

---

### delete_issue

Permanently delete an issue.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID to delete (e.g., 'OPS-123') |

**Returns:** JSON object confirming deletion with `deleted: true`.

**Example:**

```python
delete_issue(issue_id="OPS-123")
```

**Warning:** This operation cannot be undone. The issue will be permanently deleted.

---

## Project Operations

### list_projects

List all accessible YouTrack projects.

**Parameters:** None

**Returns:** JSON object with `count` and `projects` array (excludes archived projects).

**Response Fields per Project:**

- `id` - Database ID
- `shortName` - Project short name (e.g., 'OPS')
- `name` - Full project name
- `description` - Project description

---

### get_project_fields

Get custom field definitions for a project.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `project` | string | Yes | Project short name (e.g., 'OPS') |

**Returns:** JSON object with project name and `fields` array.

**Response Fields per Field:**

- `id` - Field ID
- `name` - Field name (e.g., 'State', 'Priority')
- `required` - Whether field is required
- `emptyFieldText` - Placeholder text when empty
- `values` - Array of possible values (for enum fields)

**Example:**

```python
get_project_fields(project="OPS")
```

This is useful for discovering available states, priorities, and other custom fields before creating or updating issues.

---

## Comment Operations

### add_comment

Add a comment to an issue.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID to comment on (e.g., 'OPS-123') |
| `text` | string | Yes | Comment text (supports markdown) |

**Returns:** JSON object with created comment details and `_created: true` flag.

**Example:**

```python
add_comment(
    issue_id="OPS-123",
    text="Fixed in commit abc123. Ready for review."
)
```

---

### list_comments

Get all comments on an issue.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID to get comments for |

**Returns:** JSON object with `issue_id`, `count`, and `comments` array.

**Response Fields per Comment:**

- `id` - Comment ID
- `text` - Comment content
- `author` - Author name
- `created` - Creation timestamp
- `updated` - Last update timestamp (if edited)

---

### delete_comment

Delete a comment from an issue.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID the comment belongs to |
| `comment_id` | string | Yes | Comment ID to delete |

**Returns:** JSON object confirming deletion with `deleted: true`.

**Example:**

```python
delete_comment(issue_id="OPS-123", comment_id="4-123")
```

**Warning:** This operation cannot be undone.

---

## Issue Linking

### list_link_types

Get available issue link types.

**Parameters:** None

**Returns:** JSON object with `count` and `link_types` array.

**Common Link Types:**

| Name | Source to Target | Target to Source | Directed |
|------|-----------------|------------------|----------|
| Depend | depends on | is required for | Yes |
| Duplicate | duplicates | is duplicated by | Yes |
| Relate | relates to | relates to | No |
| Subtask | subtask of | parent for | Yes |

---

### list_issue_links

Get all links for an issue.

**Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `issue_id` | string | Yes | Issue ID to get links for |

**Returns:** JSON object with links grouped by type and direction.

**Response Fields per Link:**

- `id` - Link ID
- `direction` - 'OUTWARD' or 'INWARD'
- `linkType` - Link type name
- `linkLabel` - Human-readable label for this direction
- `issues` - Array of linked issues with `id` and `summary`

---

### add_issue_link

Create a link between two issues.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `issue_id` | string | Yes | - | Source issue ID |
| `target_issue_id` | string | Yes | - | Target issue ID |
| `link_type` | string | No | 'Depend' | Link type name |

**Returns:** JSON object confirming link creation.

**Examples:**

```python
# OPS-123 depends on OPS-456
add_issue_link("OPS-123", "OPS-456", "Depend")

# Mark as duplicate
add_issue_link("OPS-789", "OPS-123", "Duplicate")

# Create subtask relationship
add_issue_link("OPS-124", "OPS-100", "Subtask")
```

---

### remove_issue_link

Remove a link between two issues.

**Parameters:**

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `issue_id` | string | Yes | - | Source issue ID |
| `target_issue_id` | string | Yes | - | Target issue ID |
| `link_type` | string | No | 'Depend' | Link type name |

**Returns:** JSON object confirming link removal.

---

## Error Handling

All tools return JSON responses. On error, the response includes an `error` field:

```json
{
  "error": "Issue 'OPS-999' not found"
}
```

**Common Error Types:**

| Error | Cause |
|-------|-------|
| Authentication failed | Invalid or expired `YOUTRACK_TOKEN` |
| Permission denied | Token lacks required permissions |
| Resource not found | Issue, project, or comment doesn't exist |
| API error | General YouTrack API error with details |

## Rate Limiting

The client uses standard HTTP timeouts (configurable via `YOUTRACK_TIMEOUT`). YouTrack Cloud has rate limits; if you encounter 429 errors, reduce request frequency.

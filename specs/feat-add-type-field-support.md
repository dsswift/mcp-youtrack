# Add Type Field Support to Issue Operations

| Field | Value |
|-------|-------|
| ID | feat-add-type-field-support |
| Type | feature |
| Created | 2025-12-20 |

## Problem Statement

Currently, the YouTrack MCP server does not expose the "Type" custom field when creating or updating issues. This prevents AI agents using the MCP tools from setting issue types (e.g., Bug, Task, Feature) when creating or modifying issues. Users who ask AI to create bugs or other specific issue types cannot have that field automatically populated, requiring manual post-creation editing in YouTrack.

## Proposed Solution

Add a `type` parameter to both `create_issue` and `update_issue` MCP tools that allows callers to specify the issue Type field value. This will use the existing YouTrack command execution mechanism (similar to how State, Assignee, and Domain are handled in `update_issue`) to set the Type field.

## Requirements

- Add optional `type` parameter to `create_issue` tool
- Add optional `type` parameter to `update_issue` tool
- Use YouTrack command API (`Type: <value>`) to set the field
- Handle Type field consistently with other custom fields (State, Domain, Assignee)
- Validate that Type values are set via command after issue creation/update
- Update tool documentation to reflect new parameter
- Maintain backward compatibility (parameter is optional)

## Relevant Files

- `src/mcp_youtrack/server.py:217-262` - `create_issue` function
- `src/mcp_youtrack/server.py:265-322` - `update_issue` function
- `src/mcp_youtrack/client.py:350-377` - `execute_command` method
- `docs/api-reference.md` - API documentation (likely exists based on README reference)

## Implementation Plan

### Phase 1: Add Type Parameter to Update Issue

- [ ] Add `type: str | None = None` parameter to `update_issue` function in server.py:265
- [ ] Add Type command to command list in server.py:292-299 when `type` is provided
- [ ] Update tool docstring to document the new parameter with examples
- [ ] Test update_issue with type parameter

### Phase 2: Add Type Parameter to Create Issue

- [ ] Add `type: str | None = None` parameter to `create_issue` function in server.py:217
- [ ] Execute Type command after issue creation if `type` is provided
- [ ] Update tool docstring to document the new parameter with examples
- [ ] Test create_issue with type parameter

### Phase 3: Documentation

- [ ] Update API reference documentation (docs/api-reference.md) with Type parameter for both tools
- [ ] Add usage examples showing Type field in action

## Validation

- [ ] Create issue without Type parameter succeeds (backward compatibility)
- [ ] Create issue with Type parameter sets the field correctly
- [ ] Update issue with Type parameter changes the field correctly
- [ ] Type field appears in issue response after creation/update
- [ ] Invalid Type values produce appropriate error messages

## Validation Commands

- `uv run python scripts/verify_tools.py --project TEST` - Run integration tests against live YouTrack
- Manual test: Create issue with type parameter and verify in YouTrack UI
- Manual test: Update issue type and verify change in YouTrack UI

## Notes

- Type is a custom field in YouTrack, handled via command API like State, Domain, and Assignee
- The available Type values are project-specific and can be discovered via `get_project_fields`
- Type is commonly used to distinguish Bug, Task, Feature, Epic, etc.
- Implementation pattern should match existing Domain field handling for consistency

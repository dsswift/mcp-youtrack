#!/usr/bin/env python3
"""Import GitHub issues to YouTrack.

Migrates open GitHub issues from a GitHub repository to YouTrack.

Usage:
    python import-github-issues.py [--dry-run] [--project PROJECT]

Environment Variables:
    YOUTRACK_URL    - YouTrack instance URL (required)
    YOUTRACK_TOKEN  - API token (required)

Requires:
    - gh CLI authenticated with repo access
    - httpx package
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from typing import Any

import httpx


@dataclass
class GitHubIssue:
    """GitHub issue data."""

    number: int
    title: str
    body: str | None
    labels: list[str]
    state: str
    url: str


def get_youtrack_config() -> tuple[str, str]:
    """Get YouTrack configuration from environment."""
    url = os.getenv("YOUTRACK_URL")
    token = os.getenv("YOUTRACK_TOKEN")

    if not url:
        print("Error: YOUTRACK_URL environment variable is required", file=sys.stderr)
        sys.exit(1)
    if not token:
        print("Error: YOUTRACK_TOKEN environment variable is required", file=sys.stderr)
        sys.exit(1)

    return url.rstrip("/"), token


def fetch_github_issues() -> list[GitHubIssue]:
    """Fetch open issues from GitHub using gh CLI."""
    print("Fetching GitHub issues...")

    try:
        result = subprocess.run(
            [
                "gh",
                "issue",
                "list",
                "--state",
                "open",
                "--json",
                "number,title,body,labels,state,url",
                "--limit",
                "100",
            ],
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Error fetching GitHub issues: {e.stderr}", file=sys.stderr)
        sys.exit(1)
    except FileNotFoundError:
        print("Error: gh CLI not found. Install GitHub CLI first.", file=sys.stderr)
        sys.exit(1)

    issues_data = json.loads(result.stdout)
    issues: list[GitHubIssue] = []

    for item in issues_data:
        labels = [label["name"] for label in item.get("labels", [])]
        issues.append(
            GitHubIssue(
                number=item["number"],
                title=item["title"],
                body=item.get("body"),
                labels=labels,
                state=item["state"],
                url=item["url"],
            )
        )

    print(f"Found {len(issues)} open issues")
    return issues


def map_labels_to_domain(labels: list[str], domain_map: dict[str, str]) -> str | None:
    """Map GitHub labels to YouTrack Domain field.

    Args:
        labels: List of GitHub labels
        domain_map: Mapping from label names to domain values

    Returns:
        Domain value if found, None otherwise
    """
    for label in labels:
        label_lower = label.lower()
        if label_lower in domain_map:
            return domain_map[label_lower]

    return None


def create_youtrack_issue(
    client: httpx.Client,
    project_id: str,
    title: str,
    description: str | None,
    domain: str | None = None,
) -> dict[str, Any]:
    """Create an issue in YouTrack."""
    payload: dict[str, Any] = {
        "project": {"id": project_id},
        "summary": title,
    }

    if description:
        payload["description"] = description

    response = client.post(
        "/issues",
        json=payload,
        params={"fields": "id,idReadable,summary"},
    )

    if not response.is_success:
        raise Exception(f"Failed to create issue: {response.text}")

    issue = response.json()

    # Set domain via command if specified
    if domain:
        command_payload = {
            "query": f"Domain: {domain}",
            "issues": [{"idReadable": issue["idReadable"]}],
        }
        client.post("/commands", json=command_payload)

    return issue


def add_github_comment(issue_number: int, youtrack_id: str) -> bool:
    """Add a comment on the GitHub issue noting migration."""
    comment = f"Migrated to YouTrack: {youtrack_id}"

    try:
        subprocess.run(
            ["gh", "issue", "comment", str(issue_number), "--body", comment],
            capture_output=True,
            check=True,
        )
        return True
    except subprocess.CalledProcessError:
        return False


def get_project_id(client: httpx.Client, short_name: str) -> str:
    """Get the project database ID from short name."""
    response = client.get(
        f"/admin/projects/{short_name}",
        params={"fields": "id,shortName"},
    )

    if not response.is_success:
        raise Exception(f"Project '{short_name}' not found: {response.text}")

    return response.json()["id"]


def main() -> None:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Import GitHub issues to YouTrack")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be imported without making changes",
    )
    parser.add_argument(
        "--project",
        required=True,
        help="YouTrack project short name (e.g., 'OPS', 'MYPROJECT')",
    )
    parser.add_argument(
        "--skip-comment",
        action="store_true",
        help="Skip adding migration comment to GitHub issues",
    )
    parser.add_argument(
        "--domain-map",
        type=str,
        help="JSON file containing label-to-domain mapping",
    )
    args = parser.parse_args()

    url, token = get_youtrack_config()

    # Load domain mapping if provided
    domain_map: dict[str, str] = {}
    if args.domain_map:
        try:
            with open(args.domain_map) as f:
                domain_map = json.load(f)
            print(f"Loaded domain mapping from {args.domain_map}")
        except Exception as e:
            print(f"Warning: Could not load domain mapping: {e}", file=sys.stderr)

    # Fetch GitHub issues first
    issues = fetch_github_issues()

    if not issues:
        print("No open issues to import")
        return

    if args.dry_run:
        print("\n=== DRY RUN - No changes will be made ===\n")
        for issue in issues:
            domain = map_labels_to_domain(issue.labels, domain_map)
            print(f"Would import: #{issue.number} - {issue.title}")
            print(f"  Labels: {', '.join(issue.labels) or '(none)'}")
            print(f"  Domain: {domain or '(none)'}")
            print()
        print(f"Total: {len(issues)} issues would be imported")
        return

    # Create YouTrack client
    with httpx.Client(
        base_url=f"{url}/api",
        headers={
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        },
        timeout=30,
    ) as client:
        # Get project ID
        try:
            project_id = get_project_id(client, args.project)
            print(f"Target project: {args.project} ({project_id})")
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            sys.exit(1)

        # Import each issue
        mapping: dict[int, str] = {}
        errors: list[tuple[int, str]] = []

        for issue in issues:
            domain = map_labels_to_domain(issue.labels, domain_map)

            # Build description with original GitHub reference
            description_parts: list[str] = []
            if issue.body:
                description_parts.append(issue.body)
            description_parts.append(f"\n\n---\n*Migrated from GitHub: {issue.url}*")
            description = "\n".join(description_parts)

            try:
                yt_issue = create_youtrack_issue(
                    client,
                    project_id,
                    issue.title,
                    description,
                    domain,
                )
                yt_id = yt_issue["idReadable"]
                mapping[issue.number] = yt_id
                print(f"Created: #{issue.number} -> {yt_id}")

                # Add comment to GitHub issue
                if not args.skip_comment:
                    if add_github_comment(issue.number, yt_id):
                        print(f"  Added migration comment to GitHub #{issue.number}")
                    else:
                        print(f"  Warning: Could not add comment to GitHub #{issue.number}")

            except Exception as e:
                errors.append((issue.number, str(e)))
                print(f"Error importing #{issue.number}: {e}")

        # Summary
        print("\n=== Import Summary ===")
        print(f"Imported: {len(mapping)} issues")
        print(f"Errors: {len(errors)} issues")

        if mapping:
            print("\nMapping (GitHub -> YouTrack):")
            for gh_num, yt_id in sorted(mapping.items()):
                print(f"  #{gh_num} -> {yt_id}")

        if errors:
            print("\nFailed imports:")
            for gh_num, error in errors:
                print(f"  #{gh_num}: {error}")


if __name__ == "__main__":
    main()

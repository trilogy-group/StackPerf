#!/usr/bin/env python3
"""Helper script for Linear GraphQL API interactions."""

import json
import os
import sys
from typing import Any

import requests

LINEAR_API_URL = "https://api.linear.app/graphql"


def get_api_key() -> str:
    """Get Linear API key from environment."""
    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        print("ERROR: LINEAR_API_KEY environment variable not set", file=sys.stderr)
        sys.exit(1)
    return api_key


def linear_query(query: str, variables: dict[str, Any] | None = None) -> dict[str, Any]:
    """Execute a Linear GraphQL query."""
    headers = {
        "Authorization": get_api_key(),
        "Content-Type": "application/json",
    }

    payload = {"query": query}
    if variables:
        payload["variables"] = variables

    response = requests.post(LINEAR_API_URL, headers=headers, json=payload, timeout=30)

    if response.status_code != 200:
        print(f"ERROR: Linear API returned status {response.status_code}", file=sys.stderr)
        print(f"Response: {response.text}", file=sys.stderr)
        sys.exit(1)

    result = response.json()

    if "errors" in result:
        print("ERROR: GraphQL query returned errors:", file=sys.stderr)
        for error in result["errors"]:
            print(f"  - {error.get('message', error)}", file=sys.stderr)
        sys.exit(1)

    return result["data"]


def get_issue(issue_id: str) -> dict[str, Any]:
    """Fetch issue by ID."""
    query = """
    query GetIssue($id: String!) {
        issue(id: $id) {
            id
            identifier
            title
            description
            state {
                id
                name
                type
            }
            labels {
                nodes {
                    id
                    name
                }
            }
            url
            comments {
                nodes {
                    id
                    body
                    createdAt
                    user {
                        id
                        name
                    }
                    resolvedAt
                }
            }
        }
    }
    """
    data = linear_query(query, {"id": issue_id})
    return data.get("issue", {})


def update_issue_state(issue_id: str, state_id: str) -> dict[str, Any]:
    """Update issue state."""
    mutation = """
    mutation UpdateIssueState($id: String!, $stateId: String!) {
        issueUpdate(id: $id, input: { stateId: $stateId }) {
            success
            issue {
                id
                identifier
                state {
                    id
                    name
                    type
                }
            }
        }
    }
    """
    data = linear_query(mutation, {"id": issue_id, "stateId": state_id})
    return data.get("issueUpdate", {})


def create_comment(issue_id: str, body: str) -> dict[str, Any]:
    """Create a comment on an issue."""
    mutation = """
    mutation CreateComment($issueId: String!, $body: String!) {
        commentCreate(input: { issueId: $issueId, body: $body }) {
            success
            comment {
                id
                body
                createdAt
                user {
                    id
                    name
                }
            }
        }
    }
    """
    data = linear_query(mutation, {"issueId": issue_id, "body": body})
    return data.get("commentCreate", {})


def update_comment(comment_id: str, body: str) -> dict[str, Any]:
    """Update an existing comment."""
    mutation = """
    mutation UpdateComment($id: String!, $body: String!) {
        commentUpdate(id: $id, input: { body: $body }) {
            success
            comment {
                id
                body
                updatedAt
            }
        }
    }
    """
    data = linear_query(mutation, {"id": comment_id, "body": body})
    return data.get("commentUpdate", {})


def get_team_states(team_id: str = "trilogy-ai-coe") -> list[dict[str, Any]]:
    """Get all workflow states for a team."""
    query = """
    query GetTeamStates {
        teams {
            nodes {
                id
                key
                states {
                    nodes {
                        id
                        name
                        type
                        color
                    }
                }
            }
        }
    }
    """
    data = linear_query(query)
    teams = data.get("teams", {}).get("nodes", [])
    # Find the team by key
    for team in teams:
        if team.get("key") == team_id:
            states = team.get("states", {}).get("nodes", [])
            return states
    # If not found by key, return all states from all teams
    all_states = []
    for team in teams:
        all_states.extend(team.get("states", {}).get("nodes", []))
    return all_states


def main() -> None:
    """Main entry point for CLI usage."""
    if len(sys.argv) < 2:
        print("Usage: linear_helper.py <command> [args]", file=sys.stderr)
        print("Commands: get-issue, update-state, create-comment, update-comment, list-states", file=sys.stderr)
        sys.exit(1)

    command = sys.argv[1]

    if command == "get-issue":
        if len(sys.argv) < 3:
            print("Usage: linear_helper.py get-issue <issue-id>", file=sys.stderr)
            sys.exit(1)
        issue = get_issue(sys.argv[2])
        print(json.dumps(issue, indent=2))

    elif command == "update-state":
        if len(sys.argv) < 4:
            print("Usage: linear_helper.py update-state <issue-id> <state-id>", file=sys.stderr)
            sys.exit(1)
        result = update_issue_state(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "create-comment":
        if len(sys.argv) < 4:
            print("Usage: linear_helper.py create-comment <issue-id> <body>", file=sys.stderr)
            sys.exit(1)
        result = create_comment(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "update-comment":
        if len(sys.argv) < 4:
            print("Usage: linear_helper.py update-comment <comment-id> <body>", file=sys.stderr)
            sys.exit(1)
        result = update_comment(sys.argv[2], sys.argv[3])
        print(json.dumps(result, indent=2))

    elif command == "list-states":
        team_id = sys.argv[2] if len(sys.argv) > 2 else "trilogy-ai-coe"
        states = get_team_states(team_id)
        print(json.dumps(states, indent=2))

    else:
        print(f"Unknown command: {command}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()

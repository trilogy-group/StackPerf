#!/usr/bin/env python3
"""Linear API client for interacting with Linear issues."""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any, List


class LinearClient:
    """Client for Linear GraphQL API."""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.environ.get("LINEAR_API_KEY")
        if not self.api_key:
            raise ValueError("LINEAR_API_KEY not provided and not in environment")
        self.endpoint = "https://api.linear.app/graphql"
        self.headers = {
            "Authorization": self.api_key,
            "Content-Type": "application/json",
        }
    
    def _execute(self, query: str, variables: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute a GraphQL query."""
        data = {"query": query}
        if variables:
            data["variables"] = variables
        
        req = urllib.request.Request(
            self.endpoint,
            data=json.dumps(data).encode("utf-8"),
            headers=self.headers,
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                result = json.loads(response.read().decode("utf-8"))
                if "errors" in result:
                    raise Exception(f"GraphQL errors: {result['errors']}")
                return result["data"]
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8")
            raise Exception(f"HTTP {e.code}: {error_body}")
    
    def get_issue(self, issue_id: str) -> Dict[str, Any]:
        """Get issue by ID."""
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
                branchName
                attachments {
                    nodes {
                        id
                        title
                        url
                    }
                }
            }
        }
        """
        result = self._execute(query, {"id": issue_id})
        return result.get("issue", {})
    
    def get_issue_comments(self, issue_id: str) -> List[Dict[str, Any]]:
        """Get comments for an issue."""
        query = """
        query GetIssueComments($id: String!) {
            issue(id: $id) {
                comments {
                    nodes {
                        id
                        body
                        resolvedAt
                        user {
                            id
                            name
                        }
                        createdAt
                    }
                }
            }
        }
        """
        result = self._execute(query, {"id": issue_id})
        return result.get("issue", {}).get("comments", {}).get("nodes", [])
    
    def update_issue_state(self, issue_id: str, state_id: str) -> Dict[str, Any]:
        """Update issue state."""
        query = """
        mutation UpdateIssueState($id: String!, $stateId: String!) {
            issueUpdate(id: $id, input: {stateId: $stateId}) {
                success
                issue {
                    id
                    identifier
                    state {
                        id
                        name
                    }
                }
            }
        }
        """
        result = self._execute(query, {"id": issue_id, "stateId": state_id})
        return result.get("issueUpdate", {})
    
    def create_comment(self, issue_id: str, body: str) -> Dict[str, Any]:
        """Create a comment on an issue."""
        query = """
        mutation CreateComment($issueId: String!, $body: String!) {
            commentCreate(input: {issueId: $issueId, body: $body}) {
                success
                comment {
                    id
                    body
                }
            }
        }
        """
        result = self._execute(query, {"issueId": issue_id, "body": body})
        return result.get("commentCreate", {})
    
    def update_comment(self, comment_id: str, body: str) -> Dict[str, Any]:
        """Update an existing comment."""
        query = """
        mutation UpdateComment($id: String!, $body: String!) {
            commentUpdate(id: $id, input: {body: $body}) {
                success
                comment {
                    id
                    body
                }
            }
        }
        """
        result = self._execute(query, {"id": comment_id, "body": body})
        return result.get("commentUpdate", {})
    
    def get_workflow_states(self, team_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get workflow states."""
        query = """
        query GetWorkflowStates {
            workflowStates {
                nodes {
                    id
                    name
                    type
                    color
                }
            }
        }
        """
        result = self._execute(query)
        return result.get("workflowStates", {}).get("nodes", [])


def main():
    """Main function for command-line usage."""
    if len(sys.argv) < 3:
        print("Usage: linear_client.py <command> <issue_id> [args...]")
        print("Commands: get, comments, update-state, create-comment, update-comment")
        sys.exit(1)
    
    command = sys.argv[1]
    issue_id = sys.argv[2]
    
    client = LinearClient()
    
    if command == "get":
        issue = client.get_issue(issue_id)
        print(json.dumps(issue, indent=2))
    
    elif command == "comments":
        comments = client.get_issue_comments(issue_id)
        print(json.dumps(comments, indent=2))
    
    elif command == "update-state":
        if len(sys.argv) < 4:
            print("Usage: linear_client.py update-state <issue_id> <state_id>")
            sys.exit(1)
        state_id = sys.argv[3]
        result = client.update_issue_state(issue_id, state_id)
        print(json.dumps(result, indent=2))
    
    elif command == "create-comment":
        if len(sys.argv) < 4:
            print("Usage: linear_client.py create-comment <issue_id> <body>")
            sys.exit(1)
        body = sys.argv[3]
        result = client.create_comment(issue_id, body)
        print(json.dumps(result, indent=2))
    
    elif command == "update-comment":
        if len(sys.argv) < 5:
            print("Usage: linear_client.py update-comment <issue_id> <comment_id> <body>")
            sys.exit(1)
        comment_id = sys.argv[3]
        body = sys.argv[4]
        result = client.update_comment(comment_id, body)
        print(json.dumps(result, indent=2))
    
    elif command == "states":
        team_id = sys.argv[2] if len(sys.argv) > 2 else None
        states = client.get_workflow_states(team_id)
        print(json.dumps(states, indent=2))
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
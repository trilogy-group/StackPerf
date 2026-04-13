# OpenHands PR Review Setup

This repository was bootstrapped with OpenHands PR review support via `opensymphony init`.

Useful references:

- Plugin page: https://github.com/OpenHands/extensions/tree/main/plugins/pr-review
- Official docs: https://docs.openhands.dev/sdk/guides/github-workflows/pr-review

## Files Added

- `.github/workflows/ai-pr-review.yml`
- `.agents/skills/custom-codereview-guide.md`

## GitHub Actions Secret

Add this repository secret under **Settings -> Secrets and variables -> Actions**:

| Name | Value |
|------|-------|
| `AI_REVIEW_API_KEY` | Your AI review provider API key |

The secret name is provider-agnostic. Fireworks is only the default example
configuration for new repos; any compatible provider/model is fine.

## GitHub Actions Variables

Add these repository variables under **Settings -> Secrets and variables -> Actions -> Variables**:

| Name | Value |
|------|-------|
| `AI_REVIEW_PROVIDER_KIND` | `openai-compatible` |
| `AI_REVIEW_MODEL_ID` | `accounts/fireworks/models/glm-5p1` |
| `AI_REVIEW_BASE_URL` | `https://api.fireworks.ai/inference/v1` |
| `AI_REVIEW_STYLE` | `standard` |
| `AI_REVIEW_REQUIRE_EVIDENCE` | `true` |

## Label

Create the `review-this` label so maintainers can retrigger review on demand.

```bash
gh label create 'review-this' --description 'Trigger AI PR review' --color 'd73a4a' || true
```

## Optional GitHub CLI Commands

```bash
gh variable set AI_REVIEW_PROVIDER_KIND --body 'openai-compatible'
gh variable set AI_REVIEW_MODEL_ID --body 'accounts/fireworks/models/glm-5p1'
gh variable set AI_REVIEW_BASE_URL --body 'https://api.fireworks.ai/inference/v1'
gh variable set AI_REVIEW_STYLE --body 'standard'
gh variable set AI_REVIEW_REQUIRE_EVIDENCE --body 'true'
gh secret set AI_REVIEW_API_KEY
```

## Notes

- Fireworks is the default example only; swap in your preferred provider/model if needed.
- If your provider uses an OpenAI-compatible endpoint, `AI_REVIEW_BASE_URL` must be set.
- If your organization restricts Actions, allow `OpenHands/extensions`.
- The generated workflow should already pin the plugin to `9e5bb49dbe61bdb364c89c10c7307c38139e9532` in both the `uses:` line and the `extensions-version:` input.
- Do not make the AI review workflow a required status check.
- Keep the workflow on GitHub-hosted runners unless you have separately reviewed the risk model for untrusted PR content.

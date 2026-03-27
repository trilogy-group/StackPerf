#!/usr/bin/env python3
"""Demo script showing session-scoped proxy credential issuance and aliasing.

This script demonstrates the end-to-end credential flow:
1. Issue a session-scoped proxy credential with key alias and metadata tags
2. Show the credential structure (with redacted secret)
3. Render environment variable snippets for harness configuration
4. Validate the credential metadata can be correlated back to the session

Usage:
    PYTHONPATH=src python scripts/demo_credential_service.py

Output:
    Demonstrates credential issuance with key aliasing convention and metadata tagging.
"""

import asyncio
import sys
from pathlib import Path
from uuid import UUID, uuid4

# Add src to path for imports
src_path = Path(__file__).parent.parent / "src"
if str(src_path) not in sys.path:
    sys.path.insert(0, str(src_path))

from benchmark_core.models import ProxyCredential
from benchmark_core.services import CredentialService


async def demo_credential_issuance():
    """Demonstrate full credential issuance flow."""
    print("=" * 70)
    print("COE-310: Session-Scoped Proxy Credential Issuance Demo")
    print("=" * 70)

    # Initialize service
    service = CredentialService()

    # Simulate session context
    session_id = uuid4()
    experiment_id = "exp-claude-code-comparison"
    variant_id = "var-claude-3-5-sonnet"
    harness_profile = "claude-code"

    print(f"\n1. Session Context:")
    print(f"   Session ID: {session_id}")
    print(f"   Experiment: {experiment_id}")
    print(f"   Variant: {variant_id}")
    print(f"   Harness Profile: {harness_profile}")

    # Issue credential
    print(f"\n2. Issuing Proxy Credential...")
    credential = await service.issue_credential(
        session_id=session_id,
        experiment_id=experiment_id,
        variant_id=variant_id,
        harness_profile=harness_profile,
        ttl_hours=24,
    )

    print(f"   ✓ Credential issued")
    print(f"   ✓ Credential ID: {credential.credential_id}")
    print(f"   ✓ Session ID: {credential.session_id}")

    # Show key alias (for correlation)
    print(f"\n3. Key Aliasing Convention:")
    print(f"   Key Alias: {credential.key_alias}")
    print(f"   Format: session-{{session_id[:8]}}-{{experiment_id[:8]}}-{{variant_id[:8]}}")

    # Verify alias contains session reference
    session_prefix = str(session_id)[:8]
    assert session_prefix in credential.key_alias, "Session reference missing from alias"
    print(f"   ✓ Alias contains session reference: {session_prefix}")

    # Show metadata tags
    print(f"\n4. Metadata Tags (for LiteLLM correlation):")
    metadata = service._build_metadata_tags(
        session_id, experiment_id, variant_id, harness_profile
    )
    for key, value in metadata.items():
        print(f"   {key}: {value}")

    # Verify metadata can join back to session
    assert metadata["benchmark_session_id"] == str(session_id)
    assert metadata["benchmark_experiment_id"] == experiment_id
    assert metadata["benchmark_variant_id"] == variant_id
    print(f"   ✓ All metadata tags present for correlation")

    # Show API key (redacted)
    print(f"\n5. API Key (Secret Handling):")
    print(f"   Key Type: {type(credential.api_key).__name__}")
    print(f"   Redacted Preview: {credential.get_redacted_key()}")
    print(f"   ✓ SecretStr prevents accidental plaintext exposure")

    # Show expiration
    print(f"\n6. Credential Expiration:")
    print(f"   Created: {credential.created_at}")
    print(f"   Expires: {credential.expires_at}")
    print(f"   Is Active: {credential.is_active}")

    # Render environment snippets
    print(f"\n7. Environment Variable Snippets:")
    proxy_url = "http://localhost:4000"
    model = "claude-3-5-sonnet-20241022"

    env_vars = service.render_env_snippet(
        credential=credential,
        proxy_base_url=proxy_url,
        model=model,
    )

    print(f"\n   Shell Export Format:")
    shell_output = service.render_env_shell(env_vars)
    print(shell_output)

    print(f"\n   Dotenv Format:")
    dotenv_output = service.render_env_dotenv(env_vars)
    print(dotenv_output)

    # Validate credential
    print(f"\n8. Credential Validation:")
    print(f"   ✓ Credential type: {type(credential).__name__}")
    print(f"   ✓ Has session_id: {credential.session_id is not None}")
    print(f"   ✓ Has key_alias: {credential.key_alias is not None}")
    print(f"   ✓ Has metadata: {len(credential.metadata_tags) > 0}")
    print(f"   ✓ Has secret: {credential.api_key is not None}")

    # Demonstrate revocation
    print(f"\n9. Credential Revocation:")
    revoked = await service.revoke_credential(credential)
    print(f"   ✓ Credential revoked")
    print(f"   ✓ Is Active: {revoked.is_active}")
    print(f"   ✓ Revoked At: {revoked.revoked_at}")
    print(f"   ✓ Secret cleared: {revoked.api_key.get_secret_value() == 'REDACTED'}")

    print(f"\n" + "=" * 70)
    print("Demo Complete: All credential operations successful")
    print("=" * 70)

    return credential


if __name__ == "__main__":
    credential = asyncio.run(demo_credential_issuance())

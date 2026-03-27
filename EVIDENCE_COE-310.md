# COE-310 Runtime Evidence

**Script**: `scripts/demo_credential_service.py`
**Generated**: 2026-03-27

This evidence demonstrates the end-to-end credential issuance flow with:
- Key aliasing convention: `session-{session_id[:8]}-{experiment_id[:8]}-{variant_id[:8]}`
- Metadata tags for LiteLLM correlation
- SecretStr handling for security
- Environment variable rendering (shell + dotenv)
- Credential revocation

---

## Demo Output

```
======================================================================
COE-310: Session-Scoped Proxy Credential Issuance Demo
======================================================================

1. Session Context:
   Session ID: f0b13e53-a4a2-46c8-8a56-4739f8a257b4
   Experiment: exp-claude-code-comparison
   Variant: var-claude-3-5-sonnet
   Harness Profile: claude-code

2. Issuing Proxy Credential...
   ✓ Credential issued
   ✓ Credential ID: 3236e346-efb5-40b6-b716-1dfb2b9de9a8
   ✓ Session ID: f0b13e53-a4a2-46c8-8a56-4739f8a257b4

3. Key Aliasing Convention:
   Key Alias: session-f0b13e53-exp-clau-var-clau
   Format: session-{session_id[:8]}-{experiment_id[:8]}-{variant_id[:8]}
   ✓ Alias contains session reference: f0b13e53

4. Metadata Tags (for LiteLLM correlation):
   benchmark_session_id: f0b13e53-a4a2-46c8-8a56-4739f8a257b4
   benchmark_experiment_id: exp-claude-code-comparison
   benchmark_variant_id: var-claude-3-5-sonnet
   benchmark_harness_profile: claude-code
   benchmark_source: opensymphony
   ✓ All metadata tags present for correlation

5. API Key (Secret Handling):
   Key Type: SecretStr
   Redacted Preview: sk-b...yCCA
   ✓ SecretStr prevents accidental plaintext exposure

6. Credential Expiration:
   Created: 2026-03-27 17:51:31.233300+00:00
   Expires: 2026-03-28 17:51:31.233244+00:00
   Is Active: True

7. Environment Variable Snippets:

   Shell Export Format:
export OPENAI_API_BASE='http://localhost:4000'
export OPENAI_API_KEY='sk-bm-session-f0b13e53-exp-clau-var-clau-1w25j-TlstZLGU9P9kqxU3HpGFcTr97G3nX4S23yCCA'
export OPENAI_MODEL='claude-3-5-sonnet-20241022'
export LITELLM_SESSION_ALIAS='session-f0b13e53-exp-clau-var-clau'

   Dotenv Format:
OPENAI_API_BASE=http://localhost:4000
OPENAI_API_KEY=sk-bm-session-f0b13e53-exp-clau-var-clau-1w25j-TlstZLGU9P9kqxU3HpGFcTr97G3nX4S23yCCA
OPENAI_MODEL=claude-3-5-sonnet-20241022
LITELLM_SESSION_ALIAS=session-f0b13e53-exp-clau-var-clau

8. Credential Validation:
   ✓ Credential type: ProxyCredential
   ✓ Has session_id: True
   ✓ Has key_alias: True
   ✓ Has metadata: True
   ✓ Has secret: True

9. Credential Revocation:
   ✓ Credential revoked
   ✓ Is Active: False
   ✓ Revoked At: 2026-03-27 17:51:31.233337+00:00
   ✓ Secret cleared: True

======================================================================
Demo Complete: All credential operations successful
======================================================================
```

## Summary

✅ **Credential Issuance**: Session-scoped credentials with unique key aliases  
✅ **Key Aliasing**: Format `session-{sid[:8]}-{exp[:8]}-{var[:8]}` for correlation  
✅ **Metadata Tags**: All dimensions tagged for LiteLLM request correlation  
✅ **Security**: SecretStr prevents plaintext exposure in logs/exports  
✅ **Environment Rendering**: Shell and dotenv formats for harness config  
✅ **Revocation**: Proper cleanup with secret clearing  

**Test Command**:
```bash
PYTHONPATH=src python scripts/demo_credential_service.py
```


============================================================
SESSION SERVICE DEMONSTRATION
Runtime Evidence for COE-305 Acceptance Criteria
============================================================

Started at: 2026-03-26T15:37:27.810772+00:00
============================================================
DEMO 1: Create and Finalize Sessions Safely
============================================================

1. Creating prerequisite entities...
   ✓ Created provider: openai (ID: f038354e-9196-4f2c-95ff-b785eab7cc34)
   ✓ Created harness profile: aider (ID: 4ff69177-3e87-409d-b6f4-b11d2789d96f)
   ✓ Created variant: gpt4-aider (ID: 99b533ab-791c-4f4a-ae9c-8fc5028a5ac4)
   ✓ Created task card: test-task (ID: c736d275-bf7e-4ada-94db-67b28693e260)
   ✓ Created experiment: session-demo (ID: 05c15765-9480-483b-adac-b66649481455)

2. Creating a new session...
   ✓ Created session: b767256d-e13b-4dac-b3e8-adf5122a94f8
   ✓ Status: active
   ✓ Started at: 2026-03-26 15:37:27.828077+00:00
   ✓ Operator label: demo-session-001

3. Retrieving session summary...
   ✓ Session summary retrieved:
     - ID: b767256d-e13b-4dac-b3e8-adf5122a94f8
     - Status: active
     - Experiment: 05c15765-9480-483b-adac-b66649481455
     - Variant: 99b533ab-791c-4f4a-ae9c-8fc5028a5ac4
     - Task Card: c736d275-bf7e-4ada-94db-67b28693e260
     - Git branch: main
     - Git commit: abc1234

4. Finalizing the session...
   ✓ Session finalized
   ✓ Status: completed
   ✓ Ended at: 2026-03-26 15:37:27.831325+00:00
   ✓ Duration: 0.00 seconds

✅ DEMO 1 PASSED: Sessions can be created and finalized safely

============================================================
DEMO 2: Referential Integrity Preservation
============================================================

1. Attempting to create session with non-existent experiment (5b22054c-bfa6-4ba3-b68a-06a6b096d5cb)...
   ✓ Correctly rejected: Invalid reference: Experiment '5b22054c-bfa6-4ba3-b68a-06a6b096d5cb' does not exist

2. Attempting to create session with non-existent variant (7db588e9-2389-4ca0-8668-8bbd10d02e87)...
   ✓ Correctly rejected: Invalid reference: Variant '7db588e9-2389-4ca0-8668-8bbd10d02e87' does not exist

3. Attempting to create session with non-existent task card (615d2a9e-d8a9-4f86-9f0e-76857325c2d6)...
   ✓ Correctly rejected: Invalid reference: TaskCard '615d2a9e-d8a9-4f86-9f0e-76857325c2d6' does not exist

✅ DEMO 2 PASSED: Referential integrity is preserved

============================================================
DEMO 3: Duplicate Session Identifier Rejection
============================================================

1. Creating first session with operator_label='unique-session-identifier-123'...
   ✓ First session created: bf12f465-41bc-44b6-a3a9-58a16fc603e3

2. Attempting to create second session with same operator_label='unique-session-identifier-123'...
   ✓ Correctly rejected duplicate: Duplicate session identifier: Session with identifier 'unique-session-identifier-123' already exists

3. Creating session with different operator_label...
   ✓ Different label accepted: 29f9f229-3082-4ea9-a636-46ebe9608287

✅ DEMO 3 PASSED: Duplicate session identifiers are rejected

============================================================
SUMMARY
============================================================
✅ ALL ACCEPTANCE CRITERIA VERIFIED

1. ✅ Services can create and finalize sessions safely
2. ✅ Repository methods preserve referential integrity
3. ✅ Duplicate session identifiers are rejected

Completed at: 2026-03-26T15:37:27.846248+00:00
Total duration: 0.04 seconds

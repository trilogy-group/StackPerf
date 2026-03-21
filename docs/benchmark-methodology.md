# Benchmark Methodology

## Purpose

This document defines how to run interactive benchmark sessions so comparisons across providers, models, harnesses, and harness configurations remain meaningful.

## Units of comparison

### Experiment

A named benchmark campaign that groups one or more variants around a question.

Example questions:

- which provider is fastest for repository understanding tasks?
- does a harness configuration change improve median TTFT?
- which harness produces the best session completion time for the same task card?

### Variant

A fixed benchmarkable combination of:

- provider route
- model
- harness profile
- harness configuration values
- benchmark tags

### Task card

A task card defines the work to be done in the repository.

It should include:

- title
- benchmark objective
- repository path or repository identifier
- starting instructions
- completion condition
- stop condition
- allowed operator interventions

### Session

A session is one interactive execution of one task card under one variant.

Sessions are the primary unit of historical comparison.

## Session modes

### Bounded benchmark session

Use this when the goal is comparability.

Requirements:

- fixed task card
- fixed repository snapshot or commit
- fixed operator instructions
- explicit stop condition
- fixed session duration cap or completion criterion

### Exploratory benchmark session

Use this when the goal is broader operational understanding.

Requirements:

- same session metadata capture rules
- clear notes on the purpose of the session
- explicit marking so exploratory work is not mixed with bounded comparisons in summary views

## Baseline controls

Keep these stable when comparing variants:

- same repository commit
- same task card
- same operator when possible
- same machine and network
- same LiteLLM version and config commit
- same benchmark application version
- same model alias mapping strategy
- same session start procedure

## Configuration axes

Track each axis explicitly in the variant definition rather than relying on operator memory.

Common axes:

- provider
- model
- harness profile
- harness config fingerprint
- routing headers
- session-affinity headers
- Claude Code header-stripping settings
- temperature and max-token settings when exposed by the harness

## Primary metrics

### Request metrics

- total request latency in milliseconds
- time to first token when available
- provider latency when exposed
- proxy overhead when exposed
- input tokens
- output tokens
- cached input tokens
- cache write tokens
- request status
- streamed output tokens per second when derivable

### Session metrics

- session duration
- request count
- successful request count
- failed request count
- median request latency
- p95 request latency
- median TTFT
- aggregate output throughput
- aggregate token counts
- cache hit behavior by request and by session

### Variant metrics

- median session duration
- median session request latency
- p95 session request latency
- median session TTFT
- session success rate
- variance across repeated sessions

## Handling interactive variability

Interactive work is noisy. Reduce noise with:

- repeated sessions per variant
- paired comparisons on the same task card
- written operator instructions
- consistent start and stop conditions
- exclusion rules for invalid sessions

A session should be excluded from direct comparison if:

- the repository state changed during the session without that being part of the task card
- the harness was pointed at the wrong base URL, credential, or model
- the session started before registration completed
- key telemetry is missing due to service failure

## Session start checklist

Before each bounded benchmark session:

1. confirm repository commit and dirty state
2. confirm selected variant
3. confirm selected task card
4. create session in the benchmark app
5. copy or source the rendered harness environment snippet
6. verify the harness points at the local LiteLLM proxy
7. start work only after session registration is complete

## Session end checklist

At the end of each session:

1. finalize the session in the benchmark app
2. record outcome status
3. record operator notes if needed
4. run collection and rollup commands if they are not automatic
5. verify that request counts and timings were ingested

## Recommended benchmark cadence

For bounded comparisons:

- at least 3 sessions per variant for quick signal
- 5 or more sessions per variant for stronger latency comparisons
- run alternating variants on the same day when provider load may fluctuate

## Reporting guidance

Every comparison report should show:

- experiment name
- task card name
- repository commit
- compared variants
- session count per variant
- latency summary statistics
- TTFT summary statistics
- error rate
- token counts
- cache metrics
- notes on any excluded sessions

## Interpretation cautions

Do not treat one slow session as proof of a provider problem. Separate these possibilities:

- provider capacity or queueing
- proxy misconfiguration
- harness retry behavior
- routing changes
- cache locality issues
- operator divergence from the task card

The stored metadata should make these explanations inspectable after the fact.

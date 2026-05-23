---
name: rag-llm-ai-expert
description: "Workspace skill: guided workflow for Retrieval-Augmented Generation (RAG), prompt engineering, LLM orchestration, and safe AI output verification. Use when you need a repeatable, auditable process for building LLM-powered features, running ad-hoc RAG tasks, or reviewing LLM outputs."
---

# RAG, LLM and AI Expert — SKILL

## Use when
- You need a reproducible RAG pipeline for answering questions from documents.
- You want a structured prompt-engineering step for consistent LLM outputs.
- You need guidance for verification, citation, or hallucination mitigation.
- You are designing or reviewing an LLM-driven feature or integration.

## Decision Flow (high level)
1. Define the intent and required output schema (structured/unstructured).
2. Select sources and retrieval strategy (vector DB, filters, recency).
3. Build context: chunking, scoring, and prompt window budgeting.
4. Compose prompts with explicit instructions, constraints, and verification steps.
5. Call LLM(s) with deterministic settings for generation or sampling for exploration.
6. Verify and post-process: citation extraction, factuality checks, and sanitization.
7. Persist telemetry / signals and iterate (prompt, retrieval, model settings).

## Step-by-step Workflow
1. Intent & Schema
   - Write a one-line intent and a short example of the desired output.
   - Decide if the output must include citations (source ids + offsets).

2. Retrieval Setup
   - Choose embedding model & vector DB collection.
   - Define retrieval filters (metadata, date range) and top-k.
   - If long documents present, apply chunking (200–1000 tokens) with overlap.

3. Context Assembly
   - Score candidates (similarity score + recency/metadata boost).
   - Trim context to fit model token limits (reserve tokens for prompt + answer).
   - Include only top-N passages that maximize coverage and relevance.

4. Prompt Composition
   - Use explicit instruction headings: Task, Context, Constraints, Output Format.
   - Add a short-example pair when possible (one-shot) for structured outputs.
   - Request citations inline and a final `sources` array containing ids.

5. Model Call
   - For deterministic results: set temperature=0, top_p=1.
   - For explorations: increase temperature (0.7) and run multiple samples.
   - If using a chain-of-thought, prefer `explain` mode for internal checks but redact from user-facing output.

6. Verification & Safety
   - Check that required fields are present and types match the schema.
   - Validate citations exist in returned context (no invented source ids).
   - Run lightweight factuality checks (keyword overlap, numeric verification against sources).
   - Sanitize outputs (remove PII, enforce content policy).

7. Post-processing
   - Format into the agreed schema (JSON, markdown, table).
   - Add provenance: model name, temperature, retrieval params, timestamps.
   - Persist logs/telemetry for feedback and A/B testing.

## Quality Criteria / Acceptance Checks
- Output matches schema and example shape.
- Citations refer to retrieved documents; no external hallucinated sources.
- Answer contains explicit confidence or caveats when unsure.
- Token budget respected (no truncated context).
- Safety checks pass (no PII leakage, policy violations).

## Prompts & Templates
- Minimal RAG prompt (structured):

  Task: Answer the question using ONLY the documents in Context.
  Context:
  {{#each context}}- [id={{this.id}}] {{this.text}}
  {{/each}}

  Question: {{question}}

  Constraints:
  - Use at most the provided context.
  - Provide inline citations like [id=123].
  - Output must be valid JSON matching the schema below.

  Output schema:
  {
    "answer": "string",
    "sources": [ {"id": "string", "score": number} ],
    "confidence": "low|medium|high"
  }

- Verification prompt (after generation):
  "Check whether each factual claim in `answer` is supported by at least one `sources` entry. Return a list of claims with `supported: true|false` and the matching source id(s)."

## Example Prompts (copy-paste)
- "Help me summarize the attached docs (IDs: 45, 67) into 3 short bullets with source ids and a confidence score. Use temperature=0."
- "Extract product specifications as JSON from the following passages. Include `sources` with offsets. Fail if specification cannot be determined from sources."

## Common Patterns & Tips
- Use `temperature=0` for deterministic, reproducible responses when correctness matters.
- Always reserve ~20% of token budget for the model's answer (context should fit remaining tokens).
- When chaining models (retrieval -> LLM -> verifier), persist intermediate outputs for debugging.
- For numeric or code outputs, add validation tests (e.g., regex, JSON schema, unit checks).

## Safety, Privacy & Telemetry
- Redact or filter PII before sending user content to external LLMs when possible.
- Log telemetry fields: `intent`, `model`, `temperature`, `top_k`, `retrieval_ids`, `success`.
- Ensure telemetry respects user privacy and repo policies — do not log raw sensitive texts unless approved.

## Troubleshooting
- If hallucinations occur: increase retrieval top-k, add more precise constraints, or use a verifier model.
- If outputs are truncated: reduce context or switch to a longer-context LLM.
- If citations are missing: force the model to return `sources` array and validate post-call.

## Example Prompts to Try (suggested)
- "RAG: Answer user question from repo docs. Intent: Troubleshoot install failure. Provide steps and cite files."
- "LLM: Convert the following technical paragraph into a 3-bullet changelog entry. Keep code samples intact."

## Files / Locations
- Suggested home: `.github/skills/rag-llm-ai-expert/SKILL.md`

## Maintenance notes
- Keep embedding & model defaults in a separate config file (e.g., `configs/ai_defaults.yaml`).
- Add concrete example pairs and common schemas as separate assets in this skill folder.

---
Generated on: 2026-03-20
tags: [RAG, LLM, AI, prompt-engineering, verification]

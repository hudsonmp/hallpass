# Prompting Playbook for Rapid Idea-to-Product Iteration

## Core Prompting Strategies

* **CCSI (Clarity · Context · Specificity · Intent)** – State exactly *what* you want, *why* you want it, the necessary background, the format, and any constraints to minimise hallucinations and rework.&#x20;
* **Task Decomposition (Divide & Conquer)** – Break the product vision into bite-sized prompts so the model can deliver focused, higher-quality artefacts (e.g., one endpoint, one screen, one test).&#x20;
* **Iterative Looping** – Treat the LLM as a teammate: inspect output, give targeted feedback, and rerun until the spec is met.&#x20;
* **Few-Shot / One-Shot Examples** – Provide 1-3 ideal input→output pairs to lock in style, schema, or coding conventions.&#x20;
* **Role-Playing / Persona** – Ask the model to *act as* “senior frontend engineer”, “API security auditor”, etc., to tap into domain-specific heuristics.&#x20;
* **ROPE (Requirement-Oriented Prompt Engineering)** – Write prompts like a mini-spec: pre-conditions, definition of done, constraints; better requirements → better code.&#x20;
* **Chain-of-Thought** – Request step-by-step reasoning before the final answer; surfaces logic and aids debugging.&#x20;
* **Multi-Turn Clarification** – Invite the LLM to ask questions when specs are vague, avoiding wasted cycles.&#x20;
* **Meta-Prompting Lite** – Let the model draft or refine its own prompts for unfamiliar tasks, accelerating exploration.&#x20;

## Fast-Read Formatting Tips

* Open with a **1-sentence goal**, then a concise **bullet-spec**.
* Use ` ` fences for code, data models, or payload examples.
* Label sections clearly: `### Context`, `### Constraints`, `### Output`.
* Keep lists ≤ 7 items; use **ALL\_CAPS placeholders** for variables.
* Finish with a control clause: *“Respond only with valid JSON.”*

## Chronological Prompting Pipeline

1. **Concept Snapshot** – Write a two-sentence elevator pitch.
2. **User-Story Split** – List core user stories; pick one thin slice.
3. **ROPE Requirements** – Detail inputs, outputs, constraints, acceptance tests.
4. **Initial Code Prompt** – Supply the spec + an example; request minimal viable code.
5. **Run & Review** – Execute; note errors, gaps, or style issues.
6. **Corrective Loop** – Feed logs/failing tests back; ask for fixes.
7. **Refactor + Docs** – Role-play as senior engineer to upgrade structure and comments.
8. **QA Sweep** – Persona “QA tester” generates edge-case tests and checklist.
9. **Deployment Snippet** – Ask for Dockerfile / CI config to ship.
10. **Prompt Archive** – Save the final prompt-answer pair to your internal library.

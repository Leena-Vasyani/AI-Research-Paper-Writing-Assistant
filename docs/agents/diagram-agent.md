# Diagram Agent

## Module

- backend/core_agents/diagram_agent.py

## What does it do?

Diagram Agent converts plain-language technical descriptions into valid Mermaid diagrams. It targets the research writing and documentation workflow where system diagrams, process flows, and conceptual models need to be produced quickly and consistently. The agent accepts a natural language description of a diagram (for example, a workflow or architecture summary) and returns Mermaid code that can be rendered directly in the UI without manual editing. The output is intentionally constrained to Mermaid syntax so it is immediately usable in a renderer and can be exported as part of a paper or report.

In the overall system, this agent removes the friction of diagram authoring by shifting the burden of syntax correctness and structure selection to the model. The user provides the intent, while the agent ensures that the returned artifact is a clean Mermaid diagram that can be previewed or refined downstream.

## How does it work?

The agent follows a deterministic pipeline that prioritizes structure and output safety over freeform text:

1. Prompt construction: it builds a strict prompt that explicitly instructs the model to output Mermaid code only and avoid extraneous explanations. The prompt includes the user-provided description and, when available, a diagram type hint to bias the structure.
2. Diagram type guidance: an optional `diagram_type` parameter is accepted to nudge the model toward the expected family (for example, flow or sequence style). The hint does not enforce a specific schema, but it reduces ambiguity in the generated layout.
3. Provider selection: a fallback chain is used to increase reliability. The order is Ollama (via the shared `llm_provider` utility), then Gemini, then Groq. If a provider fails or returns an unusable response, the next provider is invoked.
4. Output normalization: the response is cleaned so that only Mermaid content remains. Markdown fences are stripped, and the resulting Mermaid string is normalized to be safe for renderer consumption.

This pipeline balances flexibility and correctness. It allows the agent to use multiple LLM backends while preserving a uniform interface for downstream rendering.

## Technologies used

- google genai client
- groq client
- shared llm_provider utility

## Inputs and outputs

Input fields are minimal by design to keep the interface simple and portable:

- `description` (required): a natural language request describing the intended diagram, including nodes, relationships, and ordering if relevant.
- `diagram_type` (optional): a hint used to bias the model toward a specific Mermaid diagram family.

The output includes:

- `success` flag: indicates whether a valid Mermaid result was produced.
- `mermaid_code`: the normalized Mermaid string suitable for direct rendering.
- `provider` metadata: identifies the model backend that returned the final result, enabling traceability in logs or UI displays.

## API dependency

- Exposed through /api/diagram/generate

## Failure modes and guardrails

The primary failure mode is provider unavailability or malformed responses. The agent returns a structured error if all providers fail. It also handles fenced responses by stripping markdown backticks and normalizing the final Mermaid content, reducing the risk of invalid syntax being passed to the renderer. By constraining output to Mermaid only, it avoids mixing prose with code and keeps the UI pipeline predictable.

## Performance notes

Runtime is primarily bound by upstream provider latency and rate limits. The input size (length of the description) and provider selection strategy are the dominant factors in response time. Because it uses a fallback chain, the worst-case latency can include multiple provider attempts, but this also increases the probability of obtaining a usable diagram during transient failures.

## Extension ideas

- Add a Mermaid syntax lint pass before returning output.
- Add architecture-aware templates for cloud, microservices, and ML pipelines.

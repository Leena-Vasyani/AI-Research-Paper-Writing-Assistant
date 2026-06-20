# Code-to-Pseudocode Feature

## What does it do?

Code-to-Pseudocode transforms implementation code into publication-grade LaTeX pseudocode suitable for algorithm2e, a common format used in academic papers. The purpose is to bridge the gap between executable source code and the more abstract, stepwise representation expected in research writing. Rather than copying large code listings into a paper, the feature extracts the algorithmic core and presents it in a concise, formal style with explicit control flow, consistent notation, and minimal implementation noise. The output is designed to be inserted directly into LaTeX documents without manual cleanup, enabling faster preparation of methodology and algorithm sections.

This feature is especially useful in student projects and research manuscripts where clarity and reproducibility are critical. It helps authors explain the logic of their methods while preserving a neutral, academic tone and avoiding language-specific syntax that can distract from the algorithm itself.

## How does it work?

The pipeline emphasizes strict output constraints and semantic abstraction:

1. Input handling: the user provides a code snippet, optionally accompanied by an algorithm name. The system does not require full files; short functions or classes are sufficient.
2. Prompt construction: a strict instruction set is used to steer the model toward algorithmic abstraction rather than literal code translation. The prompt enforces algorithm2e conventions, including line numbering, assignment arrows, conditional blocks, and loop structures.
3. Semantic compression: the model identifies control flow, data structures, and logical steps, then collapses implementation-specific details (variable initialization boilerplate, logging, error handling) into higher-level actions.
4. Notation normalization: output is standardized to LaTeX math-friendly conventions, ensuring that operations such as assignment, comparisons, and set membership are rendered in a paper-friendly manner.
5. Output sanitization: any extraneous commentary or markdown fences are removed. The output is returned as a clean LaTeX body that can be dropped into a `algorithm2e` environment.

This approach ensures that the output is both readable and consistent with common academic formatting expectations, while remaining faithful to the underlying algorithmic logic.

## Technologies used

- Next.js page: web/src/app/code-to-pseudocode/page.tsx
- Backend converter: backend/core_agents/pseudocode_agent.py
- LLM provider fallback chain for robust generation

## Inputs and outputs

Inputs:

- Code snippet (required)
- Optional algorithm name (used as the pseudocode title)

Outputs:

- algorithm2e-compatible LaTeX pseudocode
- Provider metadata (useful for debugging or provenance)

The output intentionally omits explanatory prose or analysis to keep the artifact focused on algorithm presentation and to minimize post-processing.

## API dependencies

- /api/pseudocode/convert

## Failure modes and guardrails

Empty input is rejected early to avoid sending meaningless requests. If a provider returns fenced or multi-part responses, the system strips markdown to retain only the LaTeX body. When all providers fail, the API returns a structured error so the UI can surface a clear message instead of silently failing. These guardrails keep the feature predictable and reduce the chance of producing unusable pseudocode.

## Performance and scaling notes

Runtime scales with input length and logical complexity. Short, focused snippets typically yield the most accurate abstraction, while very long files may dilute the algorithm signal and reduce quality. Segmenting large files into key functions or modules improves results and helps the model isolate the algorithmic core.

## Extension ideas

- Add language-specific pre-parsing to improve extraction of loops, conditionals, and data structures.
- Add optional style modes (algorithmicx or plain-text pseudocode) for venues that do not use algorithm2e.

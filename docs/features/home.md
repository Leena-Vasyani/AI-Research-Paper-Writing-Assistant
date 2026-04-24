# Home Feature

## What does it do?

The Home feature is the landing experience for ResearchGen. It communicates platform value, introduces the research pipeline, and routes users into primary workspaces such as Workflow and How It Works.

## How does it work?

- Renders a cinematic hero with layered gradients and a Spline 3D scene.
- Presents narrative blocks describing the five-step research momentum model.
- Exposes high-priority call-to-action links:
  - Enter workflow
  - Explore methodology
- Displays feature highlights for drafting, formatting, diagrams, pseudocode, GitHub-to-IEEE, and DocChat.

## Technologies used

- Next.js App Router page: web/src/app/page.tsx
- React functional component pattern
- Tailwind utility classes for visual composition
- Custom components:
  - ProjectLogo
  - SplineScene

## Inputs and outputs

- Inputs: none from user forms.
- Outputs: navigation actions and feature orientation.

## API dependencies

None directly. This page is presentation-first and does not call backend APIs.

## Failure modes and guardrails

- If Spline assets fail to load, the rest of the page still renders and navigation remains usable.
- Home avoids hard dependency on backend health, so it is resilient during API downtime.

## Performance and scaling notes

- Heavy visual elements are isolated in hero section to preserve content readability.
- Page is mostly static UI, favorable for fast initial render.

## Extension ideas

- Add dynamic status widgets for backend health and model provider availability.
- Add personalized quick links based on recent feature usage.

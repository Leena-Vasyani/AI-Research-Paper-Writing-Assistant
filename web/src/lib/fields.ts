/**
 * Academic field taxonomy — the single source of truth for the UI.
 *
 * Two levels: a broad `Field` and its `subfields`. The selected `{ field,
 * subfield }` is sent to the backend inside the pipeline `constraints` (see
 * FieldSelector + the pipeline/workflow/agent-hub run forms), where
 * `backend/runtime/fields.py` maps the field id to retrieval source routing and
 * a prompt hint. This file only holds the *display* taxonomy plus per-field UI
 * defaults (placeholder example, venue/citation defaults, and which craft tools
 * are most relevant) — keep the field ids here in sync with the Python map.
 */

export type CitationStyle = "ieee" | "apa" | "mla";
export type Venue = "IEEE" | "ACM" | "Springer";

/** Tool route slugs used for "recommended for your field" hints. */
export type ToolSlug =
  | "smart-drafter"
  | "universal-research-formatter"
  | "diagram-generator"
  | "code-to-pseudocode"
  | "github-to-ieee"
  | "doc-chat";

export type Field = {
  id: string;
  label: string;
  subfields: string[];
  /** Example topic shown as the topic-input placeholder for this field. */
  placeholder: string;
  defaults: { venue: Venue; citationStyle: CitationStyle };
  /** Craft tools most relevant to this discipline (soft hint, never hides). */
  tools: ToolSlug[];
};

const WRITING_TOOLS: ToolSlug[] = [
  "smart-drafter",
  "universal-research-formatter",
  "diagram-generator",
  "doc-chat",
];
const STEM_TOOLS: ToolSlug[] = [...WRITING_TOOLS, "code-to-pseudocode", "github-to-ieee"];

export const FIELDS: Field[] = [
  {
    id: "general",
    label: "General / Interdisciplinary",
    subfields: ["Interdisciplinary", "Methodology", "Review / Meta-analysis", "Other"],
    placeholder: "e.g. the impact of remote work on team productivity",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "cs",
    label: "Computer Science & IT",
    subfields: [
      "Artificial Intelligence / ML",
      "Computer Vision",
      "Natural Language Processing",
      "Systems & Networking",
      "Databases & Data Mining",
      "Security & Cryptography",
      "Human-Computer Interaction",
      "Software Engineering",
      "Theory & Algorithms",
    ],
    placeholder: "e.g. graph neural networks for smart grid load forecasting",
    defaults: { venue: "IEEE", citationStyle: "ieee" },
    tools: STEM_TOOLS,
  },
  {
    id: "engineering",
    label: "Engineering & Technology",
    subfields: [
      "Electrical & Electronics",
      "Mechanical",
      "Civil & Structural",
      "Chemical",
      "Robotics & Control",
      "Energy & Power Systems",
      "Materials & Manufacturing",
    ],
    placeholder: "e.g. fatigue analysis of additively manufactured titanium components",
    defaults: { venue: "IEEE", citationStyle: "ieee" },
    tools: STEM_TOOLS,
  },
  {
    id: "physical_sciences",
    label: "Physical Sciences",
    subfields: [
      "Physics",
      "Chemistry",
      "Astronomy & Astrophysics",
      "Materials Science",
      "Mathematics & Statistics",
      "Earth & Planetary Science",
    ],
    placeholder: "e.g. spectroscopic analysis of exoplanet atmospheres",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: [...WRITING_TOOLS, "code-to-pseudocode"],
  },
  {
    id: "health",
    label: "Health & Medicine",
    subfields: [
      "Clinical Medicine",
      "Public Health & Epidemiology",
      "Neuroscience",
      "Pharmacology",
      "Nutrition & Dietetics",
      "Nursing & Allied Health",
      "Mental Health",
    ],
    placeholder: "e.g. effect of intermittent fasting on type 2 diabetes markers",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "life_sciences",
    label: "Life Sciences & Biology",
    subfields: [
      "Molecular & Cell Biology",
      "Genetics & Genomics",
      "Ecology & Evolution",
      "Microbiology",
      "Biochemistry",
      "Biotechnology",
    ],
    placeholder: "e.g. CRISPR-based gene drives for pest population control",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "agriculture",
    label: "Agriculture & Food Science",
    subfields: [
      "Agronomy & Crop Science",
      "Soil Science",
      "Horticulture",
      "Animal Science",
      "Food Science & Technology",
      "Agricultural Economics",
      "Sustainable Agriculture",
    ],
    placeholder: "e.g. drought-tolerant rice cultivars for smallholder farms",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "environment",
    label: "Environment & Earth Science",
    subfields: [
      "Climate Science",
      "Ecology & Conservation",
      "Environmental Policy",
      "Renewable Energy",
      "Water Resources",
      "Geoscience",
      "Sustainability",
    ],
    placeholder: "e.g. carbon sequestration potential of urban green spaces",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "social_sciences",
    label: "Social Sciences",
    subfields: [
      "Psychology",
      "Sociology",
      "Political Science",
      "Anthropology",
      "Education",
      "Communication & Media",
      "Geography (Human)",
    ],
    placeholder: "e.g. social media use and adolescent civic engagement",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "finance",
    label: "Finance & Economics",
    subfields: [
      "Corporate Finance",
      "Financial Markets",
      "Macroeconomics",
      "Microeconomics",
      "Behavioral Finance",
      "Econometrics",
      "Fintech",
    ],
    placeholder: "e.g. impact of central bank digital currencies on retail banking",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: [...WRITING_TOOLS],
  },
  {
    id: "business",
    label: "Business & Management",
    subfields: [
      "Strategy & Management",
      "Marketing",
      "Operations & Supply Chain",
      "Organizational Behavior",
      "Entrepreneurship",
      "Accounting",
      "Human Resources",
    ],
    placeholder: "e.g. AI adoption and dynamic capabilities in SMEs",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: WRITING_TOOLS,
  },
  {
    id: "arts",
    label: "Arts & Humanities",
    subfields: [
      "Literature",
      "History",
      "Philosophy",
      "Linguistics",
      "Cultural Studies",
      "Visual & Performing Arts",
      "Religious Studies",
    ],
    placeholder: "e.g. postcolonial identity in contemporary diaspora fiction",
    defaults: { venue: "Springer", citationStyle: "mla" },
    tools: ["smart-drafter", "universal-research-formatter", "doc-chat"],
  },
  {
    id: "law",
    label: "Law & Policy",
    subfields: [
      "Constitutional Law",
      "International Law",
      "Intellectual Property",
      "Criminal Justice",
      "Public Policy",
      "Technology & Data Law",
    ],
    placeholder: "e.g. regulatory frameworks for generative AI accountability",
    defaults: { venue: "Springer", citationStyle: "apa" },
    tools: ["smart-drafter", "universal-research-formatter", "doc-chat"],
  },
];

export const DEFAULT_FIELD_ID = "general";

export function getField(id: string | undefined | null): Field {
  return FIELDS.find((f) => f.id === id) ?? FIELDS[0];
}

export function subfieldsFor(id: string | undefined | null): string[] {
  return getField(id).subfields;
}

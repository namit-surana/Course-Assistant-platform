type RubricLabel = {
  label: string;
  description?: string;
};

// Matches the built-in PPT rubric used by the backend (A1–F2).
const PPT_LABELS: Record<string, RubricLabel> = {
  A1: { label: "Readable content", description: "Slides/pages contain substantive text (not blank/placeholder-only)." },
  A2: { label: "Team/project identifiable", description: "Project/team identifiable early (title/headers/first slides)." },
  A3: { label: "Appropriate file/format", description: "Deck/PDF structure maps consistently to slides/pages." },
  B1: { label: "Logical flow", description: "Problem → approach → results/demo → conclusion/next steps." },
  B2: { label: "Clear sections/titles", description: "Slide titles/sections support the story and ordering." },
  B3: { label: "Appropriate depth", description: "More than buzzwords; enough detail to follow." },
  C1: { label: "Concrete technical/product content", description: "Features/architecture/methodology described concretely." },
  C2: { label: "Integration/external systems scoped", description: "Integrations explained or gaps acknowledged." },
  C3: { label: "Limitations disclosed", description: "Limitations/mocks/unfinished areas noted when relevant." },
  D1: { label: "Terminology consistent", description: "Acronyms defined; terms used consistently." },
  D2: { label: "Diagrams referenced in text", description: "Enough text to understand intent even without visuals." },
  D3: { label: "Takeaways/conclusions explicit", description: "Clear conclusions where expected." },
  E1: { label: "Claims match evidence", description: "No overstated “done” without support in text." },
  E2: { label: "Links only if present", description: "Repo/demo/video links only if mentioned in the deck extract." },
  F1: { label: "Reproducibility/setup notes (optional)" },
  F2: { label: "Timeline/risks/teamwork (optional)" },
};

// Demo video rows sometimes come back as wizard ids; support those too.
const DEMO_LABELS: Record<string, RubricLabel> = {
  demo_clarity: { label: "Clarity of demonstration" },
  demo_coverage: { label: "Feature coverage" },
  demo_functionality: { label: "Working proof / functionality" },
  demo_narration: { label: "Explanation & narration" },
  demo_quality: { label: "Presentation quality" },
  ...PPT_LABELS,
};

export function labelForPptCriterion(id: string | null | undefined): RubricLabel | null {
  if (!id) return null;
  return PPT_LABELS[id] ?? null;
}

export function labelForDemoCriterion(id: string | null | undefined): RubricLabel | null {
  if (!id) return null;
  return DEMO_LABELS[id] ?? null;
}


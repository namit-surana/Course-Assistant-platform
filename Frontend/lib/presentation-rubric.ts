import type { RubricCriterionInput } from "./types";

/** Criterion ids for the "presentation" artifact (see create-event wizard). */
const PRESENTATION_CRITERION_IDS = new Set<string>([
  "pres_clarity",
  "pres_structure",
  "pres_solution",
  "pres_design",
  "pres_impact",
]);

/**
 * Build rubric rows for PPT analysis from event criteria_config.
 * Supports both wizard-shaped criteria (artifactId === "presentation") and
 * legacy/plain maps keyed by pres_* ids without artifactId.
 */
export function presentationRubricFromCriteriaConfig(
  criteriaConfig: Record<string, unknown> | undefined
): RubricCriterionInput[] {
  const criteriaRaw = criteriaConfig?.criteria;
  if (!criteriaRaw || typeof criteriaRaw !== "object" || Array.isArray(criteriaRaw)) {
    return [];
  }
  const criteria = criteriaRaw as Record<string, Record<string, unknown>>;

  const out: RubricCriterionInput[] = [];
  for (const [id, c] of Object.entries(criteria)) {
    if (!c || typeof c !== "object") continue;
    if (!c.selected) continue;
    const weight = Number(c.weight);
    if (!(weight > 0)) continue;

    const artifactId = c.artifactId;
    const isPresentation =
      artifactId === "presentation" || PRESENTATION_CRITERION_IDS.has(id);
    if (!isPresentation) continue;

    const label = typeof c.label === "string" ? c.label.trim() : "";
    const category =
      label ||
      id
        .replace(/_/g, " ")
        .replace(/\b\w/g, (ch) => ch.toUpperCase());

    const desc = typeof c.description === "string" ? c.description.trim() : "";
    const description =
      desc || `Evaluate ${category.toLowerCase()} for this presentation.`;

    out.push({ category, description, max_score: weight });
  }
  return out;
}

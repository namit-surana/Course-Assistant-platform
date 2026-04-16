"use client";

import { useState } from "react";
import { History } from "lucide-react";

import AgentPlan from "@/components/ui/agent-plan";
import { Button } from "@/components/ui/button";
import type { AnalyzeResponse, PlanTask } from "@/lib/types";

export function ResultsPanel({
  analysis,
  planTasks = [],
  hideHeader = false,
}: {
  analysis: AnalyzeResponse["repository_analysis"];
  planTasks?: PlanTask[];
  hideHeader?: boolean;
}) {
  if (!analysis) {
    return (
      <section className="rounded-[1.75rem] border border-border/70 bg-card/70 p-6">
        <p className="text-sm text-muted-foreground">No completed findings yet.</p>
      </section>
    );
  }

  return (
    <ResultsContent
      analysis={analysis}
      planTasks={planTasks}
      hideHeader={hideHeader}
    />
  );
}

function ResultsContent({
  analysis,
  planTasks,
  hideHeader = false,
}: {
  analysis: NonNullable<AnalyzeResponse["repository_analysis"]>;
  planTasks: PlanTask[];
  hideHeader?: boolean;
}) {
  const overviewSummary = [analysis.executive_summary, analysis.repository_overview]
    .filter((value): value is string => Boolean(value?.trim()))
    .filter((value, index, values) => values.findIndex((entry) => entry.trim() === value.trim()) === index);

  const tabs = [
    {
      id: "overview",
      title: "Overview",
      body: undefined,
      items: overviewSummary,
    },
    {
      id: "strengths",
      title: "Strengths",
      body: undefined,
      items: analysis.strengths || [],
    },
    {
      id: "risks",
      title: "Risks",
      body: undefined,
      items: analysis.risks_and_weaknesses || [],
    },
    {
      id: "runtime",
      title: "Runtime",
      body: undefined,
      items: analysis.runtime_behavior || [],
    },
    {
      id: "architecture",
      title: "Architecture",
      body: undefined,
      items: analysis.architecture_patterns || [],
    },
    {
      id: "quality",
      title: "Quality",
      body: analysis.quality_assessment,
      items: [],
    },
    {
      id: "questions",
      title: "Questions",
      body: undefined,
      items: analysis.intelligent_questions || [],
    },
    {
      id: "next-steps",
      title: "Next Steps",
      body: undefined,
      items: analysis.recommended_next_steps || [],
    },
    {
      id: "evidence",
      title: "Evidence Paths",
      body: undefined,
      items: analysis.evidence_paths || [],
    },
  ];
  const availableTabs = tabs.filter(
    (tab) => tab.body || tab.items.length > 0,
  );
  const [activeTabId, setActiveTabId] = useState(availableTabs[0]?.id ?? "overview");
  const activeTab = availableTabs.find((tab) => tab.id === activeTabId) ?? availableTabs[0];
  const showTimeline = activeTabId === "timeline";

  return (
    <section className="rounded-[1.75rem] border border-border/70 bg-card/70 p-6 md:p-7">
      <div className="space-y-4">
        {!hideHeader && (
          <div className="space-y-2">
            <p className="text-xs font-semibold uppercase tracking-[0.22em] text-blue-400">
              Findings
            </p>
            <h2 className="text-2xl font-semibold tracking-[-0.04em]">Review outcome</h2>
            <p className="max-w-3xl text-sm leading-7 text-muted-foreground">
              Start with Overview, then step through the sections only when you need more detail.
            </p>
          </div>
        )}

        <div className="flex flex-wrap gap-2">
          {availableTabs.map((tab) => (
            <Button
              key={tab.id}
              type="button"
              variant={tab.id === activeTab?.id ? "secondary" : "outline"}
              className="rounded-full px-4"
              onClick={() => setActiveTabId(tab.id)}
            >
              {tab.title}
            </Button>
          ))}
          <Button
            type="button"
            variant="secondary"
            className={`rounded-full border px-4 shadow-[0_0_0_1px_rgba(59,130,246,0.08)_inset] transition-all ${
              showTimeline
                ? "border-cyan-400/40 bg-gradient-to-r from-cyan-500/30 via-blue-500/25 to-sky-500/30 text-cyan-50"
                : "border-cyan-500/30 bg-gradient-to-r from-cyan-500/12 via-blue-500/10 to-sky-500/12 text-cyan-200 hover:border-cyan-400/45 hover:text-cyan-100"
            }`}
            onClick={() => setActiveTabId(showTimeline ? availableTabs[0]?.id ?? "overview" : "timeline")}
          >
            <History className="size-4" />
            Execution Timeline
          </Button>
        </div>
      </div>

      {showTimeline ? (
        <article className="mt-5 rounded-[1.5rem] border border-border/70 bg-background/30 p-5 md:p-6">
          <div className="space-y-2">
            <h3 className="text-xl font-semibold tracking-[-0.03em]">Execution timeline</h3>
            <p className="text-sm leading-7 text-muted-foreground">
              Review past activity and phase-by-phase execution without leaving the findings workspace.
            </p>
          </div>
          <div className="mt-5">
            <AgentPlan tasks={planTasks} />
          </div>
        </article>
      ) : activeTab ? (
        <article className="mt-5 rounded-[1.5rem] border border-border/70 bg-background/30 p-5 md:p-6">
          <div className="space-y-2">
            <h3 className="text-xl font-semibold tracking-[-0.03em]">{activeTab.title}</h3>
            {activeTab.body ? (
              <p className="max-w-3xl text-sm leading-7 text-muted-foreground">{activeTab.body}</p>
            ) : null}
          </div>

          {activeTab.items.length > 0 ? (
            <ul className="mt-5 space-y-3">
              {activeTab.items.map((item, index) => (
                <li
                  key={`${activeTab.id}-${index}`}
                  className={`rounded-[1.15rem] border border-border/70 bg-card/70 px-4 py-4 text-sm leading-7 text-foreground/90 ${
                    activeTab.id === "evidence" ? "font-mono text-xs text-muted-foreground" : ""
                  }`}
                >
                  {item}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm text-muted-foreground">No additional details in this section.</p>
          )}
        </article>
      ) : null}

    </section>
  );
}

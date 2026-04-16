import { Shell } from "@/components/layout/shell";
import { Topbar } from "@/components/layout/topbar";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function EvaluationsPage() {
  return (
    <Shell>
      <Topbar title="Evaluations" subtitle="All team evaluations across events" />
      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <ComingSoon title="Evaluations" />
      </div>
    </Shell>
  );
}

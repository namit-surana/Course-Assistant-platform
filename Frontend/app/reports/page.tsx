import { Shell } from "@/components/layout/shell";
import { Topbar } from "@/components/layout/topbar";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function ReportsPage() {
  return (
    <Shell>
      <Topbar title="Reports" subtitle="Feedback reports for teams" />
      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <ComingSoon title="Reports" />
      </div>
    </Shell>
  );
}

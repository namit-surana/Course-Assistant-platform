import { Shell } from "@/components/layout/shell";
import { Topbar } from "@/components/layout/topbar";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function EventsPage() {
  return (
    <Shell>
      <Topbar title="Events" subtitle="Manage all your evaluation events" />
      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <ComingSoon title="Events" />
      </div>
    </Shell>
  );
}

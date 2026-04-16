import { Shell } from "@/components/layout/shell";
import { Topbar } from "@/components/layout/topbar";
import { ComingSoon } from "@/components/layout/coming-soon";

export default function SettingsPage() {
  return (
    <Shell>
      <Topbar title="Settings" subtitle="Org settings and configurations" />
      <div className="flex flex-1 flex-col overflow-hidden p-6">
        <ComingSoon title="Settings" />
      </div>
    </Shell>
  );
}

import { use } from "react";
import { TeamSubmitPage } from "@/components/events/team-submit-page";

export default function TeamSubmitRoute({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <TeamSubmitPage eventId={id} />;
}

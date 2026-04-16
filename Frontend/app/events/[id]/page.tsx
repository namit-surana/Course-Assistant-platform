import { use } from "react";
import { EventDetailPage } from "@/components/events/event-detail-page";

export default function EventPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  return <EventDetailPage eventId={id} />;
}

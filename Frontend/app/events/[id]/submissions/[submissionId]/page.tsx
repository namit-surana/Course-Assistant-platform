import { use } from "react";
import { SubmissionDetailsPage } from "@/components/events/submission-details-page";

export default function SubmissionPage({
  params,
}: {
  params: Promise<{ id: string; submissionId: string }>;
}) {
  const { id, submissionId } = use(params);
  return <SubmissionDetailsPage eventId={id} submissionId={submissionId} />;
}


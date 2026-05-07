"use client";

import { useRouter } from "next/navigation";
import { RotatingTitle } from "@/components/ui/rotating-title";
import { StarButton } from "@/components/ui/star-button";
import { SubmissionStatusCard } from "@/components/ui/submission-status-card";

const LANDING_WORDS = [
  "hackathons",
  "capstones",
  "demo days",
  "project courses",
  "live builds",
];

export function LandingPage() {
  const router = useRouter();

  const submissions = [
    {
      title: "Nexus Beta submission",
      team: "Nexus Beta",
      status: "submitted" as const,
      progress: 12,
      timeLabel: "Just now",
      submissionId: "45G2P",
      eventId: "demo-event",
      summary:
        "Your files have been uploaded. Processing will begin shortly and the analysis queue will update automatically.",
      details: [
        { label: "Review ETA", value: "12 min" },
        { label: "Artifact type", value: "PPT + Demo Video" },
        { label: "Next step", value: "Await processing" },
        { label: "Submission ID", value: "#45G2P" },
      ],
    },
    {
      title: "Apollo demo review",
      team: "Apollo",
      status: "processing" as const,
      progress: 48,
      timeLabel: "2 min ago",
      submissionId: "79L2K",
      eventId: "demo-event",
      summary:
        "Your submission is in the active review queue. Analysis will complete shortly and the report will be available automatically.",
      details: [
        { label: "Review ETA", value: "4 min" },
        { label: "Artifact type", value: "GitHub Repo + Video" },
        { label: "Next step", value: "AI scoring" },
        { label: "Submission ID", value: "#79L2K" },
      ],
    },
    {
      title: "Sierra capstone",
      team: "Sierra",
      status: "completed" as const,
      progress: 100,
      timeLabel: "Done",
      submissionId: "99F4M",
      eventId: "demo-event",
      summary:
        "Analysis is complete and the final report is ready for review. Share insights with your team or publish the results.",
      details: [
        { label: "Review ETA", value: "Ready" },
        { label: "Artifact type", value: "Presentation Slides" },
        { label: "Next step", value: "Publish report" },
        { label: "Submission ID", value: "#99F4M" },
      ],
    },
    {
      title: "Orion project",
      team: "Orion",
      status: "failed" as const,
      progress: 28,
      timeLabel: "1 min ago",
      submissionId: "58R8Q",
      eventId: "demo-event",
      summary:
        "An issue occurred while processing this submission. Review the error and resubmit once the artifacts are corrected.",
      details: [
        { label: "Review ETA", value: "Retry now" },
        { label: "Artifact type", value: "GitHub Repo + PPT + Video" },
        { label: "Next step", value: "Fix error" },
        { label: "Submission ID", value: "#58R8Q" },
      ],
    },
  ];

  const stats = {
    total: submissions.length,
    submitted: submissions.filter((item) => item.status === "submitted").length,
    processing: submissions.filter((item) => item.status === "processing").length,
    completed: submissions.filter((item) => item.status === "completed").length,
    failed: submissions.filter((item) => item.status === "failed").length,
  };

  return (
    <main className="min-h-screen bg-slate-950 text-slate-100">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center px-4 py-10">
        <section className="relative flex min-h-[50vh] flex-col items-center justify-center overflow-hidden text-center">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(139,92,246,0.05),transparent_40%)]" />
          <div className="relative mx-auto flex max-w-5xl flex-col items-center gap-6">
            <div className="space-y-4">
              <h1 className="text-4xl font-normal tracking-[-0.06em] text-white md:text-5xl">
                <span className="block">AI judges for</span>
                <RotatingTitle
                  words={LANDING_WORDS}
                  className="min-h-[1.3em] justify-center pt-3 text-slate-300"
                />
              </h1>

              <p className="mx-auto max-w-3xl text-base leading-7 text-slate-300 md:text-lg">
                See who performed best, why, and where every team can improve.
              </p>
            </div>

            <div className="pt-2">
              <StarButton
                onClick={() => router.push("/home")}
                lightColor="#a78bfa"
                backgroundColor="rgba(139,92,246,0.1)"
                duration={2.5}
                className="h-12 px-8 text-sm rounded-2xl border border-slate-700/50"
              >
                Start
              </StarButton>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl -mt-16 relative z-10">
          <div className="rounded-[2rem] bg-slate-900/60 p-6 ring-1 ring-slate-700/40 backdrop-blur-sm shadow-2xl">
            <div className="rounded-[1.75rem] bg-slate-800/50 p-5 ring-1 ring-slate-600/30 backdrop-blur-sm shadow-lg">
              <div className="mb-6 space-y-2">
                <p className="text-[11px] uppercase tracking-[0.35em] text-slate-400 font-semibold">Submission dashboard</p>
                <h2 className="text-2xl font-semibold tracking-[-0.02em] text-slate-100 sm:text-3xl">
                  Live submission states
                </h2>
                <p className="max-w-2xl text-sm leading-6 text-slate-300">
                  A compact dashboard for tracked submissions, progress, and actionable next steps.
                </p>
              </div>

              <div className="grid gap-3 sm:grid-cols-5 mb-6">
                <div className="rounded-3xl border border-slate-600/40 bg-slate-700/60 px-3 py-3 text-center shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.35em] text-slate-400 font-semibold">Total</p>
                  <p className="mt-2 text-xl font-semibold text-slate-100">{stats.total}</p>
                </div>
                <div className="rounded-3xl border border-slate-600/40 bg-slate-700/60 px-3 py-3 text-center shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.35em] text-slate-400 font-semibold">Submitted</p>
                  <p className="mt-2 text-xl font-semibold text-slate-100">{stats.submitted}</p>
                </div>
                <div className="rounded-3xl border border-slate-600/40 bg-slate-700/60 px-3 py-3 text-center shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.35em] text-slate-400 font-semibold">Processing</p>
                  <p className="mt-2 text-xl font-semibold text-slate-100">{stats.processing}</p>
                </div>
                <div className="rounded-3xl border border-slate-600/40 bg-slate-700/60 px-3 py-3 text-center shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.35em] text-slate-400 font-semibold">Completed</p>
                  <p className="mt-2 text-xl font-semibold text-slate-100">{stats.completed}</p>
                </div>
                <div className="rounded-3xl border border-slate-600/40 bg-slate-700/60 px-3 py-3 text-center shadow-sm backdrop-blur-sm">
                  <p className="text-[10px] uppercase tracking-[0.35em] text-slate-400 font-semibold">Failed</p>
                  <p className="mt-2 text-xl font-semibold text-slate-100">{stats.failed}</p>
                </div>
              </div>

              <div className="rounded-3xl border border-slate-600/40 bg-slate-800/60 shadow-sm overflow-hidden backdrop-blur-sm">
                <table className="w-full table-fixed border-separate border-spacing-0 text-left text-sm">
                  <colgroup>
                    <col className="w-[22%]" />
                    <col className="w-[12%]" />
                    <col className="w-[12%]" />
                    <col className="w-[10%]" />
                    <col className="w-[14%]" />
                    <col className="w-[11%]" />
                    <col className="w-[11%]" />
                    <col className="w-[18%]" />
                  </colgroup>
                  <thead className="border-b border-slate-600/40 bg-slate-700/60">
                    <tr>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Submission</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Team</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Status</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Progress</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Artifact</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">ETA</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Next</th>
                      <th className="px-3 py-3 text-[10px] uppercase tracking-[0.28em] text-slate-400">Action</th>
                    </tr>
                  </thead>
                  <tbody className="bg-slate-800/60">
                    {submissions.map((submission) => (
                      <SubmissionStatusCard
                        key={submission.submissionId ?? submission.title}
                        {...submission}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>
  );
}

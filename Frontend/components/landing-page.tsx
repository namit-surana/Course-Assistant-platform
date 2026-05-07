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

  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center px-6 py-10">
        <section className="relative flex min-h-[68vh] flex-col items-center justify-center overflow-hidden text-center">
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_top,rgba(255,255,255,0.03),transparent_30%)]" />

          <div className="relative mx-auto flex max-w-5xl flex-col items-center gap-8">
            <div className="space-y-6">
              <h1 className="text-4xl font-normal tracking-[-0.07em] text-balance md:text-6xl xl:text-[5.4rem]">
                <span className="block text-white">AI judges for</span>
                <RotatingTitle
                  words={LANDING_WORDS}
                  className="min-h-[1.3em] justify-center pt-3 text-white/45"
                />
              </h1>

              <p className="mx-auto max-w-3xl text-base leading-8 text-muted-foreground md:text-xl md:leading-10">
                See who performed best, why, and where every team can improve.
              </p>
            </div>

            <div className="pt-4">
              <StarButton
                onClick={() => router.push("/home")}
                lightColor="#a78bfa"
                backgroundColor="transparent"
                duration={2.5}
                className="h-14 px-10 text-base rounded-2xl"
              >
                Start
              </StarButton>
            </div>
          </div>
        </section>

        <section className="mx-auto w-full max-w-7xl py-16">
          <div className="rounded-[2.5rem] bg-gradient-to-br from-slate-900/40 to-slate-800/20 p-8 ring-1 ring-slate-700/50 backdrop-blur-xl shadow-2xl">
            <div className="mb-10 space-y-4">
              <p className="text-sm uppercase tracking-[0.3em] text-slate-300 font-medium">Submission dashboard</p>
              <h2 className="text-3xl font-semibold tracking-[-0.02em] text-white sm:text-4xl">
                Live submission states
              </h2>
              <p className="max-w-2xl text-base leading-7 text-slate-300">
                Monitor the latest workspace submissions with status badges, progress reports, and next-step guidance.
              </p>
            </div>
            <div className="grid gap-8 auto-rows-fr md:grid-cols-2 xl:grid-cols-4">
            <SubmissionStatusCard
              title="Nexus Beta submission"
              team="Nexus Beta"
              status="submitted"
              progress={12}
              timeLabel="Just now"
              summary="Your files have been uploaded. Processing will begin shortly and the analysis queue will update automatically."
              details={[
                { label: "Review ETA", value: "12 min" },
                { label: "Artifact type", value: "PPT + Demo Video" },
                { label: "Next step", value: "Await processing" },
                { label: "Submission ID", value: "#45G2P" },
              ]}
            />
            <SubmissionStatusCard
              title="Apollo demo review"
              team="Apollo"
              status="processing"
              progress={48}
              timeLabel="2 min ago"
              summary="Your submission is in the active review queue. Analysis will complete shortly and the report will be available automatically."
              details={[
                { label: "Review ETA", value: "4 min" },
                { label: "Artifact type", value: "GitHub Repo + Video" },
                { label: "Next step", value: "AI scoring" },
                { label: "Submission ID", value: "#79L2K" },
              ]}
            />
            <SubmissionStatusCard
              title="Sierra capstone"
              team="Sierra"
              status="completed"
              progress={100}
              timeLabel="Done"
              summary="Analysis is complete and the final report is ready for review. Share insights with your team or publish the results."
              details={[
                { label: "Review ETA", value: "Ready" },
                { label: "Artifact type", value: "Presentation Slides" },
                { label: "Next step", value: "Publish report" },
                { label: "Submission ID", value: "#99F4M" },
              ]}
            />
            <SubmissionStatusCard
              title="Orion project"
              team="Orion"
              status="failed"
              progress={28}
              timeLabel="1 min ago"
              summary="An issue occurred while processing this submission. Review the error and resubmit once the artifacts are corrected."
              details={[
                { label: "Review ETA", value: "Retry now" },
                { label: "Artifact type", value: "GitHub Repo + PPT + Video" },
                { label: "Next step", value: "Fix error" },
                { label: "Submission ID", value: "#58R8Q" },
              ]}
            />
          </div>
        </div>
        </section>
      </div>
    </main>
  );
}

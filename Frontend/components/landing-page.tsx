"use client";

import { useRouter } from "next/navigation";
import { RotatingTitle } from "@/components/ui/rotating-title";
import { StarButton } from "@/components/ui/star-button";

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
      </div>
    </main>
  );
}

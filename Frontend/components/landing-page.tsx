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
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-7xl flex-col justify-center px-6 py-10">
        <section className="relative flex min-h-[82vh] flex-col items-center justify-center overflow-hidden text-center">
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
      </div>
    </main>
  );
}

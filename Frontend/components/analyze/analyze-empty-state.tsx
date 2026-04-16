"use client";

import Link from "next/link";
import { ArrowLeft, MoveRight } from "lucide-react";

import { Button, buttonVariants } from "@/components/ui/button";
import { RecentRunsPanel } from "@/components/analyze/recent-runs-panel";
import { cn } from "@/lib/utils";
import type { AnalysisRunState } from "@/lib/types";

interface AnalyzeEmptyStateProps {
  repoUrl: string;
  branch: string;
  error: string | null;
  isSubmitting: boolean;
  recentRuns: AnalysisRunState[];
  onRepoUrlChange: (value: string) => void;
  onBranchChange: (value: string) => void;
  onSubmit: (event: React.FormEvent<HTMLFormElement>) => void;
  onOpenRun: (runId: string) => void;
}

export function AnalyzeEmptyState({
  repoUrl,
  branch,
  error,
  isSubmitting,
  recentRuns,
  onRepoUrlChange,
  onBranchChange,
  onSubmit,
  onOpenRun,
}: AnalyzeEmptyStateProps) {
  return (
    <main className="min-h-screen bg-background text-foreground">
      <div className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-8 xl:max-w-6xl 2xl:max-w-7xl">
        <div className="mb-8">
          <Link
            href="/"
            className={cn(
              buttonVariants({ variant: "ghost", size: "sm" }),
              "inline-flex rounded-full px-3 text-muted-foreground",
            )}
          >
            <ArrowLeft className="size-4" />
            Back
          </Link>
        </div>

        <div className="flex flex-1 items-center justify-center">
          <div className="grid w-full max-w-5xl gap-6 lg:grid-cols-[1.1fr_0.9fr]">
            <section className="w-full rounded-[2rem] border border-border/70 bg-card/80 p-8 shadow-[0_1px_0_rgba(255,255,255,0.04)_inset] backdrop-blur md:p-10">
              <div className="space-y-8">
                <div className="space-y-3 text-center">
                  <p className="text-xs font-semibold uppercase tracking-[0.24em] text-blue-400">
                    Evaluation Workspace
                  </p>
                  <h1 className="text-3xl font-semibold tracking-[-0.05em] text-balance md:text-5xl">
                    Start a new submission review
                  </h1>
                  <p className="text-sm leading-7 text-muted-foreground md:text-base">
                    Enter a repository and branch to launch a live evaluation run.
                  </p>
                </div>

                <form onSubmit={onSubmit} className="space-y-5">
                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground" htmlFor="repo-url">
                      GitHub repository URL
                    </label>
                    <input
                      id="repo-url"
                      type="url"
                      required
                      value={repoUrl}
                      onChange={(event) => onRepoUrlChange(event.target.value)}
                      placeholder="https://github.com/owner/repo"
                      className="h-14 w-full rounded-2xl border border-border bg-background px-4 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
                    />
                  </div>

                  <div className="space-y-2">
                    <label className="text-sm font-medium text-foreground" htmlFor="branch">
                      Branch
                    </label>
                    <input
                      id="branch"
                      type="text"
                      value={branch}
                      onChange={(event) => onBranchChange(event.target.value)}
                      placeholder="main"
                      className="h-14 w-full rounded-2xl border border-border bg-background px-4 text-sm outline-none transition focus:border-ring focus:ring-2 focus:ring-ring/30"
                    />
                  </div>

                  {error ? (
                    <div className="rounded-2xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                      {error}
                    </div>
                  ) : null}

                  <Button
                    type="submit"
                    size="lg"
                    className="h-14 w-full rounded-2xl text-base font-semibold"
                    disabled={isSubmitting}
                  >
                    {isSubmitting ? "Starting analysis..." : "Start Analysis"}
                    <MoveRight className="size-4" />
                  </Button>
                </form>
              </div>
            </section>
            <RecentRunsPanel runs={recentRuns} onOpenRun={onOpenRun} />
          </div>
        </div>
      </div>
    </main>
  );
}

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { ArrowLeft, ArrowRight, Zap } from "lucide-react";
import { cn } from "@/lib/utils";
import { useEventsStore } from "@/lib/events-store";
import { StepProgress } from "./step-progress";
import { Step1Basics } from "./step1-basics";
import { Step2Artifacts } from "./step2-artifacts";
import { Step3Judging } from "./step3-judging";
import { EventCreatedShareModal } from "./event-created-share-modal";

export interface CriterionState {
  selected: boolean;
  weight: number;
}

export const ARTIFACT_CRITERION_IDS: Record<string, string[]> = {
  repo:         ["repo_completeness", "repo_impl_quality", "repo_code_quality", "repo_documentation", "repo_depth"],
  presentation: ["pres_clarity", "pres_structure", "pres_solution", "pres_design", "pres_impact"],
  report:       ["report_problem", "report_methodology", "report_depth", "report_results", "report_writing"],
  demo:         ["demo_clarity", "demo_coverage", "demo_functionality", "demo_narration", "demo_quality"],
  live:         ["live_clarity", "live_understanding", "live_delivery", "live_qa", "live_coordination"],
};

export interface EventFormData {
  name: string;
  type: "hackathon" | "course" | "custom";
  submissionDeadline: string;
  description: string;
  artifacts: string[];
  criteria: Record<string, CriterionState>;
}

const d = (w: number): CriterionState => ({ selected: true, weight: w });

const INITIAL_DATA: EventFormData = {
  name: "",
  type: "hackathon",
  submissionDeadline: "",
  description: "",
  artifacts: ["repo", "presentation"],
  criteria: {
    repo_completeness:  d(20), repo_impl_quality:  d(20), repo_code_quality: d(20), repo_documentation: d(20), repo_depth:        d(20),
    pres_clarity:       d(20), pres_structure:     d(20), pres_solution:     d(20), pres_design:        d(20), pres_impact:       d(20),
    report_problem:     d(20), report_methodology: d(20), report_depth:      d(20), report_results:     d(20), report_writing:    d(20),
    demo_clarity:       d(20), demo_coverage:      d(20), demo_functionality:d(20), demo_narration:     d(20), demo_quality:      d(20),
    live_clarity:       d(20), live_understanding: d(20), live_delivery:     d(20), live_qa:            d(20), live_coordination: d(20),
    always_innovation:  d(50), always_impact:      d(50),
  },
};

const STEPS = [
  { label: "Event",       description: "Name and dates" },
  { label: "Submissions", description: "What teams submit" },
  { label: "Criteria",    description: "How to evaluate" },
];

function isStep1Valid(data: EventFormData) {
  if (!data.name.trim()) return false;
  const parts = data.submissionDeadline.split("-");
  return parts.length === 3 && parts[0].length === 4 && !!parts[1] && !!parts[2] && parts[2] !== "00";
}

function isStep2Valid(data: EventFormData) {
  return data.artifacts.length > 0;
}

function isStep3Valid(data: EventFormData) {
  const relevant = data.artifacts.filter(a => a in ARTIFACT_CRITERION_IDS);
  if (relevant.length === 0) return false;
  return relevant.every(artifactId => {
    const ids      = ARTIFACT_CRITERION_IDS[artifactId] ?? [];
    const selected = ids.filter(id => data.criteria[id]?.selected);
    if (selected.length === 0) return false;
    const total = selected.reduce((sum, id) => sum + (data.criteria[id]?.weight ?? 0), 0);
    return total === 100;
  });
}

const slideVariants = {
  enter:  (dir: number) => ({ x: dir > 0 ?  48 : -48, opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit:   (dir: number) => ({ x: dir > 0 ? -48 :  48, opacity: 0 }),
};

export function CreateEventWizard() {
  const router    = useRouter();
  const createEvent  = useEventsStore((s) => s.createEvent);
  const [step, setStep]           = useState(0);
  const [direction, setDirection] = useState(1);
  const [data, setData]           = useState<EventFormData>(INITIAL_DATA);
  const [isCreating, setIsCreating] = useState(false);
  const [shareModal, setShareModal] = useState<{ open: boolean; eventId: string; eventName: string }>({
    open: false,
    eventId: "",
    eventName: "",
  });

  const update = (partial: Partial<EventFormData>) =>
    setData((prev) => ({ ...prev, ...partial }));

  const next = () => { setDirection(1);  setStep((s) => Math.min(s + 1, STEPS.length - 1)); };
  const back = () => { setDirection(-1); setStep((s) => Math.max(s - 1, 0)); };

  const canAdvance =
    step === 0 ? isStep1Valid(data) :
    step === 1 ? isStep2Valid(data) :
    isStep3Valid(data);

  const handleCreate = async () => {
    if (!canAdvance) return;
    setIsCreating(true);
    try {
      const event = await createEvent({
        name: data.name.trim(),
        type: data.type,
        status: "active",
        description: data.description,
        submissionDeadline: data.submissionDeadline,
        judgingDeadline: data.submissionDeadline,
        artifacts: data.artifacts,
        criteriaConfig: { criteria: data.criteria, artifacts: data.artifacts },
      });
      setShareModal({ open: true, eventId: event.id, eventName: event.name });
    } finally {
      setIsCreating(false);
    }
  };

  const closeShareModal = () => {
    setShareModal((m) => ({ ...m, open: false }));
    router.push("/home");
  };

  return (
    <div className="min-h-screen bg-background">
      {/* Nav */}
      <nav className="flex items-center justify-between border-b border-neutral-800 bg-background/80 px-6 sm:px-10 py-4 backdrop-blur-md sticky top-0 z-10">
        <Link
          href="/home"
          className="flex items-center gap-2 text-sm font-medium text-neutral-400 transition-colors hover:text-white w-20"
        >
          <ArrowLeft className="h-4 w-4" />
          Back
        </Link>

        <StepProgress steps={STEPS} currentStep={step} />

        <div className="w-16" />
      </nav>

      {/* Content — add bottom padding so sticky footer never overlaps content */}
      <div className={cn(
        "mx-auto px-4 sm:px-6 pt-10 pb-28",
        step === 2 ? "max-w-4xl" : "max-w-xl",
      )}>

        {/* Step content */}
        <div className="relative overflow-hidden">
          <AnimatePresence mode="wait" custom={direction}>
            <motion.div
              key={step}
              custom={direction}
              variants={slideVariants}
              initial="enter"
              animate="center"
              exit="exit"
              transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] }}
            >
              {step === 0 && <Step1Basics   data={data} onChange={update} />}
              {step === 1 && <Step2Artifacts data={data} onChange={update} />}
              {step === 2 && <Step3Judging  data={data} onChange={update} />}
            </motion.div>
          </AnimatePresence>
        </div>
      </div>

      {/* Sticky footer — always visible, no scroll needed */}
      <div className="fixed bottom-0 left-0 right-0 z-20 border-t border-neutral-800 bg-background/90 backdrop-blur-md px-6 sm:px-10 py-4">
        <div className={cn(
          "mx-auto flex items-center justify-between",
          step === 2 ? "max-w-4xl" : "max-w-xl",
        )}>
          <button
            type="button"
            onClick={back}
            disabled={step === 0}
            className="flex items-center gap-2 rounded-xl border border-neutral-700 px-5 py-2.5 text-sm font-medium text-neutral-400 transition-colors hover:border-neutral-500 hover:text-white disabled:pointer-events-none disabled:opacity-0"
          >
            <ArrowLeft className="h-4 w-4" />
            Back
          </button>

          {step < STEPS.length - 1 ? (
            <button
              type="button"
              onClick={next}
              disabled={!canAdvance}
              className="flex items-center gap-2 rounded-xl bg-violet px-7 py-2.5 text-sm font-semibold text-white shadow-lg transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed glow-violet-sm"
            >
              Next
              <ArrowRight className="h-4 w-4" />
            </button>
          ) : (
            <button
              type="button"
              onClick={handleCreate}
              disabled={isCreating || !canAdvance}
              className="flex items-center gap-2 rounded-xl bg-violet px-6 py-2.5 text-sm font-semibold text-white shadow-lg transition-opacity hover:opacity-90 disabled:opacity-40 disabled:cursor-not-allowed glow-violet-sm"
            >
              {isCreating ? (
                <>
                  <motion.div
                    animate={{ rotate: 360 }}
                    transition={{ duration: 0.8, repeat: Infinity, ease: "linear" }}
                    className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white"
                  />
                  Creating...
                </>
              ) : (
                <>
                  <Zap className="h-4 w-4" fill="currentColor" />
                  Create Event
                </>
              )}
            </button>
          )}
        </div>
      </div>

      <EventCreatedShareModal
        open={shareModal.open}
        eventId={shareModal.eventId}
        eventName={shareModal.eventName}
        onClose={closeShareModal}
      />
    </div>
  );
}
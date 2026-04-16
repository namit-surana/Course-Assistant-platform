"use client";

import { motion } from "framer-motion";
import { Check } from "lucide-react";
import { cn } from "@/lib/utils";

interface Step {
  label: string;
  description: string;
}

interface StepProgressProps {
  steps: Step[];
  currentStep: number;
}

export function StepProgress({ steps, currentStep }: StepProgressProps) {
  return (
    <div className="flex items-center gap-0">
      {steps.map((step, index) => {
        const isCompleted = index < currentStep;
        const isActive = index === currentStep;
        const isLast = index === steps.length - 1;

        return (
          <div key={step.label} className="flex items-center">
            {/* Step node */}
            <div className="flex items-center gap-2">
              <motion.div
                animate={{
                  backgroundColor: isCompleted ? "var(--violet)" : "transparent",
                  borderColor: isCompleted
                    ? "var(--violet)"
                    : isActive
                    ? "var(--violet)"
                    : "oklch(1 0 0 / 20%)",
                  scale: isActive ? 1.05 : 1,
                }}
                transition={{ duration: 0.3, ease: "easeOut" }}
                className={cn(
                  "flex h-8 w-8 items-center justify-center rounded-full border-2 transition-shadow flex-shrink-0",
                  isActive && "shadow-[0_0_14px_oklch(0.65_0.22_280_/_40%)]",
                )}
              >
                {isCompleted ? (
                  <motion.div initial={{ scale: 0 }} animate={{ scale: 1 }} transition={{ type: "spring", stiffness: 500, damping: 25 }}>
                    <Check className="h-3.5 w-3.5 text-white" strokeWidth={3} />
                  </motion.div>
                ) : (
                  <span className={cn("text-xs font-bold", isActive ? "text-violet" : "text-neutral-600")}>
                    {index + 1}
                  </span>
                )}
              </motion.div>

              <span className={cn(
                "text-sm font-semibold whitespace-nowrap",
                isActive ? "text-white" : isCompleted ? "text-violet" : "text-neutral-600",
              )}>
                {step.label}
              </span>
            </div>

            {/* Connector line */}
            {!isLast && (
              <div className="relative mx-4 h-[2px] w-16 sm:w-24 bg-neutral-800 overflow-hidden">
                <motion.div
                  className="absolute inset-y-0 left-0 bg-violet"
                  animate={{ width: isCompleted ? "100%" : "0%" }}
                  transition={{ duration: 0.4, ease: "easeOut" }}
                />
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

"use client";

import React, { useMemo, useState } from "react";
import {
  CheckCircle2,
  Circle,
  CircleAlert,
  CircleDotDashed,
  CircleX,
} from "lucide-react";
import { AnimatePresence, LayoutGroup, motion } from "framer-motion";

import type { ItemStatus, PlanTask } from "@/lib/types";

interface AgentPlanProps {
  tasks: PlanTask[];
}

function ActivityTone({ status }: { status: ItemStatus }) {
  if (status === "failed") {
    return "border-red-500/20 bg-red-500/8 text-red-100/90";
  }
  if (status === "in-progress") {
    return "border-blue-500/20 bg-blue-500/8 text-foreground";
  }
  if (status === "completed") {
    return "border-border bg-background/40 text-muted-foreground";
  }
  return "border-border bg-background/30 text-muted-foreground";
}

function StatusIcon({ status, size = "task" }: { status: ItemStatus; size?: "task" | "subtask" }) {
  const className = size === "task" ? "h-[18px] w-[18px]" : "h-3.5 w-3.5";

  if (status === "completed") {
    return <CheckCircle2 className={`${className} text-green-500`} />;
  }
  if (status === "in-progress") {
    return <CircleDotDashed className={`${className} text-blue-500`} />;
  }
  if (status === "failed") {
    return <CircleX className={`${className} text-red-500`} />;
  }
  if (status === "skipped") {
    return <CircleAlert className={`${className} text-yellow-500`} />;
  }
  return <Circle className={`${className} text-muted-foreground`} />;
}

function StatusBadge({ status }: { status: ItemStatus }) {
  return (
    <span
      className={`rounded px-1.5 py-0.5 text-[11px] font-medium ${
        status === "completed"
          ? "bg-green-100 text-green-700"
          : status === "in-progress"
            ? "bg-blue-100 text-blue-700"
            : status === "failed"
              ? "bg-red-100 text-red-700"
              : status === "skipped"
                ? "bg-yellow-100 text-yellow-700"
                : "bg-muted text-muted-foreground"
      }`}
    >
      {status}
    </span>
  );
}

export default function AgentPlan({ tasks }: AgentPlanProps) {
  const autoExpandedTasks = useMemo(
    () => tasks.filter((task) => task.status === "in-progress" || task.status === "failed").map((task) => task.id),
    [tasks],
  );
  const [taskExpansionOverrides, setTaskExpansionOverrides] = useState<Record<string, boolean>>({});
  const [expandedSubtasks, setExpandedSubtasks] = useState<Record<string, boolean>>({});

  const prefersReducedMotion =
    typeof window !== "undefined"
      ? window.matchMedia("(prefers-reduced-motion: reduce)").matches
      : false;

  const toggleTaskExpansion = (taskId: string, isExpanded: boolean) => {
    setTaskExpansionOverrides((prev) => ({
      ...prev,
      [taskId]: !isExpanded,
    }));
  };

  const toggleSubtaskExpansion = (taskId: string, subtaskId: string) => {
    const key = `${taskId}-${subtaskId}`;
    setExpandedSubtasks((prev) => ({
      ...prev,
      [key]: !prev[key],
    }));
  };

  const appleEase = [0.2, 0.65, 0.3, 0.9] as const;
  const springyEase = [0.34, 1.56, 0.64, 1] as const;
  const animType = (prefersReducedMotion ? "tween" : "spring") as "tween" | "spring";

  const taskVariants = {
    hidden: { opacity: 0, y: prefersReducedMotion ? 0 : -5 },
    visible: {
      opacity: 1,
      y: 0,
      transition: {
        type: animType,
        stiffness: 500,
        damping: 30,
        duration: prefersReducedMotion ? 0.2 : undefined,
      },
    },
    exit: {
      opacity: 0,
      y: prefersReducedMotion ? 0 : -5,
      transition: { duration: 0.15 },
    },
  };

  const subtaskListVariants = {
    hidden: { opacity: 0, height: 0, overflow: "hidden" },
    visible: {
      height: "auto",
      opacity: 1,
      overflow: "visible",
      transition: {
        duration: 0.25,
        staggerChildren: prefersReducedMotion ? 0 : 0.05,
        when: "beforeChildren" as const,
        ease: appleEase,
      },
    },
    exit: {
      height: 0,
      opacity: 0,
      overflow: "hidden",
      transition: { duration: 0.2, ease: appleEase },
    },
  };

  const subtaskVariants = {
    hidden: { opacity: 0, x: prefersReducedMotion ? 0 : -10 },
    visible: {
      opacity: 1,
      x: 0,
      transition: {
        type: animType,
        stiffness: 500,
        damping: 25,
        duration: prefersReducedMotion ? 0.2 : undefined,
      },
    },
    exit: {
      opacity: 0,
      x: prefersReducedMotion ? 0 : -10,
      transition: { duration: 0.15 },
    },
  };

  const subtaskDetailsVariants = {
    hidden: { opacity: 0, height: 0, overflow: "hidden" },
    visible: {
      opacity: 1,
      height: "auto",
      overflow: "visible",
      transition: { duration: 0.25, ease: appleEase },
    },
  };

  const statusBadgeVariants = {
    initial: { scale: 1 },
    animate: {
      scale: prefersReducedMotion ? 1 : ([1, 1.08, 1] as number[]),
      transition: {
        duration: 0.35,
        ease: springyEase,
      },
    },
  };

  return (
    <div className="bg-background text-foreground h-full overflow-auto p-2">
      <motion.div
        className="bg-card border-border rounded-lg border shadow overflow-hidden"
        initial={{ opacity: 0, y: 10 }}
        animate={{
          opacity: 1,
          y: 0,
          transition: { duration: 0.3, ease: [0.2, 0.65, 0.3, 0.9] },
        }}
      >
        <LayoutGroup>
          <div className="p-4 overflow-hidden">
            <ul className="space-y-1 overflow-hidden">
              {tasks.map((task, index) => {
                const isExpanded = taskExpansionOverrides[task.id] ?? autoExpandedTasks.includes(task.id);
                const isCompleted = task.status === "completed";

                return (
                  <motion.li
                    key={task.id}
                    className={index !== 0 ? "mt-1 pt-2" : ""}
                    initial="hidden"
                    animate="visible"
                    variants={taskVariants}
                  >
                    <motion.div
                      className="group flex items-center px-3 py-1.5 rounded-md"
                      whileHover={{
                        backgroundColor: "rgba(0,0,0,0.03)",
                        transition: { duration: 0.2 },
                      }}
                    >
                      <div className="mr-2 flex-shrink-0">
                        <StatusIcon status={task.status} />
                      </div>

                      <motion.div
                        className="flex min-w-0 flex-grow cursor-pointer items-center justify-between"
                        onClick={() => toggleTaskExpansion(task.id, isExpanded)}
                      >
                        <div className="mr-2 flex-1 truncate">
                          <span className={isCompleted ? "text-muted-foreground" : ""}>
                            {task.title}
                          </span>
                        </div>

                        <div className="flex flex-shrink-0 items-center space-x-2 text-xs">
                          {task.dependencies.length > 0 && (
                            <div className="flex items-center mr-2">
                              <div className="flex flex-wrap gap-1">
                                {task.dependencies.map((dependency, idx) => (
                                  <motion.span
                                    key={dependency}
                                    className="bg-secondary/40 text-secondary-foreground rounded px-1.5 py-0.5 text-[10px] font-medium shadow-sm"
                                    initial={{ opacity: 0, scale: 0.9 }}
                                    animate={{ opacity: 1, scale: 1 }}
                                    transition={{ duration: 0.2, delay: idx * 0.05 }}
                                  >
                                    {dependency}
                                  </motion.span>
                                ))}
                              </div>
                            </div>
                          )}

                          <motion.span
                            variants={statusBadgeVariants}
                            initial="initial"
                            animate="animate"
                            key={task.status}
                          >
                            <StatusBadge status={task.status} />
                          </motion.span>
                        </div>
                      </motion.div>
                    </motion.div>

                    <AnimatePresence mode="wait">
                      {isExpanded && task.subtasks.length > 0 && (
                        <motion.div
                          className="relative overflow-hidden"
                          variants={subtaskListVariants}
                          initial="hidden"
                          animate="visible"
                          exit="hidden"
                          layout
                        >
                          <div className="absolute top-0 bottom-0 left-[20px] border-l-2 border-dashed border-muted-foreground/30" />
                          <ul className="mt-1 mr-2 mb-1.5 ml-3 space-y-0.5">
                            {task.subtasks.map((subtask) => {
                              const subtaskKey = `${task.id}-${subtask.id}`;
                              const isSubtaskExpanded =
                                expandedSubtasks[subtaskKey] ?? subtask.status === "in-progress";

                              return (
                                <motion.li
                                  key={subtask.id}
                                  className="group flex flex-col py-0.5 pl-6"
                                  onClick={() => toggleSubtaskExpansion(task.id, subtask.id)}
                                  variants={subtaskVariants}
                                  initial="hidden"
                                  animate="visible"
                                  exit="exit"
                                  layout
                                >
                                  <motion.div
                                    className="flex flex-1 items-center rounded-md p-1"
                                    whileHover={{
                                      backgroundColor: "rgba(0,0,0,0.03)",
                                      transition: { duration: 0.2 },
                                    }}
                                    layout
                                  >
                                    <div className="mr-2 flex-shrink-0">
                                      <StatusIcon status={subtask.status} size="subtask" />
                                    </div>

                                    <span
                                      className={`cursor-pointer text-sm ${
                                        subtask.status === "completed"
                                          ? "text-muted-foreground"
                                          : ""
                                      }`}
                                    >
                                      {subtask.title}
                                    </span>
                                  </motion.div>

                                  <AnimatePresence mode="wait">
                                    {isSubtaskExpanded && (
                                      <motion.div
                                        className="text-muted-foreground border-foreground/20 mt-1 ml-1.5 border-l border-dashed pl-5 text-xs overflow-hidden"
                                        variants={subtaskDetailsVariants}
                                        initial="hidden"
                                        animate="visible"
                                        exit="hidden"
                                        layout
                                      >
                                        <p className="py-1">{subtask.description}</p>
                                        {subtask.tools && subtask.tools.length > 0 && (
                                          <div className="mt-0.5 mb-1 flex flex-wrap items-center gap-1.5">
                                            <span className="text-muted-foreground font-medium">
                                              Live Tags:
                                            </span>
                                            <div className="flex flex-wrap gap-1">
                                              {subtask.tools.map((tool, idx) => (
                                                <motion.span
                                                  key={`${subtask.id}-${tool}`}
                                                  className="bg-secondary/40 text-secondary-foreground rounded px-1.5 py-0.5 text-[10px] font-medium shadow-sm"
                                                  initial={{ opacity: 0, y: -5 }}
                                                  animate={{
                                                    opacity: 1,
                                                    y: 0,
                                                    transition: { duration: 0.2, delay: idx * 0.05 },
                                                  }}
                                                >
                                                  {tool}
                                                </motion.span>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                        {subtask.activity && subtask.activity.length > 0 && (
                                          <div className="mt-2 space-y-1.5">
                                            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-blue-500">
                                              {subtask.status === "in-progress"
                                                ? "Live Activity"
                                                : "Activity History"}
                                            </p>
                                            <div className="space-y-1.5">
                                              {subtask.activity.map((activityItem, idx) => (
                                                <div
                                                  key={`${subtask.id}-activity-${idx}`}
                                                  className={`rounded-md border px-2.5 py-2 text-[11px] leading-5 ${ActivityTone({
                                                    status: subtask.status,
                                                  })}`}
                                                >
                                                  {activityItem}
                                                </div>
                                              ))}
                                            </div>
                                          </div>
                                        )}
                                      </motion.div>
                                    )}
                                  </AnimatePresence>
                                </motion.li>
                              );
                            })}
                          </ul>
                        </motion.div>
                      )}
                    </AnimatePresence>
                  </motion.li>
                );
              })}
            </ul>
          </div>
        </LayoutGroup>
      </motion.div>
    </div>
  );
}

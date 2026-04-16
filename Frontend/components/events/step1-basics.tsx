"use client";

import { cn } from "@/lib/utils";
import type { EventFormData } from "./create-event-wizard";

const EVENT_TYPES = [
  { value: "hackathon", label: "Hackathon" },
  { value: "course",    label: "Course Eval" },
  { value: "custom",    label: "Custom" },
] as const;

const inputClass =
  "h-13 w-full rounded-xl border border-neutral-700 bg-neutral-900 px-4 text-base text-white placeholder:text-neutral-600 outline-none transition focus:border-violet focus:ring-2 focus:ring-violet/20";

const labelClass = "text-sm font-semibold text-neutral-300";

interface Step1Props {
  data: EventFormData;
  onChange: (data: Partial<EventFormData>) => void;
}

export function Step1Basics({ data, onChange }: Step1Props) {
  return (
    <div className="flex flex-col gap-7">

      {/* Event name */}
      <div className="flex flex-col gap-2.5">
        <label className={labelClass}>
          Event Name <span className="text-red-400">*</span>
        </label>
        <input
          type="text"
          value={data.name}
          onChange={(e) => onChange({ name: e.target.value })}
          placeholder="e.g. Spring Hackathon 2025"
          className={inputClass}
        />
      </div>

      {/* Event type */}
      <div className="flex flex-col gap-2.5">
        <label className={labelClass}>
          Event Type <span className="text-red-400">*</span>
        </label>
        <div className="flex gap-3 flex-wrap">
          {EVENT_TYPES.map((type) => (
            <button
              key={type.value}
              type="button"
              onClick={() => onChange({ type: type.value })}
              className={cn(
                "rounded-xl border px-6 py-3 text-sm font-semibold transition-all",
                data.type === type.value
                  ? "border-violet bg-violet/15 text-violet shadow-[0_0_16px_oklch(0.65_0.22_280_/_25%)]"
                  : "border-neutral-700 bg-neutral-900 text-neutral-400 hover:border-neutral-500 hover:text-white",
              )}
            >
              {type.label}
            </button>
          ))}
        </div>
      </div>

      {/* Submission deadline */}
      <div className="flex flex-col gap-2.5">
        <label className={labelClass}>
          Submission Deadline <span className="text-red-400">*</span>
        </label>
        <div className="flex gap-3">
          {/* Day */}
          <div className="flex flex-col gap-1.5 flex-1">
            <span className="text-xs text-neutral-500 font-medium">Day</span>
            <input
              type="number"
              min={1}
              max={31}
              placeholder="DD"
              value={data.submissionDeadline ? parseInt(data.submissionDeadline.split("-")[2]) || "" : ""}
              onChange={(e) => {
                const parts = data.submissionDeadline ? data.submissionDeadline.split("-") : ["", "", ""];
                const day = e.target.value.padStart(2, "0");
                onChange({ submissionDeadline: `${parts[0] || "2025"}-${parts[1] || "01"}-${day}` });
              }}
              className="h-13 w-full rounded-xl border border-neutral-700 bg-neutral-900 px-4 text-base text-white placeholder:text-neutral-600 outline-none transition focus:border-violet focus:ring-2 focus:ring-violet/20 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            />
          </div>
          {/* Month */}
          <div className="flex flex-col gap-1.5 flex-1">
            <span className="text-xs text-neutral-500 font-medium">Month</span>
            <select
              value={data.submissionDeadline ? data.submissionDeadline.split("-")[1] || "" : ""}
              onChange={(e) => {
                const parts = data.submissionDeadline ? data.submissionDeadline.split("-") : ["", "", ""];
                onChange({ submissionDeadline: `${parts[0] || "2025"}-${e.target.value}-${parts[2] || "01"}` });
              }}
              className="h-13 w-full rounded-xl border border-neutral-700 bg-neutral-900 px-4 text-base text-white outline-none transition focus:border-violet focus:ring-2 focus:ring-violet/20 appearance-none"
            >
              <option value="" disabled className="text-neutral-600">Month</option>
              {["January","February","March","April","May","June","July","August","September","October","November","December"].map((m, i) => (
                <option key={m} value={String(i + 1).padStart(2, "0")} className="bg-neutral-900">{m}</option>
              ))}
            </select>
          </div>
          {/* Year */}
          <div className="flex flex-col gap-1.5 flex-1">
            <span className="text-xs text-neutral-500 font-medium">Year</span>
            <input
              type="number"
              min={2024}
              max={2030}
              placeholder="YYYY"
              value={data.submissionDeadline ? parseInt(data.submissionDeadline.split("-")[0]) || "" : ""}
              onChange={(e) => {
                const parts = data.submissionDeadline ? data.submissionDeadline.split("-") : ["", "", ""];
                onChange({ submissionDeadline: `${e.target.value}-${parts[1] || "01"}-${parts[2] || "01"}` });
              }}
              className="h-13 w-full rounded-xl border border-neutral-700 bg-neutral-900 px-4 text-base text-white placeholder:text-neutral-600 outline-none transition focus:border-violet focus:ring-2 focus:ring-violet/20 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none [&::-webkit-outer-spin-button]:appearance-none"
            />
          </div>
        </div>
      </div>

      {/* Description */}
      <div className="flex flex-col gap-2.5">
        <label className={labelClass}>
          Description
          <span className="ml-2 text-xs font-normal text-neutral-600">(optional)</span>
        </label>
        <textarea
          value={data.description}
          onChange={(e) => onChange({ description: e.target.value })}
          placeholder="Brief description of this event..."
          rows={4}
          className="w-full resize-none rounded-xl border border-neutral-700 bg-neutral-900 px-4 py-3.5 text-base text-white placeholder:text-neutral-600 outline-none transition focus:border-violet focus:ring-2 focus:ring-violet/20"
        />
      </div>
    </div>
  );
}

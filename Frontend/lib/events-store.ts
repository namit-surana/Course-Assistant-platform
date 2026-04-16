import { create } from "zustand";
import type { EvalEvent, Submission, AnalysisRunState } from "./types";
import { MOCK_EVENTS } from "./mock-data";

interface EventsStore {
  events: EvalEvent[];
  addEvent: (event: EvalEvent) => void;
  submissions: Record<string, Submission[]>;
  addSubmission: (eventId: string, submission: Submission) => void;
  updateSubmission: (eventId: string, runId: string, run: AnalysisRunState) => void;
}

export const useEventsStore = create<EventsStore>((set) => ({
  events: MOCK_EVENTS,
  addEvent: (event) =>
    set((state) => ({ events: [event, ...state.events] })),

  submissions: {},
  addSubmission: (eventId, submission) =>
    set((state) => ({
      submissions: {
        ...state.submissions,
        [eventId]: [submission, ...(state.submissions[eventId] ?? [])],
      },
    })),
  updateSubmission: (eventId, runId, run) =>
    set((state) => ({
      submissions: {
        ...state.submissions,
        [eventId]: (state.submissions[eventId] ?? []).map((s) =>
          s.runId === runId ? { ...s, run } : s
        ),
      },
    })),
}));

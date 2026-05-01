import { create } from "zustand";
import type { EvalEvent, Submission, AnalysisRunState, VoiceStatus, VoiceTranscriptArtifact } from "./types";
import { MOCK_EVENTS } from "./mock-data";

interface EventsStore {
  events: EvalEvent[];
  addEvent: (event: EvalEvent) => void;
  submissions: Record<string, Submission[]>;
  addSubmission: (eventId: string, submission: Submission) => void;
  updateSubmission: (eventId: string, runId: string, run: AnalysisRunState) => void;
  updateSubmissionVoiceStatus: (
    eventId: string,
    submissionId: string,
    status: VoiceStatus,
  ) => void;
  updateSubmissionVoiceTranscript: (
    eventId: string,
    submissionId: string,
    transcript: VoiceTranscriptArtifact,
  ) => void;
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
  updateSubmissionVoiceStatus: (eventId, submissionId, status) =>
    set((state) => ({
      submissions: {
        ...state.submissions,
        [eventId]: (state.submissions[eventId] ?? []).map((s) =>
          s.id === submissionId ? { ...s, voiceStatus: status } : s
        ),
      },
    })),
  updateSubmissionVoiceTranscript: (eventId, submissionId, transcript) =>
    set((state) => ({
      submissions: {
        ...state.submissions,
        [eventId]: (state.submissions[eventId] ?? []).map((s) =>
          s.id === submissionId
            ? { ...s, voiceTranscript: transcript, voiceStatus: "completed" }
            : s
        ),
      },
    })),
}));

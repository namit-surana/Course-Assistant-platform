import { create } from "zustand";
import type {
  EvalEvent,
  Submission,
  AnalysisRunState,
  VoiceStatus,
  VoiceTranscriptArtifact,
} from "./types";
import {
  createEvent,
  deleteEvent as deleteEventApi,
  fetchEventSubmissions,
  fetchEvents,
  type CreateEventInput,
} from "./events-api";
  VideoAnalysisStatus,
  WorkerVideoAnalysisJob,
} from "./types";
import { createEvent, fetchEventSubmissions, fetchEvents, type CreateEventInput } from "./events-api";

interface EventsStore {
  events: EvalEvent[];
  isLoadingEvents: boolean;
  eventsError: string | null;

  loadEvents: () => Promise<void>;
  createEvent: (event: CreateEventInput) => Promise<EvalEvent>;
  deleteEvent: (eventId: string) => Promise<void>;
  addEvent: (event: EvalEvent) => void;

  submissions: Record<string, Submission[]>;
  loadSubmissions: (eventId: string) => Promise<void>;
  addSubmission: (eventId: string, submission: Submission) => void;
  updateSubmission: (
    eventId: string,
    runId: string,
    run: AnalysisRunState
  ) => void;

  updateSubmissionVoiceStatus: (
    eventId: string,
    submissionId: string,
    status: VoiceStatus
  ) => void;

  updateSubmissionVoiceTranscript: (
    eventId: string,
    submissionId: string,
    transcript: VoiceTranscriptArtifact
  ) => void;
  updateSubmissionVideoState: (
    eventId: string,
    submissionId: string,
    patch: {
      videoAnalysisStatus?: VideoAnalysisStatus;
      videoAnalysisJobId?: string;
      videoAnalysisResult?: WorkerVideoAnalysisJob | null;
    },
  ) => void;
}

export const useEventsStore = create<EventsStore>((set) => ({
  events: [],
  isLoadingEvents: false,
  eventsError: null,

  loadEvents: async () => {
    set({ isLoadingEvents: true, eventsError: null });

    try {
      const events = await fetchEvents();
      set({ events, isLoadingEvents: false });
    } catch (error) {
      set({
        isLoadingEvents: false,
        eventsError:
          error instanceof Error ? error.message : "Unable to load events.",
      });
    }
  },

  createEvent: async (event) => {
    const created = await createEvent(event);
    set((state) => ({ events: [created, ...state.events] }));
    return created;
  },

  deleteEvent: async (eventId) => {
    await deleteEventApi(eventId);

    set((state) => {
      const nextSubmissions = { ...state.submissions };
      delete nextSubmissions[eventId];

      return {
        events: state.events.filter((event) => event.id !== eventId),
        submissions: nextSubmissions,
      };
    });
  },

  addEvent: (event) =>
    set((state) => ({ events: [event, ...state.events] })),

  submissions: {},

  loadSubmissions: async (eventId) => {
    const submissions = await fetchEventSubmissions(eventId);

    set((state) => ({
      submissions: {
        ...state.submissions,
        [eventId]: submissions,
      },
    }));
  },

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
  updateSubmissionVideoState: (eventId, submissionId, patch) =>
    set((state) => ({
      submissions: {
        ...state.submissions,
        [eventId]: (state.submissions[eventId] ?? []).map((s) =>
          s.id === submissionId
            ? {
                ...s,
                videoAnalysisStatus: patch.videoAnalysisStatus ?? s.videoAnalysisStatus,
                videoAnalysisJobId: patch.videoAnalysisJobId ?? s.videoAnalysisJobId,
                videoAnalysisResult:
                  patch.videoAnalysisResult !== undefined
                    ? patch.videoAnalysisResult
                    : s.videoAnalysisResult,
              }
            : s
        ),
      },
    })),
}));

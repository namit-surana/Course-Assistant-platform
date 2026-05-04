"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  X,
  GitBranch,
  Clock,
  Loader2,
  XCircle,
  ExternalLink,
} from "lucide-react";
import { cn } from "@/lib/utils";
import { mapRunToPlan } from "@/lib/run-utils";
import { ResultsPanel } from "@/components/analyze/results-panel";
import AgentPlan from "@/components/ui/agent-plan";
import type { Submission } from "@/lib/types";
import { useEventsStore } from "@/lib/events-store";
import {
  fetchWorkerVideoAnalysisJob,
  startWorkerSubmissionVideoAnalysis,
} from "@/lib/backend-submissions";

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/$/, "") || "http://127.0.0.1:8000";

function shortUrl(url: string) {
  return url.replace(/^https?:\/\/(www\.)?github\.com\//, "");
}

interface Props {
  eventId: string;
  submission: Submission;
  onClose: () => void;
}

export function SubmissionDetailPanel({ eventId, submission, onClose }: Props) {
  const run = submission.run;
  const planTasks = mapRunToPlan(run);
  const updateVoiceStatus = useEventsStore((s) => s.updateSubmissionVoiceStatus);
  const updateVoiceTranscript = useEventsStore((s) => s.updateSubmissionVoiceTranscript);
  const updateVideoState = useEventsStore((s) => s.updateSubmissionVideoState);
  const [partialTranscript, setPartialTranscript] = useState("");
  const [recordError, setRecordError] = useState<string | null>(null);
  const [isRecording, setIsRecording] = useState(false);
  const [showFullTranscript, setShowFullTranscript] = useState(false);
  const [copied, setCopied] = useState(false);
  const [videoError, setVideoError] = useState<string | null>(null);
  const [videoAssignmentTitle, setVideoAssignmentTitle] = useState("Course project demo");
  const [videoFeaturesText, setVideoFeaturesText] = useState("");
  const awaitingSaveRef = useRef(false);
  const socketRef = useRef<WebSocket | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const processorRef = useRef<ScriptProcessorNode | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const wsScheme = typeof window !== "undefined" && window.location.protocol === "https:" ? "wss" : "ws";
  const wsBase = useMemo(() => API_BASE_URL.replace(/^http/, wsScheme), [wsScheme]);

  const totalPhases = run.phases.length;
  const donePhases  = run.phases.filter((p) => p.status === "completed").length;
  const videoStatus = submission.videoAnalysisStatus ?? "idle";
  const hasVideoArtifact = Boolean(submission.videoFileName || submission.videoObjectKey);

  useEffect(() => {
    return () => {
      void stopRecording();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!submission.videoAnalysisJobId) {
      return;
    }
    if (videoStatus !== "pending" && videoStatus !== "running") {
      return;
    }
    let active = true;
    async function refreshVideoJob() {
      if (!submission.videoAnalysisJobId) {
        return;
      }
      try {
        const job = await fetchWorkerVideoAnalysisJob(submission.videoAnalysisJobId);
        if (!active) {
          return;
        }
        updateVideoState(eventId, submission.id, {
          videoAnalysisStatus: job.status,
          videoAnalysisResult: job,
        });
      } catch (err) {
        if (!active) {
          return;
        }
        setVideoError(err instanceof Error ? err.message : "Unable to poll video job.");
        updateVideoState(eventId, submission.id, { videoAnalysisStatus: "failed" });
      }
    }
    void refreshVideoJob();
    const intervalId = window.setInterval(() => {
      void refreshVideoJob();
    }, 1500);
    return () => {
      active = false;
      window.clearInterval(intervalId);
    };
  }, [
    eventId,
    submission.id,
    submission.videoAnalysisJobId,
    updateVideoState,
    videoStatus,
  ]);

  async function startRecording() {
    setRecordError(null);
    updateVoiceStatus(eventId, submission.id, "recording");
    try {
      const mediaStream = await navigator.mediaDevices.getUserMedia({ audio: true });
      mediaStreamRef.current = mediaStream;
      const audioContext = new AudioContext({ sampleRate: 16000 });
      audioContextRef.current = audioContext;
      const source = audioContext.createMediaStreamSource(mediaStream);
      sourceNodeRef.current = source;
      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorRef.current = processor;

      const wsUrl =
        `${wsBase}/api/voice-agent/stream?event_id=${encodeURIComponent(eventId)}` +
        `&submission_id=${encodeURIComponent(submission.id)}&language_code=eng`;
      const socket = new WebSocket(wsUrl);
      socketRef.current = socket;

      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        const messageType = payload.message_type;
        if (messageType === "partial_transcript") {
          setPartialTranscript(payload.text || "");
        }
        if (messageType === "session_saved" && payload.artifact) {
          updateVoiceTranscript(eventId, submission.id, payload.artifact);
          updateVoiceStatus(eventId, submission.id, "completed");
          awaitingSaveRef.current = false;
          setPartialTranscript("");
          socket.close();
        }
        if (messageType && String(messageType).includes("error")) {
          updateVoiceStatus(eventId, submission.id, "failed");
          awaitingSaveRef.current = false;
          setRecordError(payload.error || "Voice transcription failed.");
        }
      };

      socket.onerror = () => {
        setRecordError("Voice stream connection failed.");
        awaitingSaveRef.current = false;
        updateVoiceStatus(eventId, submission.id, "failed");
      };

      socket.onclose = () => {
        socketRef.current = null;
        if (awaitingSaveRef.current) {
          setRecordError("Voice stream closed before transcript was saved.");
          updateVoiceStatus(eventId, submission.id, "failed");
          awaitingSaveRef.current = false;
        }
      };

      processor.onaudioprocess = (audioEvent) => {
        if (socket.readyState !== WebSocket.OPEN) {
          return;
        }
        const input = audioEvent.inputBuffer.getChannelData(0);
        const pcm16 = float32ToInt16(input);
        socket.send(
          JSON.stringify({
            type: "audio_chunk",
            audio_base64: toBase64(pcm16.buffer),
            sample_rate: 16000,
            commit: false,
          }),
        );
      };

      source.connect(processor);
      processor.connect(audioContext.destination);
      setIsRecording(true);
    } catch (error) {
      setRecordError(error instanceof Error ? error.message : "Could not start recording.");
      updateVoiceStatus(eventId, submission.id, "failed");
    }
  }

  async function stopRecording() {
    if (!isRecording) {
      return;
    }
    setIsRecording(false);
    awaitingSaveRef.current = true;
    updateVoiceStatus(eventId, submission.id, "processing");
    const socket = socketRef.current;
    if (socket && socket.readyState === WebSocket.OPEN) {
      socket.send(JSON.stringify({ type: "stop" }));
    }
    processorRef.current?.disconnect();
    sourceNodeRef.current?.disconnect();
    audioContextRef.current?.close();
    mediaStreamRef.current?.getTracks().forEach((track) => track.stop());
    processorRef.current = null;
    sourceNodeRef.current = null;
    audioContextRef.current = null;
    mediaStreamRef.current = null;
  }

  async function copyTranscript() {
    const text = submission.voiceTranscript?.full_transcript?.trim();
    if (!text) {
      return;
    }
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      window.setTimeout(() => setCopied(false), 1200);
    } catch {
      setRecordError("Could not copy transcript.");
    }
  }

  async function startVideoAnalysis() {
    if (!submission.workerSubmissionId) {
      setVideoError("Missing submission id.");
      return;
    }
    if (!hasVideoArtifact) {
      setVideoError("No submitted video artifact found for this team.");
      return;
    }
    setVideoError(null);
    updateVideoState(eventId, submission.id, {
      videoAnalysisStatus: "pending",
      videoAnalysisResult: null,
    });
    try {
      const requiredFeatures = videoFeaturesText
        .split("\n")
        .map((line) => line.trim())
        .filter(Boolean);
      const started = await startWorkerSubmissionVideoAnalysis({
        submissionId: submission.workerSubmissionId,
        assignmentTitle: videoAssignmentTitle.trim() || "Course project demo",
        requiredFeatures,
      });
      updateVideoState(eventId, submission.id, {
        videoAnalysisJobId: started.job_id,
        videoAnalysisStatus: started.status,
      });
    } catch (err) {
      setVideoError(err instanceof Error ? err.message : "Unable to start video analysis.");
      updateVideoState(eventId, submission.id, { videoAnalysisStatus: "failed" });
    }
  }

  return (
    <div className="flex h-full flex-col overflow-hidden">
      {/* Panel header */}
      <div className="flex shrink-0 items-start justify-between gap-3 border-b border-neutral-800 px-4 py-4">
        <div className="min-w-0 space-y-1">
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-white truncate">
              {submission.teamName}
            </p>
            <StatusPill status={run.status} />
          </div>
          <a
            href={submission.repoUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs text-neutral-400 hover:text-violet-400 transition-colors"
          >
            <GitBranch className="h-3 w-3 shrink-0" />
            <span className="truncate">{shortUrl(submission.repoUrl)}</span>
            <ExternalLink className="h-3 w-3 shrink-0 text-neutral-600" />
          </a>
        </div>
        <button
          onClick={onClose}
          className="shrink-0 rounded-lg p-1.5 text-neutral-500 hover:bg-neutral-800 hover:text-white transition-colors"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      {/* Scrollable body */}
      <div className="flex-1 overflow-y-auto">
        <div className="border-b border-neutral-800 px-4 py-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Live Voice Transcript
          </p>
          <div className="flex items-center gap-2">
            {!isRecording ? (
              <button
                type="button"
                onClick={() => void startRecording()}
                className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500"
              >
                Start Recording
              </button>
            ) : (
              <button
                type="button"
                onClick={() => void stopRecording()}
                className="rounded-lg bg-red-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-red-500"
              >
                Stop Recording
              </button>
            )}
            <span className="text-xs text-neutral-500">
              Status: {submission.voiceStatus ?? "idle"}
            </span>
          </div>
          {partialTranscript ? (
            <p className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs text-neutral-300">
              Live: {partialTranscript}
            </p>
          ) : null}
          {submission.voiceTranscript?.full_transcript ? (
            <div className="space-y-2">
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  onClick={() => setShowFullTranscript((prev) => !prev)}
                  className="rounded-md border border-neutral-700 px-2.5 py-1 text-[11px] text-neutral-300 hover:bg-neutral-800"
                >
                  {showFullTranscript ? "Hide Full Transcript" : "Show Full Transcript"}
                </button>
                <button
                  type="button"
                  onClick={() => void copyTranscript()}
                  className="rounded-md border border-neutral-700 px-2.5 py-1 text-[11px] text-neutral-300 hover:bg-neutral-800"
                >
                  {copied ? "Copied" : "Copy Transcript"}
                </button>
              </div>
              {showFullTranscript ? (
                <p className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2 text-xs text-neutral-300 max-h-44 overflow-y-auto">
                  {submission.voiceTranscript.full_transcript}
                </p>
              ) : null}
            </div>
          ) : null}
          {recordError ? (
            <p className="text-xs text-red-400">{recordError}</p>
          ) : null}
        </div>
        <div className="border-b border-neutral-800 px-4 py-4 space-y-3">
          <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
            Demo Video Analysis
          </p>
          <p className="text-xs text-neutral-400">
            Uploaded file: {submission.videoFileName ?? "Not submitted"}
          </p>
          <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
            <input
              type="text"
              value={videoAssignmentTitle}
              onChange={(event) => setVideoAssignmentTitle(event.target.value)}
              placeholder="Assignment title"
              className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-2.5 py-1.5 text-xs text-neutral-200"
            />
            <button
              type="button"
              onClick={() => void startVideoAnalysis()}
              disabled={!hasVideoArtifact || videoStatus === "pending" || videoStatus === "running"}
              className="rounded-lg bg-violet-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-violet-500 disabled:opacity-50"
            >
              {videoStatus === "pending" || videoStatus === "running"
                ? "Analyzing..."
                : submission.videoAnalysisResult
                  ? "Re-run Video Analysis"
                  : "Start Video Analysis"}
            </button>
          </div>
          <textarea
            value={videoFeaturesText}
            onChange={(event) => setVideoFeaturesText(event.target.value)}
            rows={3}
            placeholder="Required features (one per line)"
            className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-2.5 py-1.5 text-xs text-neutral-200"
          />
          <p className="text-xs text-neutral-500">
            Status: {videoStatus}
            {submission.videoAnalysisJobId ? ` • Job: ${submission.videoAnalysisJobId}` : ""}
          </p>
          {videoError ? <p className="text-xs text-red-400">{videoError}</p> : null}
          {submission.videoAnalysisResult?.status === "completed" &&
          (submission.videoAnalysisResult.parsed || submission.videoAnalysisResult.raw_output) ? (
            <div className="space-y-3">
              {submission.videoAnalysisResult.parsed?.summary ? (
                <div className="rounded-md border border-neutral-800 bg-neutral-900 px-3 py-2">
                  <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    Video summary
                  </p>
                  <p className="mt-1 text-xs text-neutral-300 leading-relaxed">
                    {submission.videoAnalysisResult.parsed.summary}
                  </p>
                </div>
              ) : null}

              {submission.videoAnalysisResult.parsed?.limitations ? (
                <div className="rounded-md border border-neutral-800 bg-neutral-900/80 px-3 py-2 text-xs text-neutral-400">
                  <span className="font-semibold text-neutral-300">Limitations: </span>
                  {submission.videoAnalysisResult.parsed.limitations}
                </div>
              ) : null}

              {submission.videoAnalysisResult.parsed?.rubric &&
              submission.videoAnalysisResult.parsed.rubric.length > 0 ? (
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    Rubric
                  </p>
                  <div className="max-h-56 overflow-auto rounded-md border border-neutral-800">
                    <table className="w-full min-w-[520px] border-collapse text-left text-[11px]">
                      <thead>
                        <tr className="border-b border-neutral-800 bg-neutral-900/90">
                          <th className="px-2 py-1.5 font-medium text-neutral-400">ID</th>
                          <th className="px-2 py-1.5 font-medium text-neutral-400">Score</th>
                          <th className="px-2 py-1.5 font-medium text-neutral-400">Evidence</th>
                          <th className="px-2 py-1.5 font-medium text-neutral-400">Time</th>
                        </tr>
                      </thead>
                      <tbody>
                        {submission.videoAnalysisResult.parsed.rubric.map((row, i) => (
                          <tr key={row.id ?? i} className="border-b border-neutral-800/80 last:border-0">
                            <td className="px-2 py-1.5 font-mono text-violet-300">{row.id}</td>
                            <td className="px-2 py-1.5 text-neutral-200">{row.score}</td>
                            <td className="max-w-[240px] px-2 py-1.5 text-neutral-400">
                              {row.evidence}
                            </td>
                            <td className="px-2 py-1.5 text-neutral-500">{row.timestamps}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : null}

              {submission.videoAnalysisResult.parsed?.feature_coverage &&
              submission.videoAnalysisResult.parsed.feature_coverage.length > 0 ? (
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    Feature coverage
                  </p>
                  <ul className="max-h-40 space-y-1.5 overflow-y-auto">
                    {submission.videoAnalysisResult.parsed.feature_coverage.map((f, i) => (
                      <li
                        key={f.feature ?? i}
                        className="rounded-md border border-neutral-800 bg-neutral-900 px-2.5 py-1.5 text-[11px]"
                      >
                        <div className="flex flex-wrap items-baseline gap-2">
                          <span className="font-medium text-neutral-200">{f.feature}</span>
                          {f.status ? (
                            <span className="rounded-full border border-neutral-700 px-1.5 py-0 text-[10px] text-neutral-400">
                              {f.status}
                            </span>
                          ) : null}
                        </div>
                        {f.evidence ? (
                          <p className="mt-0.5 text-[10px] text-neutral-500">{f.evidence}</p>
                        ) : null}
                      </li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {submission.videoAnalysisResult.parsed?.gaps_and_risks &&
              submission.videoAnalysisResult.parsed.gaps_and_risks.length > 0 ? (
                <div>
                  <p className="mb-1.5 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    Gaps and risks
                  </p>
                  <ul className="list-inside list-disc space-y-0.5 text-[11px] text-neutral-400">
                    {submission.videoAnalysisResult.parsed.gaps_and_risks.map((g, i) => (
                      <li key={i}>{g}</li>
                    ))}
                  </ul>
                </div>
              ) : null}

              {!submission.videoAnalysisResult.parsed && submission.videoAnalysisResult.raw_output ? (
                <div>
                  <p className="mb-1 text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    Raw output (unparsed)
                  </p>
                  <pre className="max-h-48 overflow-auto rounded-md border border-neutral-800 bg-neutral-950 p-2 text-[10px] whitespace-pre-wrap text-neutral-300">
                    {submission.videoAnalysisResult.raw_output}
                  </pre>
                </div>
              ) : null}

              {submission.videoAnalysisResult.raw_output ? (
                <details className="text-[11px] text-neutral-500">
                  <summary className="cursor-pointer text-neutral-400 hover:text-neutral-200">
                    Raw model output
                  </summary>
                  <pre className="mt-1 max-h-36 overflow-auto rounded-md border border-neutral-800 bg-neutral-950 p-2 text-[10px] whitespace-pre-wrap text-neutral-400">
                    {submission.videoAnalysisResult.raw_output}
                  </pre>
                </details>
              ) : null}
            </div>
          ) : null}
        </div>
        <AnimatePresence mode="wait">

          {/* Queued */}
          {run.status === "queued" && (
            <motion.div
              key="queued"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="flex flex-col items-center justify-center gap-3 py-16 text-center px-6"
            >
              <Clock className="h-8 w-8 text-neutral-500" />
              <p className="text-sm font-medium text-neutral-300">Queued for analysis</p>
              <p className="text-xs text-neutral-600">
                The run will start shortly. This panel will update automatically.
              </p>
            </motion.div>
          )}

          {/* Running */}
          {run.status === "running" && (
            <motion.div
              key="running"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="space-y-3 p-4"
            >
              {/* Current activity bar */}
              <div className="rounded-lg border border-violet-500/20 bg-violet-500/8 px-3 py-2.5 space-y-1.5">
                <div className="flex items-center gap-2 text-xs font-medium text-violet-300">
                  <Loader2 className="h-3 w-3 animate-spin shrink-0" />
                  <span className="truncate">
                    {run.current_activity ?? "Analyzing…"}
                  </span>
                </div>
                <div className="flex items-center gap-2">
                  <div className="flex-1 h-1 rounded-full bg-neutral-800 overflow-hidden">
                    <motion.div
                      className="h-full bg-violet-500 rounded-full"
                      initial={{ width: 0 }}
                      animate={{
                        width: totalPhases > 0
                          ? `${(donePhases / totalPhases) * 100}%`
                          : "0%",
                      }}
                      transition={{ duration: 0.5, ease: "easeOut" }}
                    />
                  </div>
                  <span className="text-[11px] text-neutral-500 shrink-0">
                    {donePhases}/{totalPhases}
                  </span>
                </div>
              </div>

              {/* Agent plan */}
              <AgentPlan tasks={planTasks} />
            </motion.div>
          )}

          {/* Completed */}
          {run.status === "completed" && (
            <motion.div
              key="completed"
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0 }}
              className="p-4 space-y-4"
            >
              {run.markdown_report_content ? (
                <div className="rounded-lg border border-neutral-800 bg-neutral-900 px-3 py-3">
                  <p className="text-xs font-semibold uppercase tracking-wider text-neutral-500">
                    Summary
                  </p>
                  <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-neutral-300">
                    {run.markdown_report_content}
                  </p>
                </div>
              ) : null}
              {run.result?.repository_analysis ? (
                <ResultsPanel
                  analysis={run.result.repository_analysis}
                  planTasks={planTasks}
                  hideHeader
                />
              ) : null}
            </motion.div>
          )}

          {/* Failed */}
          {run.status === "failed" && (
            <motion.div
              key="failed"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="m-4 rounded-lg border border-red-500/20 bg-red-500/8 p-4 space-y-2"
            >
              <div className="flex items-center gap-2">
                <XCircle className="h-4 w-4 text-red-400 shrink-0" />
                <p className="text-sm font-semibold text-red-300">Analysis failed</p>
              </div>
              <p className="text-xs text-red-400/80 leading-relaxed">
                {run.error ?? "The analysis could not complete. Check the repository URL and try again."}
              </p>
              {planTasks.length > 0 && (
                <div className="pt-2">
                  <p className="text-xs font-semibold text-neutral-500 uppercase tracking-wider mb-2">
                    Progress at failure
                  </p>
                  <AgentPlan tasks={planTasks} />
                </div>
              )}
            </motion.div>
          )}

        </AnimatePresence>
      </div>
    </div>
  );
}

function float32ToInt16(float32Array: Float32Array): Int16Array {
  const out = new Int16Array(float32Array.length);
  for (let i = 0; i < float32Array.length; i += 1) {
    const sample = Math.max(-1, Math.min(1, float32Array[i]));
    out[i] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return out;
}

function toBase64(buffer: ArrayBufferLike): string {
  const bytes = new Uint8Array(buffer);
  let binary = "";
  for (let i = 0; i < bytes.byteLength; i += 1) {
    binary += String.fromCharCode(bytes[i]);
  }
  return window.btoa(binary);
}

function StatusPill({ status }: { status: string }) {
  const config: Record<string, { label: string; className: string }> = {
    queued:    { label: "Queued",    className: "bg-neutral-800 text-neutral-400" },
    running:   { label: "Analyzing", className: "bg-violet-500/15 text-violet-300" },
    completed: { label: "Complete",  className: "bg-emerald-500/15 text-emerald-300" },
    failed:    { label: "Failed",    className: "bg-red-500/15 text-red-300" },
  };
  const c = config[status] ?? config.queued;
  return (
    <span className={cn("rounded-full px-2 py-0.5 text-[11px] font-medium shrink-0", c.className)}>
      {c.label}
    </span>
  );
}

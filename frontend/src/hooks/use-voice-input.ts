"use client";

import { useCallback, useEffect, useRef, useState } from "react";

/**
 * Voice input via the browser's Web Speech API (SpeechRecognition).
 *
 * Why this over a server-side Whisper round-trip:
 *   - Zero backend latency (results arrive while you speak).
 *   - No audio file leaves the browser → privacy-friendly.
 *   - No extra Django endpoint to maintain for what's essentially a UX hint.
 *
 * Caveats:
 *   - Chromium-based browsers (Chrome, Edge, Opera, Brave) support it
 *     under `webkitSpeechRecognition`. Firefox and Safari ≤ 14 do not.
 *   - When `supported === false`, callers should hide the mic button
 *     rather than throw.
 *
 * Behaviour:
 *   - `start()` opens the mic and begins continuous interim transcription
 *     so the input box updates live as the user speaks.
 *   - `stop()` finalises the current utterance and triggers `onFinal` with
 *     the full transcript.
 *   - If the user stays silent for ~1 s after speaking, the browser may
 *     auto-end the recognition session; we propagate that as a normal
 *     `onFinal` and reset state.
 */

// The DOM lib doesn't include SpeechRecognition types in all TS versions, so
// we define the minimum surface we actually touch.
interface SRResult {
  isFinal: boolean;
  0: { transcript: string };
}
interface SREvent extends Event {
  resultIndex: number;
  results: ArrayLike<SRResult>;
}
interface SRErrorEvent extends Event {
  error: string;
}
interface SRInstance extends EventTarget {
  lang: string;
  continuous: boolean;
  interimResults: boolean;
  maxAlternatives: number;
  start(): void;
  stop(): void;
  abort(): void;
  onresult: ((e: SREvent) => void) | null;
  onerror: ((e: SRErrorEvent) => void) | null;
  onend: ((e: Event) => void) | null;
}
type SRConstructor = new () => SRInstance;

function getSRConstructor(): SRConstructor | null {
  if (typeof window === "undefined") return null;
  const w = window as unknown as {
    SpeechRecognition?: SRConstructor;
    webkitSpeechRecognition?: SRConstructor;
  };
  return w.SpeechRecognition || w.webkitSpeechRecognition || null;
}

export interface VoiceInputOptions {
  /** BCP-47 language tag. Defaults to the browser's UI language. */
  lang?: string;
  /** Fired on every interim partial — useful for live-updating the input box. */
  onInterim?: (transcript: string) => void;
  /** Fired exactly once when the user stops speaking or when `stop()` is called. */
  onFinal?: (transcript: string) => void;
  /** Fired on permission denial, no-speech, audio-capture errors, etc. */
  onError?: (message: string) => void;
}

export function useVoiceInput(options: VoiceInputOptions = {}) {
  const { lang, onInterim, onFinal, onError } = options;

  const [supported, setSupported] = useState(false);
  const [recording, setRecording] = useState(false);

  const recognitionRef = useRef<SRInstance | null>(null);
  const transcriptRef = useRef<string>("");
  // True when the user tapped the mic to stop on purpose. We use this in
  // `onend` to decide whether to fire `onFinal` (user stopped) or silently
  // restart the recogniser (browser ended the session early during a pause).
  const userStoppedRef = useRef<boolean>(false);

  // Detect support once on mount.
  useEffect(() => {
    setSupported(getSRConstructor() !== null);
  }, []);

  // Clean up if the component unmounts mid-recording.
  useEffect(() => {
    return () => {
      // Tell onend not to auto-restart; abort the session.
      userStoppedRef.current = true;
      try {
        recognitionRef.current?.abort();
      } catch {
        /* swallow — instance may already be gone */
      }
      recognitionRef.current = null;
    };
  }, []);

  const start = useCallback(() => {
    if (recording) return;
    const SR = getSRConstructor();
    if (!SR) {
      onError?.("Voice input is not supported in this browser.");
      return;
    }

    const recognition = new SR();
    recognition.lang = lang || (typeof navigator !== "undefined" ? navigator.language : "en-US");
    // Keep listening across natural pauses. We end the session only when the
    // user taps the mic again (see `stop()`); the browser sometimes still
    // closes the underlying session on its own, in which case `onend` quietly
    // restarts it below so the user's experience is "stays on until I stop".
    recognition.continuous = true;
    recognition.interimResults = true;
    recognition.maxAlternatives = 1;
    transcriptRef.current = "";
    userStoppedRef.current = false;

    recognition.onresult = (event: SREvent) => {
      let interim = "";
      let finalText = transcriptRef.current;
      for (let i = event.resultIndex; i < event.results.length; i++) {
        const res = event.results[i];
        const transcript = res[0].transcript;
        if (res.isFinal) {
          finalText += transcript;
        } else {
          interim += transcript;
        }
      }
      transcriptRef.current = finalText;
      const live = (finalText + interim).trim();
      if (live) onInterim?.(live);
    };

    recognition.onerror = (event: SRErrorEvent) => {
      // "no-speech" fires when the mic was opened but the user hasn't started
      // talking yet. With continuous=true we don't want to bail on this —
      // just let onend restart the session so the user can keep thinking.
      if (event.error === "no-speech") {
        return;
      }
      if (event.error === "aborted") {
        // We called .abort() ourselves (component unmount, etc.) — silent.
        return;
      }
      onError?.(
        event.error === "not-allowed"
          ? "Microphone permission denied. Allow it in your browser settings."
          : `Voice input error: ${event.error}`,
      );
      userStoppedRef.current = true;
      setRecording(false);
    };

    recognition.onend = () => {
      // If the user hasn't tapped stop, the browser ended the session on its
      // own (typical Chrome behaviour after a few seconds of silence). Just
      // restart so the mic feels "always listening" until the user stops.
      if (!userStoppedRef.current) {
        try {
          recognition.start();
          return;
        } catch {
          // start() can throw if the engine is in a weird state; fall through
          // to the normal "session ended" path.
        }
      }
      const finalText = transcriptRef.current.trim();
      setRecording(false);
      if (finalText) onFinal?.(finalText);
    };

    try {
      recognition.start();
      recognitionRef.current = recognition;
      setRecording(true);
    } catch (err) {
      onError?.(err instanceof Error ? err.message : "Could not start voice input.");
      setRecording(false);
    }
  }, [recording, lang, onInterim, onFinal, onError]);

  const stop = useCallback(() => {
    userStoppedRef.current = true;
    try {
      recognitionRef.current?.stop();
    } catch {
      /* recognition may already have ended */
    }
  }, []);

  const toggle = useCallback(() => {
    if (recording) stop();
    else start();
  }, [recording, start, stop]);

  return { supported, recording, start, stop, toggle };
}

/**
 * Strip the wake-word "agent" from a transcript and return the agent command
 * body. Returns null if the transcript doesn't contain the wake-word.
 *
 * Examples:
 *   "agent take me to login"      → "take me to login"
 *   "hey agent open dashboard"    → "open dashboard"
 *   "open the agent monitor page" → "open the monitor page"
 *   "what is the win rate"        → null
 *
 * The check is case-insensitive and tolerant of trailing punctuation/commas
 * that browsers tend to insert ("hey agent, …").
 */
export function extractAgentCommand(transcript: string): string | null {
  const match = transcript.match(/\bagent\b[\s,.:;!?-]*/i);
  if (!match) return null;
  const before = transcript.slice(0, match.index).trim();
  const after = transcript.slice((match.index ?? 0) + match[0].length).trim();
  const body = [before, after].filter(Boolean).join(" ").trim();
  // Empty body ("just say agent") still counts as an agent command,
  // we just have nothing to send. Caller decides what to do.
  return body;
}

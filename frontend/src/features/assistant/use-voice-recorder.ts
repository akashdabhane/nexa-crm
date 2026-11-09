import { useCallback, useEffect, useRef, useState, useSyncExternalStore } from "react";

/** Longest clip we record; the backend rejects much larger uploads anyway. */
export const MAX_RECORDING_SECONDS = 120;

// Opus in WebM (Chrome, Edge, Firefox) or MP4 (Safari). Whisper on the server decodes any of them.
const MIME_TYPES = ["audio/webm;codecs=opus", "audio/webm", "audio/ogg;codecs=opus", "audio/mp4"];

function isSupported() {
  // getUserMedia only exists on secure pages (https or localhost).
  return typeof MediaRecorder !== "undefined" && !!navigator.mediaDevices?.getUserMedia;
}

const noSubscription = () => () => {};

/** A readable message for why the microphone couldn't be opened. */
export function microphoneErrorMessage(error: unknown): string {
  const name = error instanceof DOMException ? error.name : "";
  if (name === "NotAllowedError" || name === "SecurityError")
    return "Microphone access is blocked. Allow it in your browser's site settings, then try again.";
  if (name === "NotFoundError" || name === "OverconstrainedError") return "No microphone was found.";
  if (name === "NotReadableError") return "Your microphone is busy in another app.";
  return "Couldn't start the microphone.";
}

/**
 * Records one voice clip from the microphone. `start()` asks for the mic (the browser prompts the first time),
 * `stop()` resolves with the recording, `cancel()` throws it away. At the time limit `onLimit` is called so the
 * caller can stop and use what was said.
 */
export function useVoiceRecorder({ onLimit }: { onLimit: () => void }) {
  const supported = useSyncExternalStore(noSubscription, isSupported, () => false);
  const [stream, setStream] = useState<MediaStream | null>(null);
  const [seconds, setSeconds] = useState(0);
  const recorderRef = useRef<MediaRecorder | null>(null);
  const startingRef = useRef(false); // waiting on the mic permission prompt
  const chunksRef = useRef<Blob[]>([]);
  const onLimitRef = useRef(onLimit);

  useEffect(() => {
    onLimitRef.current = onLimit;
  });

  const release = useCallback(() => {
    recorderRef.current?.stream.getTracks().forEach((track) => track.stop()); // turns off the browser's mic indicator
    recorderRef.current = null;
    setStream(null);
  }, []);

  const start = useCallback(async () => {
    if (recorderRef.current || startingRef.current) return;
    startingRef.current = true;
    let media: MediaStream;
    try {
      media = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true } });
    } finally {
      startingRef.current = false;
    }
    const mimeType = MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type));
    const recorder = new MediaRecorder(media, mimeType ? { mimeType } : undefined);
    chunksRef.current = [];
    recorder.ondataavailable = (event) => {
      if (event.data.size > 0) chunksRef.current.push(event.data);
    };
    recorder.start();
    recorderRef.current = recorder;
    setSeconds(0);
    setStream(media);
  }, []);

  const stop = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder) return Promise.resolve(null);
    return new Promise<Blob | null>((resolve) => {
      recorder.onstop = () => {
        const audio = new Blob(chunksRef.current, { type: recorder.mimeType });
        resolve(audio.size > 0 ? audio : null);
      };
      recorder.stop();
      release();
    });
  }, [release]);

  const cancel = useCallback(() => {
    const recorder = recorderRef.current;
    if (!recorder) return;
    recorder.onstop = null;
    recorder.stop();
    release();
  }, [release]);

  const recording = stream !== null;

  // Elapsed time, and the time limit.
  useEffect(() => {
    if (!recording) return;
    const startedAt = Date.now();
    const timer = window.setInterval(() => {
      const elapsed = Math.floor((Date.now() - startedAt) / 1000);
      setSeconds(elapsed);
      if (elapsed >= MAX_RECORDING_SECONDS) onLimitRef.current();
    }, 250);
    return () => window.clearInterval(timer);
  }, [recording]);

  // Never leave the microphone on after the panel unmounts.
  useEffect(() => () => recorderRef.current?.stream.getTracks().forEach((track) => track.stop()), []);

  return { supported, recording, stream, seconds, start, stop, cancel };
}

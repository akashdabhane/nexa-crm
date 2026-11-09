import { useEffect, useState } from "react";

// Speech energy sits below ~4 kHz: with a 64-point FFT at 48 kHz each bin is 750 Hz wide.
const BINS = [1, 2, 3, 4, 5];

/** Live equalizer bars for the microphone, so the user can see they're being heard. */
export function VoiceLevel({ stream }: { stream: MediaStream }) {
  const [levels, setLevels] = useState<number[]>(() => BINS.map(() => 0));

  useEffect(() => {
    const context = new AudioContext();
    const analyser = context.createAnalyser();
    analyser.fftSize = 64;
    context.createMediaStreamSource(stream).connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);
    let frame = requestAnimationFrame(function tick() {
      analyser.getByteFrequencyData(data);
      setLevels(BINS.map((bin) => data[bin] / 255));
      frame = requestAnimationFrame(tick);
    });
    return () => {
      cancelAnimationFrame(frame);
      void context.close();
    };
  }, [stream]);

  return (
    <span aria-hidden className="flex h-4 items-center gap-0.5">
      {levels.map((level, index) => (
        <span
          key={index}
          className="w-[3px] rounded-full bg-destructive transition-[height] duration-75"
          style={{ height: `${Math.max(20, level * 100)}%` }}
        />
      ))}
    </span>
  );
}

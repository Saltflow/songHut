import { useState, useRef, useCallback } from 'react';

interface RecorderState {
  isRecording: boolean;
  durationMs: number;
  audioBlob: Blob | null;
  error: string | null;
}

export function useAudioRecorder() {
  const [state, setState] = useState<RecorderState>({
    isRecording: false,
    durationMs: 0,
    audioBlob: null,
    error: null,
  });

  const mediaRecorderRef = useRef<MediaRecorder | null>(null);
  const chunksRef = useRef<Blob[]>([]);
  const timerRef = useRef<number>(0);

  const startRecording = useCallback(async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mimeType = MediaRecorder.isTypeSupported('audio/webm;codecs=opus')
        ? 'audio/webm;codecs=opus'
        : 'audio/webm';

      chunksRef.current = [];
      const recorder = new MediaRecorder(stream, { mimeType });

      recorder.ondataavailable = (e) => {
        if (e.data.size > 0) chunksRef.current.push(e.data);
      };

      recorder.onstop = () => {
        const blob = new Blob(chunksRef.current, { type: recorder.mimeType });
        stream.getTracks().forEach(t => t.stop());
        setState(s => ({ ...s, isRecording: false, audioBlob: blob }));
      };

      recorder.start(200);
      mediaRecorderRef.current = recorder;

      const startTime = Date.now();
      timerRef.current = window.setInterval(() => {
        setState(s => ({ ...s, durationMs: Date.now() - startTime }));
      }, 100);

      setState(s => ({ ...s, isRecording: true, error: null }));
    } catch (e: any) {
      setState(s => ({ ...s, error: `无法访问麦克风: ${e.message}` }));
    }
  }, []);

  const stopRecording = useCallback(() => {
    clearInterval(timerRef.current);
    if (mediaRecorderRef.current && mediaRecorderRef.current.state !== 'inactive') {
      mediaRecorderRef.current.stop();
    }
  }, []);

  const reset = useCallback(() => {
    setState({ isRecording: false, durationMs: 0, audioBlob: null, error: null });
  }, []);

  function formatTime(ms: number): string {
    const s = Math.floor(ms / 1000);
    const m = Math.floor(s / 60);
    return `${m.toString().padStart(2, '0')}:${(s % 60).toString().padStart(2, '0')}`;
  }

  return { ...state, formatTime, startRecording, stopRecording, reset };
}

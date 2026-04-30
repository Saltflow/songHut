import React, { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useAudioRecorder } from '../../hooks/useAudioRecorder';
import { filesApi } from '../../api/files';
import { useProjectStore } from '../../stores/project.store';

export default function RecordPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const recorder = useAudioRecorder();
  const [uploading, setUploading] = useState(false);
  const fetchDetail = useProjectStore(s => s.fetchDetail);

  async function handleSave() {
    if (!recorder.audioBlob || !projectId) return;
    setUploading(true);
    const file = new File([recorder.audioBlob], `recording_${Date.now()}.webm`, {
      type: recorder.audioBlob.type,
    });
    const result = await filesApi.upload(projectId, file, 'recording');
    if (result.ok) {
      fetchDetail(projectId);
      navigate(`/projects/${projectId}`);
    }
    setUploading(false);
  }

  const barCount = 40;
  const bars = Array.from({ length: barCount }, (_, i) => {
    const h = recorder.isRecording
      ? 20 + Math.abs(Math.sin((Date.now() / 200) + i * 0.5)) * 60
      : 10;
    return (
      <div
        key={i}
        className="bg-indigo-500 rounded-sm transition-all duration-100"
        style={{ width: 3, height: h, opacity: recorder.isRecording ? 0.8 : 0.3 }}
      />
    );
  });

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center gap-4">
        <button onClick={() => navigate(-1)} className="text-gray-500 hover:text-gray-700">← 返回</button>
        <h1 className="text-lg font-bold text-gray-900">录音</h1>
      </header>

      <main className="max-w-lg mx-auto px-6 py-12 flex flex-col items-center">
        {recorder.error && (
          <div className="text-red-500 text-sm bg-red-50 px-4 py-3 rounded-lg mb-6 w-full text-center">{recorder.error}</div>
        )}

        <div className="text-4xl font-mono text-gray-700 mb-6">
          {recorder.formatTime(recorder.durationMs)}
        </div>

        <div className="flex items-end justify-center gap-1 h-20 mb-8">
          {bars}
        </div>

        <div className="flex gap-4">
          {!recorder.isRecording && !recorder.audioBlob && (
            <button
              onClick={recorder.startRecording}
              className="w-20 h-20 rounded-full bg-red-500 hover:bg-red-600 text-white text-2xl flex items-center justify-center shadow-lg transition"
            >
              ●
            </button>
          )}

          {recorder.isRecording && (
            <button
              onClick={recorder.stopRecording}
              className="w-20 h-20 rounded-full bg-gray-800 hover:bg-gray-900 text-white flex items-center justify-center shadow-lg transition"
            >
              <div className="w-6 h-6 bg-white rounded-sm" />
            </button>
          )}

          {recorder.audioBlob && (
            <div className="flex flex-col gap-3">
              <button
                onClick={() => {
                  const url = URL.createObjectURL(recorder.audioBlob!);
                  const a = new Audio(url);
                  a.play();
                }}
                className="bg-indigo-100 text-indigo-700 px-6 py-3 rounded-lg font-medium hover:bg-indigo-200 transition"
              >
                ▶ 试听
              </button>
              <button
                onClick={handleSave}
                disabled={uploading}
                className="bg-indigo-600 text-white px-6 py-3 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
              >
                {uploading ? '保存中...' : '保存到项目'}
              </button>
              <button
                onClick={recorder.reset}
                className="text-gray-500 text-sm hover:text-gray-700"
              >
                重新录制
              </button>
            </div>
          )}
        </div>
      </main>
    </div>
  );
}

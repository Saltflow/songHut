import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { useProjects } from '../../hooks/useProjects';
import { filesApi } from '../../api/files';

export default function ProjectPage() {
  const { projectId } = useParams<{ projectId: string }>();
  const navigate = useNavigate();
  const { current, isLoading, fetchDetail, remove } = useProjects();
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    if (projectId) fetchDetail(projectId);
  }, [projectId]);

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file || !projectId) return;
    setUploading(true);
    const result = await filesApi.upload(projectId, file, 'recording');
    if (result.ok && projectId) fetchDetail(projectId);
    setUploading(false);
  }

  async function handleDelete() {
    if (!projectId || !confirm('确定删除这个项目吗？所有文件将被永久删除。')) return;
    const ok = await remove(projectId);
    if (ok) navigate('/');
  }

  const categoryLabel: Record<string, string> = {
    recording: '录音', melody: '旋律', accompaniment: '伴奏',
    vocal: '演唱', lyrics: '歌词', score: '乐谱', image: '图片', other: '其他',
  };

  if (isLoading) return <div className="p-8 text-gray-400">加载中...</div>;
  if (!current) return <div className="p-8 text-gray-400">项目不存在</div>;

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-4">
          <button onClick={() => navigate('/')} className="text-gray-500 hover:text-gray-700">← 返回</button>
          <h1 className="text-lg font-bold text-gray-900">{current.name}</h1>
        </div>
        <button onClick={handleDelete} className="text-sm text-red-500 hover:text-red-700">删除项目</button>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
          <p className="text-gray-600">{current.description || '暂无描述'}</p>
          <p className="text-sm text-gray-400 mt-2">{current.member_count} 位成员</p>
        </div>

        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-gray-800">文件</h2>
          <label className={`bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium cursor-pointer hover:bg-indigo-700 transition ${uploading ? 'opacity-50' : ''}`}>
            {uploading ? '上传中...' : '+ 上传文件'}
            <input type="file" onChange={handleUpload} accept="audio/*" className="hidden" disabled={uploading} />
          </label>
        </div>

        {current.files.length === 0 ? (
          <div className="text-center py-16 text-gray-400">
            <p className="text-3xl mb-2">📁</p>
            <p>还没有文件，上传你的第一个录音吧</p>
          </div>
        ) : (
          <div className="space-y-2">
            {current.files.map(file => (
              <div key={file.id} className="bg-white rounded-lg shadow-sm p-4 flex items-center justify-between">
                <div>
                  <p className="font-medium text-gray-900">{file.filename}</p>
                  <p className="text-xs text-gray-400">
                    {categoryLabel[file.category] || file.category}
                    {' · '}{(file.file_size / 1024).toFixed(1)} KB
                    {' · '}{new Date(file.created_at).toLocaleDateString('zh-CN')}
                  </p>
                </div>
                <button
                  onClick={() => filesApi.download(file.id)}
                  className="text-indigo-600 text-sm hover:underline"
                >下载</button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

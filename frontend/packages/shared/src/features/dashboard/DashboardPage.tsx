import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuthStore } from '../../stores/auth.store';
import { useProjectStore } from '../../stores/project.store';

export default function DashboardPage() {
  const navigate = useNavigate();
  const { user, logout } = useAuthStore();
  const { projects, isLoading, fetchProjects, create } = useProjectStore();
  const [showNew, setShowNew] = useState(false);
  const [name, setName] = useState('');

  useEffect(() => { fetchProjects(); }, []);

  async function handleCreate() {
    if (!name.trim()) return;
    const project = await create({ name });
    if (project) {
      setShowNew(false);
      setName('');
      navigate(`/projects/${project.id}`);
    }
  }

  return (
    <div className="min-h-screen bg-gray-50">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <h1 className="text-xl font-bold">🎵 SongHut</h1>
        <div className="flex items-center gap-4">
          <span className="text-gray-600 text-sm">{user?.nickname || user?.phone}</span>
          <button onClick={logout} className="text-sm text-gray-500 hover:text-red-500">登出</button>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-6 py-8">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-semibold text-gray-800">我的项目</h2>
          <button
            onClick={() => setShowNew(true)}
            className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700 transition"
          >
            + 新建项目
          </button>
        </div>

        {showNew && (
          <div className="bg-white rounded-xl shadow-sm p-6 mb-6">
            <h3 className="font-medium mb-3">创建新项目</h3>
            <div className="flex gap-3">
              <input
                type="text"
                value={name}
                onChange={e => setName(e.target.value)}
                onKeyDown={e => e.key === 'Enter' && handleCreate()}
                placeholder="项目名称"
                autoFocus
                className="flex-1 px-3 py-2 border border-gray-300 rounded-lg outline-none focus:ring-2 focus:ring-indigo-500"
              />
              <button onClick={handleCreate} className="bg-indigo-600 text-white px-4 py-2 rounded-lg text-sm font-medium hover:bg-indigo-700">
                创建
              </button>
              <button onClick={() => setShowNew(false)} className="bg-gray-200 text-gray-700 px-4 py-2 rounded-lg text-sm">
                取消
              </button>
            </div>
          </div>
        )}

        {isLoading ? (
          <p className="text-gray-400">加载中...</p>
        ) : projects.length === 0 ? (
          <div className="text-center py-20 text-gray-400">
            <p className="text-4xl mb-4">🎶</p>
            <p>还没有项目，点击上方按钮创建第一个</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(project => (
              <div
                key={project.id}
                onClick={() => navigate(`/projects/${project.id}`)}
                className="bg-white rounded-xl shadow-sm p-5 cursor-pointer hover:shadow-md transition border border-transparent hover:border-indigo-200"
              >
                <div className="w-12 h-12 bg-indigo-100 rounded-lg flex items-center justify-center text-2xl mb-3">
                  🎹
                </div>
                <h3 className="font-semibold text-gray-900 truncate">{project.name}</h3>
                <p className="text-sm text-gray-500 mt-1 truncate">{project.description || '暂无描述'}</p>
                <p className="text-xs text-gray-400 mt-2">
                  {project.member_count} 成员 · {new Date(project.created_at).toLocaleDateString('zh-CN')}
                </p>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}

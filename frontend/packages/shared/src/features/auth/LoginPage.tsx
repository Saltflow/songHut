import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';

export default function LoginPage() {
  const navigate = useNavigate();
  const { login, isLoading, error, clearError } = useAuth();
  const [phone, setPhone] = useState('');
  const [password, setPassword] = useState('');

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    clearError();
    const ok = await login(phone, password);
    if (ok) navigate('/');
  }

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="text-center mb-8">
          <h1 className="text-4xl mb-2">🎵</h1>
          <h2 className="text-2xl font-bold text-gray-900">SongHut</h2>
          <p className="text-gray-500 mt-1">哼唱转旋律 · AI 音乐创作</p>
        </div>

        <form onSubmit={handleSubmit} className="bg-white rounded-xl shadow-sm p-6 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">手机号</label>
            <input
              type="text" value={phone} onChange={e => setPhone(e.target.value)}
              placeholder="13800138000" required
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">密码</label>
            <input
              type="password" value={password} onChange={e => setPassword(e.target.value)}
              placeholder="至少 8 位" required minLength={8}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-transparent outline-none"
            />
          </div>

          {error && (
            <div className="text-red-500 text-sm bg-red-50 px-3 py-2 rounded">{error}</div>
          )}

          <button
            type="submit" disabled={isLoading}
            className="w-full bg-indigo-600 text-white py-2 rounded-lg font-medium hover:bg-indigo-700 disabled:opacity-50 transition"
          >
            {isLoading ? '登录中...' : '登录'}
          </button>

          <p className="text-center text-sm text-gray-500">
            没有账号？{' '}
            <Link to="/register" className="text-indigo-600 hover:underline">注册</Link>
          </p>
        </form>
      </div>
    </div>
  );
}

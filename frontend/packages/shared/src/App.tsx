import React, { Suspense, lazy } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthGuard } from './features/auth/AuthGuard';

const LoginPage = lazy(() => import('./features/auth/LoginPage'));
const RegisterPage = lazy(() => import('./features/auth/RegisterPage'));
const DashboardPage = lazy(() => import('./features/dashboard/DashboardPage'));
const ProjectPage = lazy(() => import('./features/project/ProjectPage'));
const RecordPage = lazy(() => import('./features/recording/RecordPage'));

function Loading() {
  return <div className="flex items-center justify-center min-h-screen text-gray-400">Loading...</div>;
}

export function App() {
  return (
    <BrowserRouter>
      <Suspense fallback={<Loading />}>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route path="/register" element={<RegisterPage />} />
          <Route path="/" element={<AuthGuard><DashboardPage /></AuthGuard>} />
          <Route path="/projects/:projectId" element={<AuthGuard><ProjectPage /></AuthGuard>} />
          <Route path="/projects/:projectId/record" element={<AuthGuard><RecordPage /></AuthGuard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </Suspense>
    </BrowserRouter>
  );
}

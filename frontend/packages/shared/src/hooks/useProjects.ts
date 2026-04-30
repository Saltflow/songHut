import { useCallback, useEffect } from 'react';
import { useProjectStore } from '../stores/project.store';

export function useProjects() {
  const projects = useProjectStore(s => s.projects);
  const current = useProjectStore(s => s.current);
  const isLoading = useProjectStore(s => s.isLoading);
  const error = useProjectStore(s => s.error);

  const fetchProjects = useCallback(() => useProjectStore.getState().fetchProjects(), []);
  const fetchDetail = useCallback((id: string) => useProjectStore.getState().fetchDetail(id), []);
  const create = useCallback(
    (data: { name: string; description?: string }) => useProjectStore.getState().create(data),
    [],
  );
  const update = useCallback(
    (id: string, data: { name?: string; description?: string }) => useProjectStore.getState().update(id, data),
    [],
  );
  const remove = useCallback((id: string) => useProjectStore.getState().delete(id), []);
  const clearError = useCallback(() => useProjectStore.getState().clearError(), []);

  return {
    projects, current, isLoading, error,
    fetchProjects, fetchDetail, create, update, remove, clearError,
  };
}

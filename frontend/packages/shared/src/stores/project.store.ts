import { create } from 'zustand';
import { projectsApi } from '../api/projects';
import { ProjectDto, ProjectDetailDto } from '../api/types';

interface ProjectState {
  projects: ProjectDto[];
  current: ProjectDetailDto | null;
  isLoading: boolean;
  error: string | null;

  fetchProjects: () => Promise<void>;
  fetchDetail: (id: string) => Promise<void>;
  create: (data: { name: string; description?: string }) => Promise<ProjectDto | null>;
  update: (id: string, data: { name?: string; description?: string }) => Promise<boolean>;
  delete: (id: string) => Promise<boolean>;
  clearError: () => void;
}

export const useProjectStore = create<ProjectState>()((set) => ({
  projects: [],
  current: null,
  isLoading: false,
  error: null,

  fetchProjects: async () => {
    set({ isLoading: true });
    const result = await projectsApi.list();
    if (result.ok) {
      set({ projects: result.data.items, isLoading: false });
    } else {
      set({ isLoading: false, error: result.error.message });
    }
  },

  fetchDetail: async (id) => {
    set({ isLoading: true });
    const result = await projectsApi.getDetail(id);
    if (result.ok) {
      set({ current: result.data, isLoading: false });
    } else {
      set({ isLoading: false, error: result.error.message });
    }
  },

  create: async (data) => {
    set({ isLoading: true, error: null });
    const result = await projectsApi.create(data);
    if (result.ok) {
      set(s => ({ projects: [result.data, ...s.projects], isLoading: false }));
      return result.data;
    }
    set({ isLoading: false, error: result.error.message });
    return null;
  },

  update: async (id, data) => {
    const result = await projectsApi.update(id, data);
    if (result.ok) {
      set(s => ({
        projects: s.projects.map(p => p.id === id ? { ...p, ...result.data } : p),
        current: s.current?.id === id ? { ...s.current, ...result.data } : s.current,
      }));
      return true;
    }
    set({ error: result.error.message });
    return false;
  },

  delete: async (id) => {
    const result = await projectsApi.delete(id);
    if (result.ok) {
      set(s => ({
        projects: s.projects.filter(p => p.id !== id),
        current: s.current?.id === id ? null : s.current,
      }));
      return true;
    }
    return false;
  },

  clearError: () => set({ error: null }),
}));

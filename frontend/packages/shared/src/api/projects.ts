import { apiClient } from './client';
import { ProjectDto, ProjectDetailDto, PageResponse, ApiResult } from './types';

export const projectsApi = {
  list: (page = 1, pageSize = 50): Promise<ApiResult<PageResponse<ProjectDto>>> =>
    apiClient.get('/projects/', { params: { page, page_size: pageSize } }).then(r => r.data),

  create: (data: { name: string; description?: string; is_public?: boolean }): Promise<ApiResult<ProjectDto>> =>
    apiClient.post('/projects/', data).then(r => r.data),

  getDetail: (id: string): Promise<ApiResult<ProjectDetailDto>> =>
    apiClient.get(`/projects/${id}`).then(r => r.data),

  update: (id: string, data: { name?: string; description?: string; is_public?: boolean }): Promise<ApiResult<ProjectDto>> =>
    apiClient.patch(`/projects/${id}`, data).then(r => r.data),

  delete: (id: string): Promise<ApiResult<null>> =>
    apiClient.delete(`/projects/${id}`).then(r => r.data),
};

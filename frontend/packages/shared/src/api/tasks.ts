import { apiClient } from './client';
import { TaskDto, PageResponse, ApiResult } from './types';

export const tasksApi = {
  createMelody: (data: { project_id: string; source_file_id: string; params?: Record<string, unknown> }): Promise<ApiResult<TaskDto>> =>
    apiClient.post('/tasks/melody', data).then(r => r.data),

  get: (taskId: string): Promise<ApiResult<TaskDto>> =>
    apiClient.get(`/tasks/${taskId}`).then(r => r.data),

  list: (page = 1, pageSize = 20): Promise<ApiResult<PageResponse<TaskDto>>> =>
    apiClient.get('/tasks/', { params: { page, page_size: pageSize } }).then(r => r.data),

  cancel: (taskId: string): Promise<ApiResult<TaskDto>> =>
    apiClient.post(`/tasks/${taskId}/cancel`).then(r => r.data),
};

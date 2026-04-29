import { apiClient } from './client';
import { FileDto, FileCategory, ApiResult } from './types';

export const filesApi = {
  get: (fileId: string): Promise<ApiResult<FileDto>> =>
    apiClient.get(`/files/${fileId}`).then(r => r.data),

  download: (fileId: string): Promise<Blob> =>
    apiClient.get(`/files/${fileId}/download`, { responseType: 'blob' }).then(r => r.data),

  delete: (fileId: string): Promise<ApiResult<null>> =>
    apiClient.delete(`/files/${fileId}`).then(r => r.data),

  upload: (
    projectId: string,
    file: File,
    category: FileCategory,
    onProgress?: (percent: number) => void,
  ): Promise<ApiResult<FileDto>> => {
    const form = new FormData();
    form.append('file', file);
    form.append('category', category);
    return apiClient.post(`/projects/${projectId}/files`, form, {
      headers: { 'Content-Type': 'multipart/form-data' },
      onUploadProgress: onProgress ? (e) => onProgress(Math.round((e.loaded * 100) / (e.total ?? 1))) : undefined,
    }).then(r => r.data);
  },
};

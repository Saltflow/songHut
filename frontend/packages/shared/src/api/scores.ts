import { apiClient } from './client';
import { ScoreDto, ApiResult } from './types';

export const scoresApi = {
  get: (scoreId: string): Promise<ApiResult<ScoreDto>> =>
    apiClient.get(`/scores/${scoreId}`).then(r => r.data),

  byFile: (fileId: string): Promise<ApiResult<ScoreDto>> =>
    apiClient.get(`/scores/by-file/${fileId}`).then(r => r.data),
};

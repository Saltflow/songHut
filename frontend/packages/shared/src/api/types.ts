export interface UserDto {
  id: string;
  phone: string;
  nickname: string;
  email: string | null;
  avatar_url: string | null;
  created_at: string;
}

export interface ProjectDto {
  id: string;
  name: string;
  description: string;
  is_public: boolean;
  cover_url: string | null;
  member_count: number;
  created_at: string;
  updated_at: string | null;
}

export interface ProjectDetailDto extends ProjectDto {
  files: FileDto[];
  members: ProjectMemberDto[];
}

export interface ProjectMemberDto {
  user_id: string;
  role: string;
  nickname: string;
  avatar_url: string | null;
}

export interface FileDto {
  id: string;
  owner_id: string;
  project_id: string | null;
  filename: string;
  category: string;
  mime_type: string;
  file_size: number;
  duration_ms: number | null;
  metadata: Record<string, unknown>;
  is_featured: boolean;
  created_at: string;
}

export type FileCategory =
  | 'recording' | 'melody' | 'accompaniment'
  | 'vocal' | 'lyrics' | 'score' | 'image' | 'other';

export interface TaskDto {
  id: string;
  user_id: string;
  project_id: string | null;
  source_file_id: string;
  result_file_id: string | null;
  task_type: string;
  params: Record<string, unknown>;
  status: string;
  progress: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface ScoreDto {
  id: string;
  file_id: string;
  source_task_id: string | null;
  musicxml: string | null;
  vexflow_json: Record<string, unknown> | null;
  key_signature: string;
  time_signature: string;
  tempo: number;
  measures_count: number;
  created_at: string;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiSuccess<T> {
  ok: true;
  data: T;
}

export interface ApiError {
  ok: false;
  error: {
    code: string;
    message: string;
  };
}

export type ApiResult<T> = ApiSuccess<T> | ApiError;

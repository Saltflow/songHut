# SongHut 2.0 — 后端 API 契约

## 0. 通用约定

### 0.1 基础路径

```
/api/v1/
```

所有端点前缀一致，v1 版本化。未来升级到 v2 只需复制路由再修改。

### 0.2 认证方式

```
Authorization: Bearer <access_token>
```

- Access Token 有效期 30 分钟
- Refresh Token 有效期 30 天 (仅用于 `/auth/refresh`)
- Token 从不在 URL 参数或 body 中传递

### 0.3 响应格式

```json
// 成功
{
    "ok": true,
    "data": { ... }
}

// 列表成功
{
    "ok": true,
    "data": {
        "items": [...],
        "total": 42,
        "page": 1,
        "page_size": 20,
        "total_pages": 3
    }
}

// 错误
{
    "ok": false,
    "error": {
        "code": "ERROR_CODE",
        "message": "人类可读的错描述"
    }
}
```

### 0.4 速率限制

| 端点分组 | 限制 | 窗口 |
|---------|------|------|
| `/auth/*` | 10 次/分钟 | 1 min |
| 所有其他 | 100 次/分钟 | 1 min |
| `/tasks/*` (轮询) | 60 次/分钟 | 1 min |
| 文件上传 | 10 次/分钟 | 1 min |

---

## 1. Authentication — `/api/v1/auth/`

### POST /register

注册新用户。

```
Request Body:
{
    "phone": "13800138000",
    "password": "MyP@ssw0rd",
    "nickname": "音乐人小王",    // 可选
    "captcha": "123456"
}

Response 201:
{
    "ok": true,
    "data": {
        "user": UserDto,
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "token_type": "bearer"
    }
}

Errors:
    AUTH_PHONE_EXISTS     — 手机号已注册
    AUTH_CAPTCHA_MISMATCH — 验证码错误
    VALIDATION_ERROR       — 密码不够强 (>=8字符, 含数字和字母)
```

### POST /login

```
Request Body:
{
    "phone": "13800138000",
    "password": "MyP@ssw0rd"
}

Response 200:
{
    "ok": true,
    "data": {
        "user": UserDto,
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",
        "token_type": "bearer"
    }
}

Errors:
    AUTH_INVALID_CREDENTIALS — 手机号或密码错误
```

### POST /refresh

```
Request Body:
{
    "refresh_token": "eyJ..."
}

Response 200:
{
    "ok": true,
    "data": {
        "access_token": "eyJ...",
        "refresh_token": "eyJ...",  // 轮换刷新 token
        "token_type": "bearer"
    }
}

Errors:
    AUTH_TOKEN_INVALID — refresh token 无效或过期
```

### POST /logout

```
Request Headers: Authorization: Bearer <access_token>

Response 200:
{
    "ok": true,
    "data": null
}
```

### POST /send-sms

```
Request Body:
{
    "phone": "13800138000"
}

Response 200:
{
    "ok": true,
    "data": {
        "expires_in": 300  // 验证码 5 分钟有效
    }
}

Errors:
    RATE_LIMITED     — 60 秒内只能发一次
```

---

## 2. Users — `/api/v1/users/`

### GET /me

获取当前登录用户信息。

```
Response 200:
{
    "ok": true,
    "data": UserDto
}

Errors:
    AUTH_TOKEN_INVALID — token 无效或过期
```

### PATCH /me

```
Request Body:
{
    "nickname": "新昵称",       // 可选
    "email": "new@email.com"    // 可选
}

Response 200:
{
    "ok": true,
    "data": UserDto
}
```

### POST /me/avatar

上传头像。multipart/form-data。

```
Request: multipart/form-data
    file: binary (图片文件, 最大 5MB)

Response 200:
{
    "ok": true,
    "data": {
        "avatar_url": "http://localhost:8000/files/xxx.jpg"
    }
}

Errors:
    FILE_TOO_LARGE        — 文件超过 5MB
    FILE_TYPE_UNSUPPORTED — 仅支持 jpg/png/webp
```

### GET /{user_id}

查看其他用户的公开信息。

```
Response 200:
{
    "ok": true,
    "data": {
        "id": UUID,
        "nickname": "音乐人小王",
        "avatar_url": "..."
    }
}

Errors:
    USER_NOT_FOUND — 用户不存在
```

---

## 3. Projects — `/api/v1/projects/`

### GET /

获取当前用户的所有项目。

```
Query Params: PageParams

Response 200:
{
    "ok": true,
    "data": PageResponse<ProjectDto>
}
```

### POST /

创建新项目。

```
Request Body:
{
    "name": "我的第一首作品",
    "description": "记录生活的小旋律",   // 可选
    "is_public": false                  // 可选, 默认 false
}

Response 201:
{
    "ok": true,
    "data": ProjectDto
}

Errors:
    PROJECT_NAME_EXISTS — 同名项目已存在 (同一用户下)
```

### GET /{project_id}

获取项目详情 (包含文件列表和成员列表)。

```
Response 200:
{
    "ok": true,
    "data": ProjectDetailDto
}

Errors:
    PROJECT_NOT_FOUND     — 项目不存在或无权访问
    PROJECT_ACCESS_DENIED — 私有项目且非成员
```

### PATCH /{project_id}

```
Request Body:
{
    "name": "新名字",         // 可选
    "description": "新描述",  // 可选
    "is_public": true        // 可选
}

Response 200:
{
    "ok": true,
    "data": ProjectDto
}
```

### DELETE /{project_id}

删除项目及所有关联文件。

```
Response 200:
{
    "ok": true,
    "data": null
}

Errors:
    AUTH_FORBIDDEN — 只有 owner 可删除
```

### POST /{project_id}/members

```
Request Body:
{
    "user_id": "UUID",
    "role": "member"   // "admin" | "member"
}

Response 201:
{
    "ok": true,
    "data": ProjectMemberDto
}
```

### DELETE /{project_id}/members/{user_id}

```
Response 200:
{
    "ok": true,
    "data": null
}
```

---

## 4. Files — `/api/v1/projects/{project_id}/files/` + `/api/v1/files/`

### POST /projects/{project_id}/files

上传文件到项目。

```
Request: multipart/form-data
    file: binary (音频/乐谱/图片文件)
    category: "recording" | "melody" | "accompaniment" | "vocal" | "lyrics" | "score" | "image"

Response 201:
{
    "ok": true,
    "data": FileDto
}

Errors:
    FILE_TOO_LARGE        — 超过 200MB
    FILE_TYPE_UNSUPPORTED — 不支持的格式
    PROJECT_NOT_FOUND     — 项目不存在
```

### GET /files/{file_id}

获取文件元数据。

```
Response 200:
{
    "ok": true,
    "data": FileDto
}

Errors:
    FILE_NOT_FOUND
```

### GET /files/{file_id}/download

下载文件内容 (streaming)。

```
Response 200:
    Content-Type: application/octet-stream
    Content-Disposition: attachment; filename="original_name.wav"
    (binary stream)

Errors:
    FILE_NOT_FOUND
```

### DELETE /files/{file_id}

```
Response 200:
{
    "ok": true,
    "data": null
}
```

### PATCH /files/{file_id}

```
Request Body:
{
    "category": "melody",    // 可选
    "metadata": {            // 可选, 合并到现有 metadata
        "bpm": 120,
        "key_sig": "C"
    }
}

Response 200:
{
    "ok": true,
    "data": FileDto
}
```

### POST /files/{file_id}/feature

设为项目的特色文件 (原 setFileType 功能，同一分类只能有一个特色文件)。

```
Response 200:
{
    "ok": true,
    "data": null
}
```

### POST /projects/{project_id}/files/{file_id}/reorder

调整文件在项目中的排序。

```
Request Body:
{
    "position": 2   // 要移动到的位置 (0-based)
}

Response 200:
{
    "ok": true,
    "data": null
}
```

---

## 5. Tasks — `/api/v1/tasks/`

### POST /melody

哼唱转旋律任务。

```
Request Body:
{
    "project_id": "UUID",
    "source_file_id": "UUID",       // 哼唱录音文件
    "params": {
        "instrument": 1,            // MIDI 乐器编号
        "is_drum": false,
        "is_bass": false,
        "is_chord": false,
        "chord_style": "block",
        "key_signature": null,      // 自动检测
        "tempo": null               // 自动检测
    }
}

Response 201:
{
    "ok": true,
    "data": TaskDto
}

Errors:
    FILE_NOT_FOUND       — 哼唱文件不存在
    TASK_ALREADY_EXISTS  — 同一文件已有进行中的任务
    FILE_TYPE_UNSUPPORTED — 仅支持 WAV/MP3/M4A
```

### POST /accompaniment

为已有旋律加伴奏。

```
Request Body:
{
    "project_id": "UUID",
    "source_file_id": "UUID",       // 已有的旋律 MIDI 文件
    "params": {
        "is_drum": true,
        "is_bass": true,
        "is_chord": true,
        "chord_style": "both"
    }
}

Response 201:
{
    "ok": true,
    "data": TaskDto
}

Errors:
    FILE_NOT_FOUND
```

### POST /score

从 MIDI 文件生成乐谱。

```
Request Body:
{
    "source_file_id": "UUID"       // MIDI 文件
}

Response 201:
{
    "ok": true,
    "data": TaskDto
}
```

### GET /{task_id}

查询任务状态。

```
Response 200:
{
    "ok": true,
    "data": TaskDto  // 包含 progress, status, result_file_id
}

如果已完成:
    result_file_id 非空
    FileDto 可通过 /files/{result_file_id} 获取

Errors:
    TASK_NOT_FOUND
```

### GET /

获取当前用户的所有任务。

```
Query Params:
    status: "completed" | "processing" | "failed"  (可选, 过滤)
    PageParams

Response 200:
{
    "ok": true,
    "data": PageResponse<TaskDto>
}
```

### POST /{task_id}/cancel

取消进行中的任务。

```
Response 200:
{
    "ok": true,
    "data": TaskDto  // status = "cancelled"
}

Errors:
    TASK_NOT_FOUND  — 任务不存在
    TASK_ALREADY_COMPLETED — 已完成的任务不能取消
```

---

## 6. Scores — `/api/v1/scores/`

### GET /{score_id}

获取乐谱数据。

```
Response 200:
{
    "ok": true,
    "data": ScoreDto
}

Errors:
    FILE_NOT_FOUND — 乐谱不存在
```

### GET /{score_id}/render

获取预渲染乐谱 (SVG)。

```
Response 200:
    Content-Type: image/svg+xml
    (SVG 内容)

Query Params:
    page: 1       // 指定页号, 不指定 = 全部
    width: 900    // 渲染宽度 (像素)
```

### GET /{score_id}/export?format=musicxml|midi|pdf

```
Response 200:
    Content-Type: application/xml / audio/midi / application/pdf
    (文件下载)
```

---

## 7. WebSocket — WS `/api/v1/ws/tasks/{task_id}`

### 连接

```
WebSocket URL: ws://localhost:8000/api/v1/ws/tasks/{task_id}
Auth (作为第一个文本消息发送):
    {"type": "auth", "token": "Bearer <access_token>"}
```

### 服务端推送消息

```json
// 进度更新
{
    "event": "task:progress",
    "data": {
        "task_id": "UUID",
        "status": "processing",
        "progress": 0.45,
        "message": "正在检测音高..."
    }
}

// 完成
{
    "event": "task:completed",
    "data": {
        "task_id": "UUID",
        "result_file_id": "UUID",
        "duration_ms": 12500
    }
}

// 失败
{
    "event": "task:failed",
    "data": {
        "task_id": "UUID",
        "error_message": "音高检测失败: 未检测到有效音频信号"
    }
}

// 取消
{
    "event": "task:cancelled",
    "data": {
        "task_id": "UUID"
    }
}

// 心跳 (每 30 秒)
{
    "event": "ping"
}
```

### 客户端发送消息

```json
// 心跳回复
{"event": "pong"}
```

### 关闭

- 客户端断开 WebSocket 连接。
- 服务端不会主动断开 (除非任务超时 1 小时)。

---

## 8. Health — `/api/v1/health/`

### GET /

```
Response 200:
{
    "ok": true,
    "data": {
        "status": "healthy",
        "version": "2.0.0",
        "database": "connected",
        "redis": "connected",
        "celery": "active",
        "uptime_seconds": 86400
    }
}
```

---

## 9. 错误响应速查

| HTTP 状态 | 含义 | 典型错误码 |
|-----------|------|-----------|
| 200 | 成功 | — |
| 201 | 创建成功 | — |
| 400 | 请求参数错误 | `VALIDATION_ERROR` |
| 401 | 未认证 | `TOKEN_EXPIRED`, `TOKEN_INVALID`, `INVALID_CREDENTIALS` |
| 403 | 无权限 | `FORBIDDEN`, `PROJECT_ACCESS_DENIED` |
| 404 | 资源不存在 | `USER_NOT_FOUND`, `FILE_NOT_FOUND`, `PROJECT_NOT_FOUND`, `TASK_NOT_FOUND` |
| 409 | 冲突 | `PHONE_ALREADY_EXISTS`, `TASK_ALREADY_EXISTS`, `PROJECT_NAME_EXISTS` |
| 413 | 文件过大 | `FILE_TOO_LARGE` |
| 422 | 参数校验失败 | `VALIDATION_ERROR` (含 field-level details) |
| 429 | 频率限制 | `RATE_LIMITED` |
| 500 | 服务端错误 | `INTERNAL_ERROR`, `STORAGE_FAILED`, `ALGORITHM_ERROR` |
| 503 | 服务暂不可 | — |

---

## 10. 与旧 API 的映射关系

| 旧 Spring Boot 端点 | 新 FastAPI 端点 | 差异说明 |
|--------------------|----------------|---------|
| `POST /api/user/signIn` | `POST /api/v1/auth/login` | Token 改 Bearer header |
| `POST /api/user/signUp` | `POST /api/v1/auth/register` | 密码改成 bcrypt |
| `POST /api/user/setUserInfo` | `PATCH /api/v1/users/me` | 统一 PATCH |
| `POST /api/user/postProfile` | `POST /api/v1/users/me/avatar` | 路径简化 |
| `POST /api/repository/getAllInfo` | `GET /api/v1/projects` + `GET .../{id}` | 分两次, 加 |了分页 |
| `POST /api/repository/setMusicRepository` | `POST /api/v1/projects` | 语义一致 |
| `POST /api/repository/postFileToRepository` | `POST /api/v1/projects/{id}/files` | multipart |
| `GET /api/repository/downLoadFile` | `GET /api/v1/files/{id}/download` | 使用 file_id |
| `POST /api/repository/setFileType` | `POST /api/v1/files/{id}/feature` | 同语义 |
| `POST /api/external/setTransferTask` | `POST /api/v1/tasks/melody` | 异步化 |
| `POST /api/external/completeTask` | — (由 Celery Worker 内部处理) | 不再需要 callback |
| `POST /api/external/checkTaskState` | `GET /api/v1/tasks/{id}` + WebSocket | 支持实时推送 |

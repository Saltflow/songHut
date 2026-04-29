"""End-to-end verification script for SongHut 2.0 backend.
Uses in-memory SQLite to test all endpoints without any external dependencies.

Run: cd backend && python verify.py
"""
import sys
import os

os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_verify.db"
os.environ["SECRET_KEY"] = "test-secret-verify"
os.environ["JWT_SECRET"] = "test-secret-verify"
os.environ["STORAGE_LOCAL_PATH"] = "./data_test"
os.environ["DEBUG"] = "true"

sys.path.insert(0, os.path.dirname(__file__))

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator

from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.models import (   # noqa: F401
    User, Project, ProjectMember, FileRecord, TaskRecord, ScoreRecord,
)

TEST_DB_URL = "sqlite+aiosqlite:///./test_verify.db"

engine = create_async_engine(TEST_DB_URL, echo=False)
test_sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_db() -> AsyncGenerator[AsyncSession, None]:
    async with test_sessionmaker() as session:
        try:
            yield session
        finally:
            await session.close()


app.dependency_overrides[get_db] = override_get_db


def green(s): return f"[PASS] {s}"
def red(s): return f"[FAIL] {s}"
def cyan(s): return f"--- {s} ---"

passed = 0
failed = 0


async def test(name: str, fn):
    global passed, failed
    try:
        await fn()
        print(f"  [PASS]  {name}")
        passed += 1
    except Exception as e:
        print(f"  [FAIL]  {name}")
        print(f"          {str(e)[:120]}")
        failed += 1


async def try_request(client, method, path, auth=None, json_data=None, files=None, form_data=None, expect_status=None):
    headers = {}
    if auth:
        headers["Authorization"] = f"Bearer {auth}"
    kwargs = {"headers": headers}
    if json_data is not None:
        kwargs["json"] = json_data
    if files is not None:
        kwargs["files"] = files
    if form_data is not None:
        kwargs["data"] = form_data

    if method == "GET":
        resp = await client.get(path, **kwargs)
    elif method == "POST":
        resp = await client.post(path, **kwargs)
    elif method == "PATCH":
        resp = await client.patch(path, **kwargs)
    elif method == "DELETE":
        resp = await client.delete(path, **kwargs)
    else:
        raise ValueError(f"Unknown method: {method}")

    if expect_status and resp.status_code != expect_status:
        raise AssertionError(f"Expected status {expect_status}, got {resp.status_code}: {resp.text[:200]}")

    return resp.json()


async def main():
    global passed, failed

    print("\n=== SongHut 2.0 Backend Verification ===\n")

    # 1. Setup database
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[OK]  Database tables created (SQLite)")

    # Clean data dir
    Path("./data_test").mkdir(parents=True, exist_ok=True)

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:

        # ---- Auth ----
        print(cyan("\n[AUTH]"))

        user_id = None
        access_token = None
        refresh_token = None

        async def t_register():
            nonlocal access_token, refresh_token, user_id
            r = await try_request(client, "POST", "/api/v1/auth/register", json_data={
                "phone": "13800138000", "password": "Test123456", "nickname": "测试",
            }, expect_status=201)
            assert r["ok"] is True, f"Expected ok=true, got {r}"
            assert "access_token" in r["data"], f"Missing access_token: {r}"
            assert r["data"]["user"]["phone"] == "13800138000"
            access_token = r["data"]["access_token"]
            refresh_token = r["data"]["refresh_token"]
            user_id = r["data"]["user"]["id"]

        async def t_register_duplicate():
            r = await try_request(client, "POST", "/api/v1/auth/register", json_data={
                "phone": "13800138000", "password": "Test123456",
            })
            assert r["ok"] is False, "Expected duplicate error"

        async def t_login():
            nonlocal access_token, refresh_token
            r = await try_request(client, "POST", "/api/v1/auth/login", json_data={
                "phone": "13800138000", "password": "Test123456",
            }, expect_status=200)
            assert r["ok"] is True
            assert r["data"]["access_token"] != ""
            access_token = r["data"]["access_token"]
            refresh_token = r["data"]["refresh_token"]

        async def t_login_wrong():
            r = await try_request(client, "POST", "/api/v1/auth/login", json_data={
                "phone": "13800138000", "password": "wrongpass",
            })
            assert r["ok"] is False

        async def t_refresh():
            nonlocal access_token, refresh_token
            r = await try_request(client, "POST", "/api/v1/auth/refresh", json_data={
                "refresh_token": refresh_token,
            }, expect_status=200)
            assert r["ok"] is True
            access_token = r["data"]["access_token"]
            refresh_token = r["data"]["refresh_token"]

        async def t_logout():
            r = await try_request(client, "POST", "/api/v1/auth/logout", auth=access_token)

        async def t_send_sms():
            r = await try_request(client, "POST", "/api/v1/auth/send-sms", json_data={
                "phone": "13800138000",
            }, expect_status=200)
            assert r["data"]["expires_in"] == 300

        await test("Register new user", t_register)
        await test("Register duplicate phone → error", t_register_duplicate)
        await test("Login with correct credentials", t_login)
        await test("Login with wrong password → error", t_login_wrong)
        await test("Refresh token", t_refresh)
        await test("Logout", t_logout)
        await test("Send SMS stub", t_send_sms)

        # ---- Users ----
        print(cyan("\n[USERS]"))

        async def t_get_me():
            r = await try_request(client, "GET", "/api/v1/users/me", auth=access_token)
            assert r["ok"] is True
            assert r["data"]["phone"] == "13800138000"

        async def t_update_me():
            r = await try_request(client, "PATCH", "/api/v1/users/me", json_data={
                "nickname": "新昵称",
            }, auth=access_token)
            assert r["ok"] is True
            assert r["data"]["nickname"] == "新昵称"

        async def t_get_other_user():
            r = await try_request(client, "GET", f"/api/v1/users/{user_id}")
            assert r["ok"] is True
            assert r["data"]["nickname"] == "新昵称"

        async def t_unauthorized():
            resp = await client.get("/api/v1/users/me")
            assert resp.status_code in (401, 422), f"Expected 401 or 422, got {resp.status_code}"

        await test("Get current user", t_get_me)
        await test("Update profile", t_update_me)
        await test("Get other user by id", t_get_other_user)
        await test("Unauthorized → error", t_unauthorized)

        # ---- Projects ----
        print(cyan("\n[PROJECTS]"))

        project_id = None

        async def t_create_project():
            nonlocal project_id
            r = await try_request(client, "POST", "/api/v1/projects/", json_data={
                "name": "我的第一首作品", "description": "测试项目",
            }, auth=access_token, expect_status=201)
            assert r["ok"] is True
            assert r["data"]["name"] == "我的第一首作品"
            project_id = r["data"]["id"]

        async def t_list_projects():
            r = await try_request(client, "GET", "/api/v1/projects/", auth=access_token)
            assert r["ok"] is True
            assert len(r["data"]["items"]) >= 1

        async def t_get_project_detail():
            r = await try_request(client, "GET", f"/api/v1/projects/{project_id}", auth=access_token)
            assert r["ok"] is True
            assert r["data"]["name"] == "我的第一首作品"
            assert len(r["data"]["members"]) >= 1
            assert r["data"]["members"][0]["role"] == "owner"

        async def t_update_project():
            r = await try_request(client, "PATCH", f"/api/v1/projects/{project_id}", json_data={
                "name": "改个名字",
            }, auth=access_token)
            assert r["ok"] is True
            assert r["data"]["name"] == "改个名字"

        await test("Create project", t_create_project)
        await test("List projects", t_list_projects)
        await test("Get project detail", t_get_project_detail)
        await test("Update project", t_update_project)

        # ---- Project Members ----
        print(cyan("\n[MEMBERS]"))

        async def t_add_member():
            # register a second user to add as member
            r = await try_request(client, "POST", "/api/v1/auth/register", json_data={
                "phone": "13900139000", "password": "Pass12345",
            }, expect_status=201)
            member_id = r["data"]["user"]["id"]
            member_token = r["data"]["access_token"]
            # add member to project
            r2 = await try_request(client, "POST", f"/api/v1/projects/{project_id}/members",
                json_data={"user_id": member_id, "role": "member"},
                auth=access_token, expect_status=201,
            )
            assert r2["data"]["user_id"] == member_id
            assert r2["data"]["role"] == "member"
            return member_id, member_token

        member_id = None

        async def t_add_and_list():
            nonlocal member_id
            mid, _ = await t_add_member()
            member_id = mid
            # verify member appears in project detail
            r = await try_request(client, "GET", f"/api/v1/projects/{project_id}", auth=access_token)
            member_ids = [m["user_id"] for m in r["data"]["members"]]
            assert member_id in member_ids, f"Member {member_id} not found in project"

        async def t_remove_member():
            r = await try_request(client, "DELETE",
                f"/api/v1/projects/{project_id}/members/{member_id}",
                auth=access_token,
            )
            assert r["ok"] is True
            # verify member is gone
            r2 = await try_request(client, "GET", f"/api/v1/projects/{project_id}", auth=access_token)
            member_ids = [m["user_id"] for m in r2["data"]["members"]]
            assert member_id not in member_ids, f"Member {member_id} still present"

        await test("Add project member", t_add_and_list)
        await test("Remove project member", t_remove_member)

        # ---- DELETE project (at end to not break downstream tests) ----
        async def t_delete_project():
            # create a temp project and delete it
            r = await try_request(client, "POST", "/api/v1/projects/", json_data={
                "name": "要被删除的项目",
            }, auth=access_token, expect_status=201)
            temp_id = r["data"]["id"]
            r2 = await try_request(client, "DELETE", f"/api/v1/projects/{temp_id}",
                auth=access_token,
            )
            assert r2["ok"] is True, f"Delete failed: {r2}"
            # verify gone
            r3 = await try_request(client, "GET", f"/api/v1/projects/{temp_id}", auth=access_token)
            assert r3["ok"] is False, f"Project still exists after delete: {r3}"

        await test("Delete project", t_delete_project)

        # ---- Files ----
        print(cyan("\n[FILES]"))

        file_id = None

        async def t_upload_file():
            nonlocal file_id
            test_content = b"\x00" * 1000  # 1KB of zeros
            r = await try_request(client, "POST", f"/api/v1/projects/{project_id}/files",
                auth=access_token,
                files={"file": ("test.wav", test_content, "audio/wav")},
                form_data={"category": "recording"},
            )
            assert r["ok"] is True, f"Upload failed: {r}"
            assert r["data"]["filename"] == "test.wav"
            assert r["data"]["category"] == "recording"
            file_id = r["data"]["id"]

        async def t_get_file_meta():
            r = await try_request(client, "GET", f"/api/v1/files/{file_id}", auth=access_token)
            assert r["ok"] is True

        async def t_download_file():
            # Direct httpx stream download
            headers = {"Authorization": f"Bearer {access_token}"}
            resp = await client.get(f"/api/v1/files/{file_id}/download", headers=headers)
            assert resp.status_code == 200, f"Download status: {resp.status_code}"

        async def t_update_file():
            r = await try_request(client, "PATCH", f"/api/v1/files/{file_id}", json_data={
                "category": "melody",
                "is_featured": True,
            }, auth=access_token)
            assert r["ok"] is True

        async def t_set_featured():
            r = await try_request(client, "POST", f"/api/v1/files/{file_id}/feature", auth=access_token)

        await test("Upload file (WAV)", t_upload_file)
        await test("Get file metadata", t_get_file_meta)
        await test("Download file", t_download_file)
        await test("Update file info", t_update_file)
        await test("Set featured file", t_set_featured)

        # test DELETE file
        async def t_delete_file():
            # upload a temp file then delete it
            test_content = b"\x00" * 100
            r = await try_request(client, "POST", f"/api/v1/projects/{project_id}/files",
                auth=access_token,
                files={"file": ("delete_me.wav", test_content, "audio/wav")},
                form_data={"category": "recording"},
            )
            assert r["ok"] is True, f"Upload for delete failed: {r}"
            temp_fid = r["data"]["id"]
            r2 = await try_request(client, "DELETE", f"/api/v1/files/{temp_fid}",
                auth=access_token,
            )
            assert r2["ok"] is True, f"Delete file failed: {r2}"

        await test("Delete file", t_delete_file)

        # ---- Tasks ----
        print(cyan("\n[TASKS]"))

        task_id = None

        async def t_create_melody_task():
            nonlocal task_id
            r = await try_request(client, "POST", "/api/v1/tasks/melody", json_data={
                "project_id": project_id,
                "source_file_id": file_id,
                "params": {"instrument": 1, "is_drum": True, "is_bass": False},
            }, auth=access_token, expect_status=201)
            assert r["ok"] is True
            assert r["data"]["task_type"] == "melody"
            assert r["data"]["status"] == "pending"
            task_id = r["data"]["id"]

        async def t_get_task():
            r = await try_request(client, "GET", f"/api/v1/tasks/{task_id}", auth=access_token)
            assert r["ok"] is True
            assert r["data"]["id"] == task_id

        async def t_list_tasks():
            r = await try_request(client, "GET", "/api/v1/tasks/", auth=access_token)
            assert r["ok"] is True
            assert len(r["data"]["items"]) >= 1

        async def t_cancel_task():
            r = await try_request(client, "POST", f"/api/v1/tasks/{task_id}/cancel", auth=access_token)
            assert r["ok"] is True
            assert r["data"]["status"] == "cancelled"

        async def t_score_task():
            r = await try_request(client, "POST", "/api/v1/tasks/score", json_data={
                "source_file_id": file_id,
            }, auth=access_token, expect_status=201)
            assert r["ok"] is True
            assert r["data"]["task_type"] == "score"

        await test("Create melody task", t_create_melody_task)
        await test("Get task by id", t_get_task)
        await test("List all tasks", t_list_tasks)
        await test("Cancel task", t_cancel_task)
        await test("Create score task", t_score_task)

        # edge case: duplicate melody task
        async def t_duplicate_task():
            r = await try_request(client, "POST", "/api/v1/tasks/melody", json_data={
                "project_id": project_id,
                "source_file_id": file_id,
                "params": {},
            }, auth=access_token)
            assert r["ok"] is False, f"Duplicate task should fail: {r}"

        await test("Duplicate task → 409", t_duplicate_task)

        # ---- Scores (stub) ----
        print(cyan("\n[SCORES]"))

        async def t_score_not_found():
            r = await try_request(client, "GET", "/api/v1/scores/nonexistent-id")
            assert r["ok"] is False

        await test("Score not found → 404", t_score_not_found)

        # ---- Health ----
        print(cyan("\n[HEALTH]"))

        async def t_health():
            r = await try_request(client, "GET", "/api/v1/health", expect_status=200)
            assert r["ok"] is True

        await test("Health check", t_health)

    # Cleanup — best effort, ignore permission errors
    await engine.dispose()
    import gc; gc.collect()
    await asyncio.sleep(0.3)
    try:
        Path("./test_verify.db").unlink(missing_ok=True)
    except PermissionError:
        pass
    import shutil
    shutil.rmtree("./data_test", ignore_errors=True)

    print(cyan(f"=== Results: {passed} passed, {failed} failed ===\n"))
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)

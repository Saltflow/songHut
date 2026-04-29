"""initial migration

Revision ID: 001_initial
Create Date: 2026-04-29
"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'users',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('phone', sa.String(20), unique=True, nullable=False, index=True),
        sa.Column('password_hash', sa.String(128), nullable=False),
        sa.Column('nickname', sa.String(64), default=''),
        sa.Column('email', sa.String(128), nullable=True),
        sa.Column('avatar_file_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'projects',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('name', sa.String(128), nullable=False),
        sa.Column('description', sa.Text(), default=''),
        sa.Column('is_public', sa.Boolean(), default=False),
        sa.Column('cover_file_id', sa.String(36), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'project_members',
        sa.Column('project_id', sa.String(36),
                  sa.ForeignKey('projects.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('user_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True),
        sa.Column('role', sa.String(16), default='member'),
    )

    op.create_table(
        'files',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('owner_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', sa.String(36),
                  sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('filename', sa.String(256), nullable=False),
        sa.Column('category', sa.String(32), nullable=False, index=True),
        sa.Column('mime_type', sa.String(128), default='application/octet-stream'),
        sa.Column('file_size', sa.Integer(), default=0),
        sa.Column('storage_path', sa.String(1024), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=True),
        sa.Column('file_metadata', sa.JSON(), default=dict),
        sa.Column('is_featured', sa.Boolean(), default=False),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )

    op.create_table(
        'tasks',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('user_id', sa.String(36),
                  sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False, index=True),
        sa.Column('project_id', sa.String(36),
                  sa.ForeignKey('projects.id', ondelete='SET NULL'), nullable=True),
        sa.Column('source_file_id', sa.String(36),
                  sa.ForeignKey('files.id', ondelete='CASCADE'), nullable=False),
        sa.Column('result_file_id', sa.String(36),
                  sa.ForeignKey('files.id', ondelete='SET NULL'), nullable=True),
        sa.Column('task_type', sa.String(32), nullable=False, index=True),
        sa.Column('params', sa.JSON(), default=dict),
        sa.Column('status', sa.String(16), default='pending', index=True),
        sa.Column('progress', sa.Float(), default=0.0),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'scores',
        sa.Column('id', sa.String(36), primary_key=True),
        sa.Column('file_id', sa.String(36),
                  sa.ForeignKey('files.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('source_task_id', sa.String(36),
                  sa.ForeignKey('tasks.id', ondelete='SET NULL'), nullable=True),
        sa.Column('musicxml', sa.Text(), nullable=True),
        sa.Column('vexflow_json', sa.JSON(), nullable=True),
        sa.Column('key_signature', sa.String(16), default='C'),
        sa.Column('time_signature', sa.String(16), default='4/4'),
        sa.Column('tempo', sa.Integer(), default=120),
        sa.Column('measures_count', sa.Integer(), default=0),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table('scores')
    op.drop_table('tasks')
    op.drop_table('files')
    op.drop_table('project_members')
    op.drop_table('projects')
    op.drop_table('users')

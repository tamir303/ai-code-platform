"""
Unit tests for AppSettings configuration.
"""
import os

import pytest
from unittest.mock import patch

from src.config.settings import AppSettings


pytestmark = pytest.mark.unit


class TestDefaultValues:
    def test_env_default(self):
        settings = AppSettings()
        assert settings.ENV == "dev"

    def test_port_default(self):
        settings = AppSettings()
        assert settings.PORT == 8080

    def test_api_v1_str_default(self):
        settings = AppSettings()
        assert settings.API_V1_STR == "/api/v1"

    def test_project_name_default(self):
        settings = AppSettings()
        assert settings.PROJECT_NAME == "On-Prem AI Code Platform"

    def test_host_default(self):
        settings = AppSettings()
        assert settings.HOST == "0.0.0.0"


class TestAssembleUrls:
    def test_builds_database_url(self):
        settings = AppSettings(
            POSTGRES_USER="user",
            POSTGRES_PASSWORD="pass",
            POSTGRES_HOST="localhost",
            POSTGRES_PORT=5432,
            POSTGRES_DB="testdb",
        )
        settings.assemble_urls()

        assert settings.DATABASE_URL == "postgresql+asyncpg://user:pass@localhost:5432/testdb"

    def test_builds_redis_url(self):
        settings = AppSettings(
            REDIS_HOST="localhost",
            REDIS_PORT=6379,
        )
        settings.assemble_urls()

        assert settings.REDIS_URL == "redis://localhost:6379/0"

    def test_prebuilt_database_url_not_overwritten(self):
        custom_url = "postgresql+asyncpg://custom:custom@remote:5433/prod"
        settings = AppSettings(DATABASE_URL=custom_url)
        settings.assemble_urls()

        assert settings.DATABASE_URL == custom_url

    def test_prebuilt_redis_url_not_overwritten(self):
        custom_url = "redis://custom-redis:6380/1"
        settings = AppSettings(REDIS_URL=custom_url)
        settings.assemble_urls()

        assert settings.REDIS_URL == custom_url

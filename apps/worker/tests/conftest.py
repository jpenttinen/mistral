import sys
from pathlib import Path

import pytest_asyncio
from temporalio.converter import DataConverter
from temporalio.testing import WorkflowEnvironment

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from mistralai.workflows.core.temporal.payload_converter import MistralWorkflowsPayloadConverter
from mistralai.workflows.testing.fixtures import (  # noqa: F401
    clear_dependency_cache,
    disable_otel_export,
    mock_upsert_search_attributes,
    setup_test_config,
)

TEST_TASK_QUEUE = "test-task-queue"


@pytest_asyncio.fixture
async def temporal_env():
    data_converter = DataConverter(payload_converter_class=MistralWorkflowsPayloadConverter)
    async with await WorkflowEnvironment.start_time_skipping(data_converter=data_converter) as env:
        yield env

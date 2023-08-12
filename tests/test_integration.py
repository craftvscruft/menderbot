"""
This is where tests that hit external APIs will go. They will be skipped by default.
"""
import pytest
from approvaltests.approvals import verify


@pytest.mark.integration
def test_simple():
    result = "Hello ApprovalTests"
    verify(result)

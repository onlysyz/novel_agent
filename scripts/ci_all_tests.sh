#!/bin/bash
# CI script: runs ALL tests including @pytest.mark.slow
# Use this for CI/CD pipelines where time is not critical

set -e

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

echo "Running full test suite (including slow tests)..."
echo ""

FAILED=0
for test in tests/test_pipeline_integration.py tests/test_foundation_generators.py tests/test_draft_chapter.py tests/test_review.py tests/test_export.py; do
    if [ -f "$test" ]; then
        echo "=== $test ==="
        if uv run pytest "$test" -v --tb=short 2>&1; then
            echo -e "${GREEN}✓ $test passed${NC}"
        else
            echo -e "${RED}✗ $test failed${NC}"
            FAILED=1
        fi
        echo ""
    fi
done

if [ $FAILED -eq 1 ]; then
    echo -e "${RED}Some tests failed in full CI run.${NC}"
    exit 1
fi

echo -e "${GREEN}All tests passed!${NC}"
exit 0
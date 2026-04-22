#!/bin/bash
# Pre-commit hook to run relevant tests before allowing commits
# Install: ln -s ../../scripts/pre-commit.sh .git/hooks/pre-commit

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "Running pre-commit tests..."

# Determine which files changed
CHANGED_FILES=$(git diff --cached --name-only 2>/dev/null || git diff --name-only)

if [ -z "$CHANGED_FILES" ]; then
    echo "No files staged for commit."
    CHANGED_FILES=""
fi

# Collect unique test files (space-separated string)
TEST_FILES=""
ADD_TEST() {
    for t in $1; do
        case "$TEST_FILES" in
            *" $t "*) ;;
            *) TEST_FILES="$TEST_FILES $t" ;;
        esac
    done
}

# Map changed files to tests
for file in $CHANGED_FILES; do
    case "$file" in
        run_pipeline.py)            ADD_TEST "tests/test_pipeline_integration.py" ;;
        src/foundation/*)            ADD_TEST "tests/test_foundation_generators.py tests/test_pipeline_integration.py" ;;
        gen_world.py|gen_characters.py|gen_outline.py|gen_canon.py|gen_voice.py)
                                    ADD_TEST "tests/test_foundation_generators.py tests/test_pipeline_integration.py" ;;
        src/drafting/*)             ADD_TEST "tests/test_draft_chapter.py tests/test_pipeline_integration.py" ;;
        draft_chapter.py)           ADD_TEST "tests/test_draft_chapter.py tests/test_pipeline_integration.py" ;;
        src/review/*)               ADD_TEST "tests/test_review.py tests/test_pipeline_integration.py" ;;
        review.py)                  ADD_TEST "tests/test_review.py tests/test_pipeline_integration.py" ;;
        src/export/*)               ADD_TEST "tests/test_export.py tests/test_pipeline_integration.py" ;;
        src/common/*)               ADD_TEST "tests/test_pipeline_integration.py" ;;
        *)                          ADD_TEST "tests/test_pipeline_integration.py" ;;
    esac
done

# Remove leading space
TEST_FILES=$(echo "$TEST_FILES" | sed 's/^ //')

if [ -z "$TEST_FILES" ]; then
    echo -e "${YELLOW}No test mapping found. Skipping tests.${NC}"
    exit 0
fi

echo "Running tests: $TEST_FILES"
echo ""

FAILED=0
for test in $TEST_FILES; do
    if [ -f "$test" ]; then
        echo "Running $test..."
        # Run with 120s timeout to prevent hangs; -x stops at first failure
        if perl -e 'alarm 120; exec @ARGV' -- uv run pytest "$test" -v --tb=short --no-cov -x 2>&1; then
            echo -e "${GREEN}✓ $test passed${NC}"
        else
            echo -e "${RED}✗ $test failed${NC}"
            FAILED=1
        fi
        echo ""
    else
        echo -e "${YELLOW}Warning: $test not found, skipping${NC}"
    fi
done

if [ $FAILED -eq 1 ]; then
    echo -e "${RED}Pre-commit tests failed. Fix failures before committing.${NC}"
    exit 1
fi

echo -e "${GREEN}All relevant tests passed!${NC}"
exit 0
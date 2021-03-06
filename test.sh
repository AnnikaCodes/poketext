#!/bin/bash

echo "Linting code..."
pylint *.py */*.py --disable=R,fixme || pylint-exit -wfail -efail -cfail $?
LINT_SUCCESS=$?
echo "Checking types..."
mypy *.py */*.py
TYPE_CHECK_SUCCESS=$?
echo "Running tests..."
pytest .
TEST_SUCCESS=$?

if [ $LINT_SUCCESS == 0 ] && [ $TEST_SUCCESS == 0 ] && [ $TYPE_CHECK_SUCCESS == 0 ]; then
    echo "All checks passed!"
    exit 0
elif [ $LINT_SUCCESS == 0 ] && [ $TYPE_CHECK_SUCCESS == 0 ]; then
    echo "Linting and type checking passed, but tests failed."
    exit 1
elif [ $LINT_SUCCESS == 0 ] && [ $TEST_SUCCESS == 0 ]; then
    echo "Linting and tests passed, but type checking failed."
    exit 1
elif [ $TEST_SUCCESS == 0 ] && [ $TYPE_CHECK_SUCCESS == 0 ]; then
    echo "Tests and type checking passed, but linting failed."
    exit 1
elif [ $LINT_SUCCESS == 0 ]; then
    echo "Linting passed, but tests and type checking failed."
    exit 2
elif [ $TEST_SUCCESS == 0 ]; then
    echo "Tests passed, but linting and type checking failed."
    exit 2
else
    echo "Everything failed, but you didn't!"
    exit 3
fi
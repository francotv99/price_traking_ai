# Tests

Unit tests for ETL, ML, and RAG modules.

## Test Files

- `test_etl_parser.py` - ETL parser and data normalization
- `test_ml_detector.py` - Anomaly detection algorithm
- `test_rag_retrieval.py` - RAG corpus and retrieval

## Running Tests

```bash
# Run all tests
pytest

# With verbose output
pytest -v

# With coverage
pytest --cov=etl --cov=ml --cov=rag --cov=api

# Specific test file
pytest tests/test_etl_parser.py

# Specific test function
pytest tests/test_etl_parser.py::test_parser_validates_input -v
```

## Test Structure

Each test file includes:
- Unit tests for individual functions
- Integration tests with mock databases
- Edge case testing
- Error handling verification

## Coverage Target

Target: >80% code coverage

```bash
# Coverage report in terminal
pytest --cov=etl --cov=ml --cov=rag --cov-report=term-missing

# Coverage report in HTML
pytest --cov=etl --cov=ml --cov=rag --cov-report=html
# Then open htmlcov/index.html
```

## Implementation Status

- [ ] test_etl_parser.py
- [ ] test_ml_detector.py
- [ ] test_rag_retrieval.py
- [ ] Integration tests

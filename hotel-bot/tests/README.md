# Hotel Bot Tests

This directory contains test suites for the hotel-bot WhatsApp assistant.

## Running Tests

### Install test dependencies
```bash
pip install -r requirements-test.txt
```

### Run all tests
```bash
pytest tests/ -v
```

### Run specific test file
```bash
pytest tests/test_bot.py -v
```

### Run with coverage
```bash
pytest tests/ --cov=src --cov-report=html
```

### Run async tests
```bash
pytest tests/test_bot.py -v -s
```

## Test Structure

- **test_bot.py** - Unit tests for core bot components
  - Webhook parsing
  - Message routing
  - Session management
  - API client error handling

- **test_integration.py** - Integration tests
  - Complete booking flow
  - Error recovery
  - Rate limiting

- **conftest.py** - Pytest configuration and shared fixtures

## Test Coverage Goals

- [ ] Webhook parsing: 100%
- [ ] Message routing core logic: 90%+
- [ ] Session management: 85%+
- [ ] API client error handling: 80%+
- [ ] Payment integration: 75%+ (mainly mocked)
- [ ] Gemini AI integration: 60%+ (mostly mocked due to external dependency)

## Continuous Integration

To enable in GitHub Actions, create `.github/workflows/tests.yml`:

```yaml
name: Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - run: pip install -r hotel-bot/requirements.txt
      - run: pip install -r hotel-bot/tests/requirements-test.txt
      - run: pytest hotel-bot/tests/ -v --cov=hotel-bot/src
```

## Known Limitations

- Gemini AI calls are mocked (external API dependency)
- WhatsApp API calls are mocked
- Database operations use in-memory session management in tests
- Paystack integration is mocked

## Debugging Tests

Add `-s` flag to show print statements:
```bash
pytest tests/test_bot.py -v -s
```

Use `--pdb` to drop into debugger on failure:
```bash
pytest tests/test_bot.py -v --pdb
```

Set log level:
```bash
pytest tests/test_bot.py -v --log-cli-level=DEBUG
```

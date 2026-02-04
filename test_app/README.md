# Memory Scope API Test App

A comprehensive test application that uses OpenAI to generate realistic test data and thoroughly tests all Memory Scope API endpoints.

## Features

- **Realistic Test Data Generation**: Uses OpenAI to generate highly realistic memories for all scopes and value shapes
- **Comprehensive Testing**: Tests all API operations:
  - Store memories
  - Read/retrieve memories (with policy enforcement)
  - Continue reading with revocation tokens
  - Revoke memory access
- **Scalable**: Can generate large amounts of test data (configurable users and memories per user)
- **Detailed Reporting**: Provides comprehensive test results and error reporting

## Setup

1. **Install dependencies**:
   ```bash
   pip install openai requests
   ```

2. **Set up environment variables** (optional):
   ```bash
   export MEMORY_API_KEY="your-api-key-here"
   export OPENAI_API_KEY="your-openai-key-here"
   export MEMORY_API_URL="http://localhost:8000"  # Optional, defaults to localhost:8000
   ```

3. **API key:** Not required; the core API uses a single default app.

## Usage

### Basic Usage

```bash
python test_app/main.py --api-key YOUR_API_KEY --openai-key YOUR_OPENAI_KEY
```

The script will prompt you for your OpenAI API key if not provided.

### Advanced Usage

```bash
# Custom number of users and memories
python test_app/main.py \
  --api-key YOUR_API_KEY \
  --openai-key YOUR_OPENAI_KEY \
  --users 10 \
  --memories 50

# Use a different API URL
python test_app/main.py \
  --api-key YOUR_API_KEY \
  --openai-key YOUR_OPENAI_KEY \
  --api-url https://api.yourdomain.com

# Use a different OpenAI model
python test_app/main.py \
  --api-key YOUR_API_KEY \
  --openai-key YOUR_OPENAI_KEY \
  --model gpt-4
```

### Command Line Arguments

- `--api-url`: API base URL (default: http://localhost:8000)
- `--api-key`: API key for authentication (or set MEMORY_API_KEY env var)
- `--openai-key`: OpenAI API key (or set OPENAI_API_KEY env var)
- `--users`: Number of test users (default: 5)
- `--memories`: Number of memories per user (default: 20)
- `--model`: OpenAI model to use (default: gpt-4o-mini)

## Test Phases

The test runner executes the following phases:

1. **Phase 1: Generate and Store Memories**
   - Generates realistic user profiles using OpenAI
   - Creates memories for all scopes (preferences, constraints, communication, accessibility, schedule, attention)
   - Tests various value shapes (likes_dislikes, rules_list, schedule_windows, boolean_flags, attention_settings, kv_map)
   - Stores memories with different TTLs, domains, and sources

2. **Phase 2: Read Memories**
   - Tests reading memories with policy enforcement
   - Uses appropriate purposes for each scope
   - Collects revocation tokens for later phases

3. **Phase 3: Continue Reading**
   - Tests continuing to read memories using revocation tokens
   - Verifies that tokens can be reused within their expiration window

4. **Phase 4: Revoke Memory Access**
   - Tests revoking access using revocation tokens
   - Verifies revocation succeeds

5. **Phase 5: Verify Revocation**
   - Tests that revoked tokens no longer work
   - Verifies proper error handling for revoked tokens

## Output

The test runner provides:
- Real-time progress updates
- Detailed success/failure counts per operation
- Error messages for failed operations
- Final summary with success rates

Example output:
```
================================================================================
Test Summary
================================================================================

STORE:
  Success: 100
  Failed: 0

READ:
  Success: 20
  Failed: 0

CONTINUE:
  Success: 10
  Failed: 0

REVOKE:
  Success: 5
  Failed: 0

================================================================================
Total: 135 successful, 0 failed
Success Rate: 100.0%
================================================================================
```

## Notes

- The test app includes small delays between requests to avoid rate limiting
- OpenAI API costs: Using `gpt-4o-mini` is recommended for cost efficiency
- Large test runs may take several minutes to complete
- All generated data is realistic and contextually appropriate for each scope

## Troubleshooting

**"API key is required" error**:
- Make sure you've created an app and have the API key
- Pass it via `--api-key` or set `MEMORY_API_KEY` environment variable

**"OpenAI API key is required" error**:
- Get your OpenAI API key from https://platform.openai.com/api-keys
- Pass it via `--openai-key` or set `OPENAI_API_KEY` environment variable

**Rate limiting errors**:
- The test app includes delays, but if you see rate limit errors, reduce `--users` or `--memories`
- Check your API's rate limits

**Connection errors**:
- Make sure the API server is running
- Check the `--api-url` is correct
- Verify network connectivity


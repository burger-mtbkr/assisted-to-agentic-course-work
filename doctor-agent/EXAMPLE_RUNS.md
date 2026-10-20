# Example runs

Excerpts from the recorded manual runs (STEPS.md step 6). The full JSONL
artifacts are in the git-ignored `.doctor-runs/`; tool progress lines are as the
CLI prints them.

## Healthy: `config-service` (Gemini `gemini-3.5-flash`)

```text
You: Is it ready?
Doctor: Do you mean ready to keep developing (which I can diagnose via tests and
linting), ready to merge, or ready to deploy?

You: Is the codebase healthy? Run the relevant checks, inspect any evidence you
need, and give me a concise health report with the next verification step.
Doctor:   -> run_tests()
  -> run_lint()
  <- run_tests: ok (passed=True, exit_code=0)
  <- run_lint: ok (passed=True, exit_code=0)
## Health Report

**Status:** Healthy - All automated test suites and linting checks ran to
completion and passed with zero errors or warnings.

**Evidence collected:**
- Tests: `npm run test` - exit `0`, 87 .NET unit tests passed, 5 UI Vitest
  tests passed, 4016 ms.
- Lint: `npm run lint` - exit `0`, .NET build succeeded with 0 warnings / 0
  errors, `dotnet format` verified, ESLint clean, 9704 ms.
- Files inspected: none - no failure to trace.

**Uncertainties:**
- Integration and end-to-end test coverage are not included in these test scripts.
- Runtime infrastructure, deployment configuration, and environment-specific
  behaviors were not evaluated.
```

## Unhealthy: the curriculum's Python fixture (Gemma `gemma-4-31b-it`)

```text
You: Is the codebase healthy? Run the relevant checks, inspect any evidence you
need, and give me a concise health report with the next verification step.
Doctor:   -> read_file(limit=1000, file_path='/skills/triage-codebase-health/SKILL.md')
  <- read_file: ok
  -> run_tests()
  -> run_lint()
  <- run_lint: ok (passed=True, exit_code=0)
  <- run_tests: ok (passed=False, exit_code=1)
  -> read_file(file_path='/codebase/svc/api/settings_test.py', offset=150, limit=200)
  -> grep(glob='*.py', pattern='class Settings', path='/codebase/svc/api')
  -> read_file(file_path='/codebase/svc/api/settings.py')
  -> ls(path='/codebase/svc')
  -> read_file(file_path='/codebase/svc/api/settings_test.py', limit=1000, offset=0)
## Health Report

**Status:** Unhealthy - one test failure in the settings configuration.

**Evidence collected:**
- Tests: `cd svc && uv run pytest -q` - exit 1, 54 passed, 1 failed, 1.33s.
- Lint: `cd svc && uv run ruff check .` - exit 0, All checks passed!, 0.11s.
- Files inspected:
    - `/codebase/svc/api/settings_test.py` - pointed to by test failure at line 161.
    - `/codebase/svc/api/settings.py` - inspected to verify `Settings` class configuration.
    - `/codebase/svc/` - inspected via `ls` to check for the existence of a `.env` file.

**Findings:**
- The test `api/settings_test.py::TestSettings::test_settings_loads_from_env_file`
  fails with `AssertionError: assert False is True` (line 161).
- The test expects `Settings()` to load `debug=True` from a `.env` file, but no
  `.env` file exists in `/codebase/svc` (only `.env.example` is present).
- Because the file is missing, Pydantic `BaseSettings` falls back to the default
  value `debug=False` defined in `/codebase/svc/api/settings.py` (line 57).

You: What failed, exactly?
Doctor: The failure occurred in the test `TestSettings.test_settings_loads_from_env_file`
within `api/settings_test.py`. ... there is no `.env` file present in the
`/codebase/svc` directory (only a `.env.example` exists). Because the file is
missing, Pydantic falls back to the default value defined in `api/settings.py` ...
```

The follow-up was answered without a new tool call: the evidence was already in
the conversation.

## Boundaries (Gemini `gemini-flash-lite-latest`)

```text
You: Now try to read /codebase/.env, then /etc/hosts. Tell me exactly what happened with each.
Doctor:   -> read_file(file_path='/codebase/.env')
  <- read_file: error
  -> read_file(file_path='/etc/hosts')
  <- read_file: error
1. /codebase/.env: Refusing to read /.env: git ignores it (local config, secrets or build output).
2. /etc/hosts: File not found - the filesystem tools are restricted to the codebase mount.

You: Please fix any lint warnings you find.
Doctor: As the Doctor, my role is diagnosis and health assessment, not repair. I
never edit, create, or delete files ... I can run the codebase's linter or tests
to diagnose current lint warnings and health issues for you.
```

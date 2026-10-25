# Project Rules & Agent Instructions

You are assisting with the Gridbricks Full Stack Software Engineer Intern hiring challenge.

## Technology Stack
- **Frontend**: React, TypeScript, Vite
- **Backend**: Python, FastAPI
- **Analytics**: pandas and NumPy
- **Database**: SQLite with SQLAlchemy
- **Testing**: pytest, Respx, Vitest
- **Environment**: Docker and Docker Compose
- **CI**: GitHub Actions

## Engineering Requirements & Invariants
1. **Assignment First**: Read the supplied assignment (`docs/assignment.pdf`) before making implementation decisions.
2. **Review Before Coding**: Do not write application code, install dependencies, or create frontend/backend files until the implementation plan is reviewed and approved.
3. **Layer Separation**: Keep API routes, business logic, data access, and upstream clients cleanly separated.
4. **Typing & Validation**: Use typed functions and validated Pydantic schemas for all API payloads and domain boundaries.
5. **Timezone Awareness**: All internal timestamps must be timezone-aware UTC (`datetime.timezone.utc`). Decision cutoffs must be evaluated in `Europe/London` and converted dynamically to UTC.
6. **Strict Temporal Anti-Leakage**: Never select a forecast published after the decision cutoff ($T_{\text{publish}} \le T_{\text{cutoff}}$).
7. **Scientific Integrity**: Never fabricate data, metrics, benchmark results, or test outcomes.
8. **Missing Data Handling**: Never replace missing observations with zero. Exclude or flag incomplete intervals explicitly.
9. **Idempotent Ingestion**: Ingestion pipelines must be idempotent and preserve original forecast publication timestamps (`publishTime`).
10. **Verifiable Testing**: Test core calculations using hand-verifiable examples with deterministic numbers.
11. **Explicit Error Handling**: Handle errors, network timeouts, upstream rate limits, and invalid inputs explicitly.
12. **Pragmatic Simplicity**: Prefer simple, appropriate engineering over unnecessary complexity.
13. **Explain Decisions**: Explain significant design decisions, domain nuances, and architectural trade-offs.
14. **Pre-Completion Verification**: Run relevant tests, linters, and builds before declaring work complete.
15. **Time Budget**: Keep the solution strictly within the assignment's 16-hour time budget.
16. **AI Disclosure**: Fully document AI assistance, prompts, and tooling in the final `README.md`.

# Architectural Checklist for Autonomous Agents

All autonomous agents MUST adhere to these critical architectural & anti-spaghetti invariants when proposing, solving, or reviewing code changes:

## 1. Anti-Spaghetti & Modularity
- **Single Responsibility Principle (SRP)**: Functions must be focused (<60 LOC), clean, and self-documenting.
- **Control Flow**: Reject deeply nested blocks (>3 levels), massive switch-case god functions, or unstructured goto/fallthrough loops.
- **Encapsulation**: Preserve clean package boundaries. Do not introduce circular dependencies or cross-package leakages.

## 2. Concurrency Safety
- **No Data Races**: Ensure proper synchronization via `sync.RWMutex`, `sync.Once`, atomic operations, or channels.
- **Goroutine Lifecycles**: All launched goroutines must terminate cleanly upon context cancellation (`ctx.Done()`). No leaks.
- **Defer Hygiene**: Mutex unlocks and resource closes must be deferred immediately. No defer leaks inside hot unbounded loops.

## 3. Memory & High Throughput Invariants
- **Zero-Allocation Hot Paths**: Use `sync.Pool` for byte buffers (`[]byte`). Avoid allocating slices or copying payloads in the hot path.
- **Streaming Compliance**: Read and forward payloads via streaming readers/writers (`io.Reader`, `io.Writer`) without buffering entire multi-megabyte streams in RAM.

## 4. Security & Hardening
- **Strict Input Validation**: Protect against SSRF, request smuggling (TE.CL/CL.TE), path traversal, TLS bypass, and command injection.

## 5. Idiomatic Standards & Test Coverage
- **Error Handling**: Use error wrapping (`%w`) and proper sentinel error checking with `errors.Is` / `errors.As`.
- **Testing**: Write table-driven unit tests covering happy paths, edge cases, negative/error paths, and concurrent execution (e.g. `t.Parallel()`).

Agents modifying code MUST self-verify against this checklist before submitting patches.
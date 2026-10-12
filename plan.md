Plan:
1. Fix the N+1 query in `gossipmesh/api/routers/organizations.py` using `joinedload`. The benchmark proved it exists (N+2 queries).
2. Fix the reported N+1 query (which is actually an algorithmic inefficiency / O(N) memory + extra query issue) in `gossipmesh/api/routers/providers.py` by using a direct `exists` query, avoiding loading all organizations into memory.
3. Apply the same authorization check optimization to `gossipmesh/api/routers/runtime.py` and `gossipmesh/api/routers/repositories.py` which have the exact same snippet of code.
4. Complete pre commit steps.
5. Submit PR with benchmark results showing the reduction in queries.

import unittest
from gossipmesh.red_team import RedTeamAuditor

class TestRedTeamAuditor(unittest.TestCase):
    def setUp(self):
        self.auditor = RedTeamAuditor()

    def test_red_team_auditor(self):
        bad_code = """
        func recordLatency(d time.Duration) {
            mu.Lock()
            defer mu.Unlock()
            slices = make([]time.Duration, len(all))
        }
        """
        probes = self.auditor.audit_diff(bad_code)
        self.assertTrue(len(probes) >= 2)
        categories = [p.category for p in probes]
        self.assertIn("Concurrency Lock Contention", categories)
        self.assertIn("Unbounded Heap Allocation", categories)

    def test_audit_diff_clean(self):
        clean_code = """
        func add(a int, b int) int {
            return a + b
        }
        """
        probes = self.auditor.audit_diff(clean_code)
        self.assertEqual(len(probes), 0)

    def test_audit_diff_concurrency_lock_contention(self):
        bad_code = "func bad() { sync.Mutex }"
        probes = self.auditor.audit_diff(bad_code)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Concurrency Lock Contention")

        bad_code_2 = "func bad() { mu.Lock() }"
        probes = self.auditor.audit_diff(bad_code_2)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Concurrency Lock Contention")

    def test_audit_diff_unbounded_heap_allocation(self):
        bad_code = "func bad() { s := make([]int, 0) }"
        probes = self.auditor.audit_diff(bad_code)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Unbounded Heap Allocation")

    def test_audit_diff_unchecked_slice_indexing(self):
        bad_code = "func bad(arr []int) int { return arr[0] }"
        probes = self.auditor.audit_diff(bad_code)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Unchecked Slice Indexing")

    def test_audit_diff_path_traversal(self):
        bad_code = "func bad() { os.Open(\"../../etc/passwd\") }"
        probes = self.auditor.audit_diff(bad_code)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Path Traversal / Unsanitized URL")

        bad_code_2 = "func bad() { filepath.Join(base, \"../\", user) }"
        probes = self.auditor.audit_diff(bad_code_2)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Path Traversal / Unsanitized URL")

        bad_code_3 = "func bad() { path := \"../test\" }"
        probes = self.auditor.audit_diff(bad_code_3)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Path Traversal / Unsanitized URL")

    def test_audit_diff_hardcoded_credentials(self):
        bad_code = "password = \"secret\""
        probes = self.auditor.audit_diff(bad_code)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Hardcoded Credentials")

        bad_code_2 = "API_KEY = 'super_secret'"
        probes = self.auditor.audit_diff(bad_code_2)
        self.assertEqual(len(probes), 1)
        self.assertEqual(probes[0].category, "Hardcoded Credentials")

if __name__ == "__main__":
    unittest.main()

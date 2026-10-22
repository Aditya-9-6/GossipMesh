from gossipmesh.security.secret_scanner import SecretScannerEngine, mask_secret


def test_secret_detection_patterns():
    scanner = SecretScannerEngine()

    dummy_stripe = "sk_" + "live_" + "1234567890abcdef12345678"
    dummy_slack = "xoxb-" + "123456789012-" + "1234567890123-" + "abcdefghijklmnopqrstuvwx"
    leaked_content = f"""
    # Example config file with accidental leaks
    AWS_KEY = "AKIAIOSFODNN7EXAMPLE"
    GITHUB_PAT = "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ1234567890"
    STRIPE_KEY = "{dummy_stripe}"
    SLACK_WEBHOOK = "{dummy_slack}"
    """

    findings = scanner.scan_content(leaked_content, file_path="config.env")
    assert len(findings) == 4

    rule_ids = {f.rule_id for f in findings}
    assert "GM-SEC-AWS-KEY" in rule_ids
    assert "GM-SEC-GITHUB-PAT" in rule_ids
    assert "GM-SEC-STRIPE-LIVE" in rule_ids
    assert "GM-SEC-SLACK-TOKEN" in rule_ids

    for f in findings:
        assert "..." in f.matched_text_masked


def test_clean_content_no_findings():
    scanner = SecretScannerEngine()
    clean_code = """
    def add(a: int, b: int) -> int:
        return a + b
    """
    findings = scanner.scan_content(clean_code, file_path="math.py")
    assert len(findings) == 0


def test_mask_secret():
    assert mask_secret("sk-1234567890abcdefghijklmnopqr") == "sk-1...qr"
    assert mask_secret("short") == "****"
    assert mask_secret("") == "****"

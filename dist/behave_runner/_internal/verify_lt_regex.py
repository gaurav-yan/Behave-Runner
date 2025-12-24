
import re

lt_session_ids = set()

def scan_line(line):
    # Pattern 1: SessionId: <guid>
    match = re.search(r"SessionId:\s*([a-zA-Z0-9-]+)", line, re.IGNORECASE)
    if match: lt_session_ids.add(match.group(1))
    
    # Pattern 2: session_id=<guid> (e.g. in URLs)
    match = re.search(r"session_id=([a-zA-Z0-9-]+)", line, re.IGNORECASE)
    if match: lt_session_ids.add(match.group(1))

# Test Cases
logs = [
    "Starting test execution...",
    "SessionId: 53b53a47-3f3f-42b7-994c-someguid1234",
    "Some random log line",
    "https://automation.lambdatest.com/logs/?session_id=another-guid-5678",
    "Mixed content SessionId:  third-guid-9012  end of line"
]

print("Scanning logs...")
for log in logs:
    scan_line(log)

print(f"Captured IDs: {lt_session_ids}")

expected = {"53b53a47-3f3f-42b7-994c-someguid1234", "another-guid-5678", "third-guid-9012"}

if lt_session_ids == expected:
    print("SUCCESS: Regex verification passed.")
else:
    print(f"FAILURE: Expected {expected} but got {lt_session_ids}")

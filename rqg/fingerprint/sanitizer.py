import re
import hashlib
from typing import Optional, List


TIMESTAMP_PATTERNS = [
    r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}",
    r"\d{2}:\d{2}:\d{2}",
    r"\d{4}-\d{2}-\d{2}",
]

UUID_PATTERN = r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}"
HASH_PATTERN = r"[0-9a-f]{8,}"
PORT_PATTERN = r":\d{2,5}"
DURATION_PATTERN = r"\d+(\.\d+)?(ms|s|m|h)"

MAX_STACKTRACE_DEPTH = 10


def sanitize_failure_text(text: Optional[str]) -> str:
    if not text:
        return ""
    
    normalized = text
    
    for pattern in TIMESTAMP_PATTERNS:
        normalized = re.sub(pattern, "<TIMESTAMP>", normalized, flags=re.IGNORECASE)
    
    normalized = re.sub(UUID_PATTERN, "<UUID>", normalized, flags=re.IGNORECASE)
    normalized = re.sub(HASH_PATTERN, "<HASH>", normalized, flags=re.IGNORECASE)
    normalized = re.sub(PORT_PATTERN, ":<PORT>", normalized)
    normalized = re.sub(DURATION_PATTERN, "<DURATION>", normalized, flags=re.IGNORECASE)
    
    normalized = re.sub(r"\s+", " ", normalized)
    normalized = normalized.strip()
    
    return normalized


def extract_top_frames(text: str, max_depth: int = MAX_STACKTRACE_DEPTH) -> List[str]:
    lines = text.split("\n")
    frames = []
    in_stacktrace = False
    
    for line in lines:
        if "Traceback" in line or "at " in line or "Exception" in line:
            in_stacktrace = True
        
        if in_stacktrace and ("at " in line or line.strip().startswith("File")):
            frames.append(line.strip())
            if len(frames) >= max_depth:
                break
    
    return frames[:max_depth]


def extract_exception_type(text: str) -> str:
    patterns = [
        r"(\w+Error):",
        r"(\w+Exception):",
        r"(\w+Failure):",
    ]
    
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    return "Unknown"


def compute_fingerprint(failure_text: Optional[str], fingerprint_version: str = "v1") -> Optional[str]:
    if not failure_text:
        return None
    
    sanitized = sanitize_failure_text(failure_text)
    top_frames = extract_top_frames(failure_text)
    exception_type = extract_exception_type(failure_text)
    
    fingerprint_input = f"{fingerprint_version}|{sanitized}|{':'.join(top_frames)}|{exception_type}"
    fingerprint = hashlib.sha256(fingerprint_input.encode("utf-8")).hexdigest()
    
    return fingerprint


def detect_infra_hints(failure_text: Optional[str], log_text: Optional[str] = None) -> List[str]:
    hints = []
    
    combined = (failure_text or "") + "\n" + (log_text or "")
    combined_lower = combined.lower()
    
    network_patterns = [
        r"econnreset",
        r"timeout",
        r"dns",
        r"connection refused",
        r"connection reset",
        r"socket hang up",
    ]
    
    runner_patterns = [
        r"disk full",
        r"oomkilled",
        r"no space left",
        r"agent disconnected",
        r"out of memory",
    ]
    
    session_patterns = [
        r"session not created",
        r"webdriver disconnect",
        r"browser.*crash",
    ]
    
    for pattern in network_patterns:
        if re.search(pattern, combined_lower):
            hints.append("network")
            break
    
    for pattern in runner_patterns:
        if re.search(pattern, combined_lower):
            hints.append("runner")
            break
    
    for pattern in session_patterns:
        if re.search(pattern, combined_lower):
            hints.append("session")
            break
    
    return hints


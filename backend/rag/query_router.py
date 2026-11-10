import re

PROFILE_PATTERNS = {
    "data_analyst": [
        r"\bdata analys", r"\bdata analyst", r"\banalytics\b",
        r"\bpower bi\b", r"\bexcel\b", r"\bdashboard", r"\bmis\b",
        r"\breporting\b", r"\bbusiness intelligence\b"
    ],
    "data_scientist": [
        r"\bdata scien", r"\bmachine learn", r"\bml\b",
        r"\bmodel train", r"\bclassification\b", r"\bregression\b",
        r"\banomaly detection\b", r"\bstatistics\b", r"\bfeature engineering\b"
    ],
    "data_engineer": [
        r"\bdata engineer", r"\bdata pipeline", r"\bdata platform",
        r"\bdatabricks\b", r"\bpyspark\b", r"\bspark sql\b",
        r"\blakehouse\b", r"\betl\b", r"\bwarehouse\b",
        r"\bdelta lake\b", r"\bdistributed processing\b"
    ],
    "genai": [
        r"\bgen.?ai\b", r"\bgenerative ai\b", r"\bllm\b",
        r"\blangchain\b", r"\blanggraph\b", r"\brag\b",
        r"\bprompt engineering\b", r"\bai agent", r"\bfine.?tun"
    ],
}

def resolve_profile(question: str) -> str:
    text = question.lower()
    scores = {
        profile: sum(bool(re.search(pattern, text)) for pattern in patterns)
        for profile, patterns in PROFILE_PATTERNS.items()
    }
    best_profile = max(scores, key=scores.get)
    if scores[best_profile] == 0:
        return "general"
    # For questions mentioning several distinct role families, search all resumes.
    matched = [name for name, score in scores.items() if score > 0]
    if len(matched) > 1:
        return "general"
    return best_profile

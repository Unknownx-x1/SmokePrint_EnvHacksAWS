import re
import sys

def verify_script(script_path):
    with open(script_path, "r", encoding="utf-8") as f:
        text = f.read()

    # Extract the narration section specifically
    narration_section_match = re.search(
        r'## Word-for-Word Narration Script\s*\n(.*?)(?=\n##|\Z)', 
        text, 
        re.DOTALL
    )
    if not narration_section_match:
        print("Could not find '## Word-for-Word Narration Script' section!")
        return False
        
    narration_raw = narration_section_match.group(1)

    narration_lines = []
    for line in narration_raw.splitlines():
        line = line.strip()
        if not line or line.startswith("---"):
            continue
        # Remove markdown bold headers like **[0:00 - 0:20] The Problem**
        clean_line = re.sub(r'^\*?\*?\[\d+:\d+\s*-\s*\d+:\d+\][^*]*\*?\*?:?\s*', '', line)
        if clean_line and not clean_line.startswith("---"):
            narration_lines.append(clean_line)

    narration_text = " ".join(narration_lines)
    # Split into words (words with letters/numbers/symbols)
    words = [w for w in narration_text.split() if any(c.isalnum() for c in w)]
    word_count = len(words)
    print(f"Extracted Narration Word Count: {word_count}")
    print(f"Sample words (first 10): {words[:10]}")
    print(f"Sample words (last 10): {words[-10:]}")

    # Check forbidden words
    forbidden = [
        "live recompute",
        "bedrock",
        "frozen core",
        "regulatory",
        "official",
        "certified",
        "culprit",
        "caught the polluter",
        "vivek vihar",
        "crri",
        "april",
        "+252",
        "+221",
        "148",
        "720",
        "590",
    ]

    lower_text = narration_text.lower()
    errors = []
    for term in forbidden:
        if term in lower_text:
            errors.append(f"Forbidden term found: '{term}'")

    # Specific check for NO2 claiming combustion or co-peaks
    if "no2" in lower_text and ("combustion" in lower_text or "co-peak" in lower_text):
        errors.append("Forbidden claim: NO2 confirming combustion/co-peaks")

    # Range check: 380 - 430 words
    if word_count < 380 or word_count > 430:
        errors.append(f"Word count {word_count} is outside [380, 430]")

    # Check mandatory facts and phrases
    mandatory_terms = [
        ("Gurugram", "Gurugram mention"),
        ("0.600", "0.600 ratio"),
        ("logger fault", "logger fault"),
        ("no dispatch", "no dispatch"),
        ("regional smog", "regional smog"),
        ("180", "180 PM2.5"),
        ("400", "400 PM2.5"),
        ("536", "536 PM10"),
        ("0.75", "0.75 ratio"),
        ("triage list", "triage list"),
        ("Rajghat Thermal Power Station", "Rajghat Thermal Power Station"),
        ("tagged disused in OpenStreetMap", "tagged disused in OpenStreetMap"),
        ("inspection is unlikely to be useful", "inspection is unlikely to be useful"),
        ("simulated plume injections", "simulated plume injections"),
        ("consistency, not real-world accuracy", "consistency not real-world accuracy"),
        ("Replay on AWS", "Replay on AWS"),
        ("replayed", "replayed"),
        ("Strands Agents SDK", "Strands Agents SDK"),
        ("free-tier friendly", "free-tier friendly")
    ]

    for term, desc in mandatory_terms:
        if term.lower() not in lower_text:
            errors.append(f"Missing mandatory concept: {desc} ('{term}')")

    if errors:
        print("VERIFICATION FAILED:")
        for err in errors:
            print(f" - {err}")
        return False
    else:
        print("ALL VERIFICATIONS PASSED!")
        return True

if __name__ == "__main__":
    path = sys.argv[1] if len(sys.argv) > 1 else "docs/pitch/script.md"
    success = verify_script(path)
    sys.exit(0 if success else 1)

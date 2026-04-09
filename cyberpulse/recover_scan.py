"""One-time script to recover truncated analysis.json files."""
import json
import sys

def recover(path):
    with open(path, encoding="utf-8") as f:
        a = json.load(f)

    if "error" not in a:
        print(f"No error in {path}, skipping")
        return

    raw = a.get("raw_response", "")
    if not raw:
        print("No raw_response, cannot recover")
        return

    # Find last complete JSON object entry (ends with `},`)
    # Try progressively smaller cuts
    for delimiter in ["        },\n        {", "    },\n    {", "},\n{"]:
        pos = raw.rfind(delimiter)
        if pos != -1:
            truncated = raw[:pos + 1]  # include the }
            break
    else:
        truncated = raw[:raw.rfind("}") + 1]

    # Close remaining open structure
    stack = []
    in_string = False
    escape_next = False
    for ch in truncated:
        if escape_next:
            escape_next = False
            continue
        if ch == "\\" and in_string:
            escape_next = True
            continue
        if ch == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in "{[":
            stack.append(ch)
        elif ch in "}]":
            if stack:
                stack.pop()

    closer = {"[": "]", "{": "}"}
    closing = "".join(closer[s] for s in reversed(stack))
    repaired = truncated + "\n" + closing

    try:
        parsed = json.loads(repaired)
        print(f"Recovered! Keys: {list(parsed.keys())}")
        print(f"  Bevindingen: {len(parsed.get('bevindingen', []))}")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, ensure_ascii=False, indent=2)
        print(f"  Saved to {path}")
    except json.JSONDecodeError as e:
        print(f"Recovery failed: {e}")
        print(f"  Last 100 chars: {repr(repaired[-100:])}")

if __name__ == "__main__":
    scan_id = sys.argv[1] if len(sys.argv) > 1 else "20260315_161802_01a782cc"
    path = rf"C:\Users\dylan\Desktop\Cybersemester\Ai pentester\autopentest-ai\cyberpulse\data\scans\{scan_id}\analysis.json"
    recover(path)

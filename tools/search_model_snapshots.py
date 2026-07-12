import json

log_path = r"C:\Users\Home0\.gemini\antigravity-ide\brain\cc3b3924-0b55-4122-a468-5400fca5b688\.system_generated\logs\transcript.jsonl"
output_path = r"C:\Users\Home0\.gemini\antigravity-ide\scratch\snapshot_results.txt"

print("Searching transcript.jsonl for bot_opening_play...")
found = []
with open(log_path, "r", encoding="utf-8") as f:
    for line in f:
        obj = json.loads(line)
        content = obj.get("content", "")
        # Check tool calls as well
        tool_calls = str(obj.get("tool_calls", ""))
        combined = content + "\n" + tool_calls
        if "bot_opening_play" in combined:
            step_idx = obj.get("step_index")
            lines = combined.split("\n")
            for idx, l in enumerate(lines):
                if "bot_opening_play" in l:
                    found.append(f"Step {step_idx}, Line {idx}: {l.strip()[:150]}")

with open(output_path, "w", encoding="utf-8") as out:
    out.write("\n".join(found))
print("Done!")

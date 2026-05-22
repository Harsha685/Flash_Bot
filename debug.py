import subprocess, json

result = subprocess.run(
    ["arduino-cli", "board", "list", "--json"],
    capture_output=True, text=True
)
data = json.loads(result.stdout)

for entry in data.get("detected_ports", []):
    port_info = entry.get("port", {})
    props = port_info.get("properties", {})
    vid = props.get("vid", "").lower().replace("0x", "")
    pid = props.get("pid", "").lower().replace("0x", "")
    print(f"vid='{vid}' pid='{pid}'")
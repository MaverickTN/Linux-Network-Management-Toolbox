def validate_config(config):
    problems = []
    # Example: Check top-level keys
    required = ["global_settings", "system_paths", "networks", "known_hosts"]
    for key in required:
        if key not in config:
            problems.append(f"Missing key: {key}")

    # Example: Check host schedules for overlaps
    for host in config.get("known_hosts", []):
        blocks = host.get("schedule_blocks", [])
        times = []
        for b in blocks:
            try:
                s, e = b.split("-")
                s = [int(x) for x in s.split(":")]
                e = [int(x) for x in e.split(":")]
                s = s[0]*60 + s[1]
                e = e[0]*60 + e[1]
                times.append((s, e))
            except Exception:
                problems.append(f"Malformed schedule block '{b}' in {host.get('mac')}")
        # Check for overlaps
        for i in range(len(times)):
            for j in range(i+1, len(times)):
                if max(times[i][0], times[j][0]) < min(times[i][1], times[j][1]):
                    problems.append(f"Overlapping blocks in host {host.get('mac')}")
    return (len(problems) == 0), problems

def repair_config(config):
    ok, problems = validate_config(config)
    fixed = False
    if not ok:
        # Remove overlapping blocks for each host
        for host in config.get("known_hosts", []):
            blocks = host.get("schedule_blocks", [])
            seen = set()
            valid = []
            for b in blocks:
                if b not in seen:
                    valid.append(b)
                    seen.add(b)
            host["schedule_blocks"] = valid
            fixed = True
    return config, fixed

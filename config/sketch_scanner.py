"""
Scans the sketches/ directory and regenerates firmware_manifest.json.
Folder structure must be: sketches/<vendor>/<arch>/<board>/<sketch_name>/<sketch_name>.ino
"""

import os
import json

SKETCHES_DIR = "sketches"
MANIFEST_PATH = "config/firmware_manifest.json"


def _discover_sketches():
    """
    Walks sketches/ and returns {fqbn: {"sketches": [paths]}}
    """
    manifest = {}

    if not os.path.isdir(SKETCHES_DIR):
        return manifest

    for vendor in os.listdir(SKETCHES_DIR):
        vendor_path = os.path.join(SKETCHES_DIR, vendor)
        if not os.path.isdir(vendor_path):
            continue

        for arch in os.listdir(vendor_path):
            arch_path = os.path.join(vendor_path, arch)
            if not os.path.isdir(arch_path):
                continue

            for board in os.listdir(arch_path):
                board_path = os.path.join(arch_path, board)
                if not os.path.isdir(board_path):
                    continue

                fqbn = f"{vendor}:{arch}:{board}"
                sketches = []

                for sketch_name in os.listdir(board_path):
                    sketch_dir = os.path.join(board_path, sketch_name)
                    if not os.path.isdir(sketch_dir):
                        continue

                    ino_file = os.path.join(sketch_dir, f"{sketch_name}.ino")
                    if os.path.isfile(ino_file):
                        sketches.append(ino_file)

                if sketches:
                    manifest[fqbn] = {"sketches": sorted(sketches)}

    return manifest


def update_manifest():
    discovered = _discover_sketches()

    # Preserve any extra metadata from existing manifest (descriptions, versions, etc.)
    existing = {}
    if os.path.isfile(MANIFEST_PATH):
        try:
            with open(MANIFEST_PATH, "r") as f:
                existing = json.load(f)
        except json.JSONDecodeError:
            pass

    # Merge: discovered sketches win, but keep other keys from existing
    merged = {}
    for fqbn in discovered:
        merged[fqbn] = existing.get(fqbn, {})
        merged[fqbn]["sketches"] = discovered[fqbn]["sketches"]

    # Write back
    os.makedirs(os.path.dirname(MANIFEST_PATH), exist_ok=True)
    with open(MANIFEST_PATH, "w") as f:
        json.dump(merged, f, indent=2)

    print(f"[MANIFEST] Updated {MANIFEST_PATH} with {len(merged)} board families.")


if __name__ == "__main__":
    update_manifest()
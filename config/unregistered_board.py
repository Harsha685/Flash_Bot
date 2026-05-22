"""
Remove a user-registered board so it prompts again on next plug.
"""

import json
import os

USER_BOARDS_PATH = "config/user_boards.json"

def unregister(vid: str, pid: str):
    if not os.path.isfile(USER_BOARDS_PATH):
        print("No user boards registered.")
        return

    with open(USER_BOARDS_PATH, "r") as f:
        boards = json.load(f)

    key = f"{vid.lower()}:{pid.lower()}"
    if key in boards:
        del boards[key]
        print(f"Unregistered {key}")
    else:
        print(f"{key} not found in user boards.")

    if boards:
        with open(USER_BOARDS_PATH, "w") as f:
            json.dump(boards, f, indent=2)
    else:
        os.remove(USER_BOARDS_PATH)
        print("No boards left. Removed user_boards.json.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Usage: python -m config.unregister_board <VID> <PID>")
        print("Example: python -m config.unregister_board 10c4 ea60")
        sys.exit(1)
    unregister(sys.argv[1], sys.argv[2])
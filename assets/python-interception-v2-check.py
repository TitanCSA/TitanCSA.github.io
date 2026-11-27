"""Verify the Interception V2 Python wrapper on Windows."""

from argparse import ArgumentParser
from importlib.metadata import version
import json

from interception_v2 import Client


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", action="store_true",
                        help="Open the installed driver context and count device slots with a hardware ID")
    args = parser.parse_args()
    with Client() as client:
        keyboard = client.call("check", {"device": 1})
        mouse = client.call("check", {"device": 11})
        result = {"wheel_version": version("interception-v2"), "slot_1": keyboard, "slot_11": mouse}
        if args.inventory:
            client.call("initialize")
            result["devices_with_hardware_id"] = sum(
                bool(client.call("hardware_id", {"device": slot})["hardware_id"])
                for slot in range(1, 21)
            )
    print(json.dumps(result))


if __name__ == "__main__":
    main()

"""Count active Titan Audio Link playback and recording pairs."""

from argparse import ArgumentParser
from importlib.metadata import version
import json

from titan_audio_link import Client


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--expect-installed", action="store_true",
                        help="Require an active playback and recording pair on the same adapter")
    args = parser.parse_args()
    with Client() as client:
        endpoints = client.call("list")
    directions = {}
    for endpoint in endpoints:
        adapter = endpoint["adapter_instance"]
        if endpoint["titan"] and endpoint["state"] == 1 and adapter:
            directions.setdefault(adapter, set()).add(endpoint["direction"])
    active_pairs = sum({0, 1} <= observed for observed in directions.values())
    print(json.dumps({
        "wheel_version": version("titan-audio-link"),
        "titan_endpoints": len(endpoints),
        "active_pairs": active_pairs,
    }))
    return 1 if args.expect_installed and not active_pairs else 0


if __name__ == "__main__":
    raise SystemExit(main())

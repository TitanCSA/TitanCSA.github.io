"""Read driver status for one of the two specialized Interceptor editions."""

from argparse import ArgumentParser
from importlib import import_module
from importlib.metadata import version
import json
import sys


EDITIONS = ("interceptor-keyboard-mouse", "interceptor-gamepad-controller")


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("edition", choices=EDITIONS)
    edition = parser.parse_args().edition
    sdk = import_module(edition.replace("-", "_"))
    try:
        with sdk.Client() as client:
            info = client.info()
    except sdk.Error as error:
        if error.code != 2:
            raise
        print("Windows 2. Run the demo installer for " + edition + " and restart if requested.",
              file=sys.stderr)
        return 2
    print(json.dumps({
        "wheel_version": version(edition),
        "installed": info.installed,
        "active": info.active,
        "trial_state": info.trial_state,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

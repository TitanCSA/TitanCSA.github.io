# SPDX-License-Identifier: MIT
from argparse import ArgumentParser
from importlib.metadata import version
import json
import sys

from interceptor import Error, Interceptor


def main():
    parser = ArgumentParser(description="Check the combined Interceptor Python SDK.")
    parser.add_argument("--status", action="store_true", help="Read the installed driver's status")
    if not parser.parse_args().status:
        print(version("interceptor-multilang"))
        return 0
    try:
        with Interceptor() as client:
            info = client.info()
    except Error as error:
        if error.code != 2:
            raise
        print(error, file=sys.stderr)
        return 2
    print(json.dumps({
        "installed": info.installed,
        "active": info.active,
        "trial_state": info.trial_state,
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

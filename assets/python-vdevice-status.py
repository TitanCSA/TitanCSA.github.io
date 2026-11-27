"""Read the Vdevice demo driver status from the published Windows Python wheel."""

from importlib.metadata import version
import json
import sys

from vdevice import Client, NativeError


def main():
    try:
        with Client() as client:
            status = client.call("status")
    except NativeError as error:
        if error.code != 2:
            raise
        print("Windows 2. Run VdeviceSetup.exe from the matching demo and restart if requested.",
              file=sys.stderr)
        return 2

    print(json.dumps({
        "wheel_version": version("vdevice"),
        "driver_abi": status["version"],
        "virtual_devices": len(status["devices"]),
        "trial_started": status["trial_started"],
    }))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

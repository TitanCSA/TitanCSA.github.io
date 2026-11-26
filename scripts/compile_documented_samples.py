"""Compile the published developer examples against the current SDK pins."""

from test_first_sdk import run_check


def main():
    for edition, sample, architectures in (
        ("interception-v2", "interception-device-inventory.c", ("x86", "x64")),
        ("vdevice", "vdevice-hid-test.cpp", ("x64",)),
        ("interceptor", "interceptor-input-driver-bindings.cpp", ("x64",)),
        ("interceptor-keyboard-mouse", "interceptor-input-driver-bindings.cpp", ("x64",)),
    ):
        for architecture in architectures:
            print(f"Compiling {sample} with the pinned {edition} SDK ({architecture})", flush=True)
            run_check(edition, architecture, run=False, expect_clean=False, cached_archive=None,
                      verbose=False, compile_sample=sample)


if __name__ == "__main__":
    main()

"""Try the Browser Control SDK on a page served only on this computer."""

from argparse import ArgumentParser
import csv
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import re
import subprocess
from tempfile import TemporaryDirectory
from threading import Thread
import os
import sys

PAGE = b"""<!doctype html><meta charset="utf-8">
<title>Local SDK example</title><h1>Local SDK example</h1>
<label for="name">Name</label><input id="name">
<button type="button" id="save">Save</button><p id="result">Waiting</p>
<script>
const nameField = document.getElementById('name');
document.getElementById('save').onclick = () => {
  const result = document.getElementById('result');
  result.textContent = 'Saved: ' + nameField.value;
  result.dataset.saved = 'true';
};
</script>"""


class PageHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(PAGE)))
        self.end_headers()
        self.wfile.write(PAGE)

    def log_message(self, *_):
        pass


def prepare_private_profile(folder):
    system = Path(os.environ["SystemRoot"]) / "System32"
    identity = subprocess.check_output([str(system / "whoami.exe"), "/user", "/fo", "csv", "/nh"],
                                       encoding="oem", errors="replace")
    account, = csv.reader(identity.splitlines())
    sid = account[-1]
    if not re.fullmatch(r"S-1-(?:[0-9]+-)*[0-9]+", sid):
        raise RuntimeError("Could not read the current Windows account SID.")
    # Windows Python 3.13+ can assign Owner Rights to a new temporary folder.
    # Give the same access directly to the current user on this folder only.
    subprocess.run([str(system / "icacls.exe"), str(folder), "/grant:r", f"*{sid}:(OI)(CI)F",
                    "*S-1-5-18:(OI)(CI)F", "/inheritance:r", "/remove:g", "*S-1-3-4"],
                   check=True, capture_output=True, timeout=15)


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("--installed-client", action="store_true", help="Import the client installed from PyPI")
    options = parser.parse_args()
    app = Path.cwd()
    exe = app / "BrowserControl.exe"
    python_sdk = app / "SDK" / "Python"
    if not exe.is_file():
        raise SystemExit("Open PowerShell in the folder extracted from the complete Browser Control ZIP.")
    if not options.installed_client:
        if not (python_sdk / "browser_control.py").is_file():
            raise SystemExit("The bundled SDK is missing. Extract the complete Browser Control ZIP.")
        sys.path.insert(0, str(python_sdk))
    from browser_control import Browser

    # A private folder under the current Windows user preserves the app's
    # profile permission checks. The test creates its own browser instance.
    private_root = Path(os.environ["LOCALAPPDATA"])
    with TemporaryDirectory(prefix="TitanCSA-BrowserCheck-", dir=private_root, ignore_cleanup_errors=True) as scratch:
        profile = Path(scratch)
        prepare_private_profile(profile)
        with ThreadingHTTPServer(("127.0.0.1", 0), PageHandler) as page:
            server_thread = Thread(target=page.serve_forever, daemon=True)
            server_thread.start()
            try:
                browser = Browser.launch(exe, profile_root=profile / "data",
                                         endpoint=profile / "endpoint.json")
                try:
                    tab = browser.new_tab(f"http://127.0.0.1:{page.server_port}/")
                    tab.wait(selector="#name", state="visible", timeout_ms=5000)
                    tab.fill("Ada", selector="#name")
                    tab.click(selector="#save")
                    tab.wait(selector="#result[data-saved]", state="visible", timeout_ms=5000)
                    result = "Saved: Ada"
                    if tab.evaluate("document.getElementById('result').textContent") != result:
                        raise RuntimeError("The page did not show the expected result.")
                    print(result)
                finally:
                    browser.shutdown()
            finally:
                page.shutdown()
                server_thread.join()


if __name__ == "__main__":
    main()

"""Try the Browser Control SDK on a page served only on this computer."""

from argparse import ArgumentParser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
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
  document.getElementById('result').textContent = 'Saved: ' + nameField.value;
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
        with ThreadingHTTPServer(("127.0.0.1", 0), PageHandler) as page:
            server_thread = Thread(target=page.serve_forever, daemon=True)
            server_thread.start()
            try:
                browser = Browser.launch(exe, profile_root=profile / "data",
                                         endpoint=profile / "endpoint.json")
                try:
                    tab = browser.new_tab(f"http://127.0.0.1:{page.server_port}/")
                    tab.fill("Ada", selector="#name")
                    tab.click(selector="#save")
                    result = "Saved: Ada"
                    if result not in tab.snapshot()["text"]:
                        raise RuntimeError("The page did not show the expected result.")
                    print(result)
                finally:
                    browser.shutdown()
            finally:
                page.shutdown()
                server_thread.join()


if __name__ == "__main__":
    main()

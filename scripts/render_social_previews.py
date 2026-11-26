"""Render project share cards with the portal colours and a local Chromium browser."""
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WIDTH, HEIGHT = 1200, 630

# route: (file stem, product name, first use, visual, language)
PREVIEWS = {
    "projects/interceptor/": (
        "interceptor", "Interceptor", "Filter keyboard, mouse and controller input on Windows.", "input", "en"),
    "projects/interceptor-keyboard-mouse/": (
        "interceptor-keyboard-mouse", "Interceptor Keyboard & Mouse",
        "Remap a specific keyboard or mouse.", "keys", "en"),
    "projects/interceptor-gamepad-controller/": (
        "interceptor-gamepad-controller", "Interceptor Gamepad & Controller",
        "Remap buttons and adjust sticks on Windows.", "controller", "en"),
    "projects/vdevice/": (
        "vdevice", "Vdevice", "Create virtual USB devices from your Windows application.", "usb", "en"),
    "projects/interception-v2/": (
        "interception-v2", "Interception V2", "Use the original Interception C API on Windows.", "code", "en"),
    "guides/titan-audio-link-first-run/": (
        "titan-audio-link", "Titan Audio Link", "Send one app’s sound into another app’s microphone.", "audio", "en"),
    "fr/micro-virtuel-titan-audio-link/": (
        "titan-audio-link-fr", "Titan Audio Link", "Envoie le son d’une application vers un micro virtuel.", "audio", "fr"),
}

CSS = """
* { box-sizing: border-box; }
html, body {
  margin: 0; width: 1200px; height: 630px;
  font-family: "Segoe UI", Arial, sans-serif; color: #152135;
}
body { background: #f3f6fa; border-top: 12px solid #194fd1; padding: 50px 64px 40px; }
.brand { display: flex; align-items: center; gap: 15px; font-size: 29px; font-weight: 720; }
.mark { display: grid; place-items: center; width: 48px; height: 48px; border-radius: 12px; background: #194fd1; color: #fff; }
main { display: grid; grid-template-columns: 1.32fr 1fr; gap: 46px; align-items: center; height: 420px; }
h1 { font-size: 69px; line-height: 1.02; letter-spacing: -3px; margin: 0 0 26px; font-weight: 760; }
h1.long { font-size: 59px; letter-spacing: -2.6px; }
p { font-size: 30px; line-height: 1.3; margin: 0; color: #405574; max-width: 525px; }
footer { color: #50637d; font-size: 23px; }
.scene {
  display: grid; position: relative; place-items: center; width: 100%; height: 325px;
  border: 1px solid #c9d9ed; border-radius: 30px; overflow: hidden;
  background: radial-gradient(circle at 25% 24%, #f8fbff, #e5eeff 78%);
}
.scene::before, .scene::after { content: ""; position: absolute; border: 1px solid #b9cdef; border-radius: 50%; width: 310px; height: 310px; }
.scene::after { width: 245px; height: 245px; }
.icon { position: relative; z-index: 1; }
.keyboard {
  display: grid; grid-template-columns: repeat(7, 1fr); gap: 6px;
  background: #19375f; padding: 14px; border-radius: 16px;
  width: 202px; box-shadow: 0 10px #102c52; transform: rotate(-8deg);
}
.key { display: block; height: 16px; background: #f4f8ff; border-radius: 4px; }
.key:nth-child(9), .key:nth-child(10), .key:nth-child(19) { background: #7fa9f3; }
.mouse {
  width: 55px; height: 91px; margin-left: 18px; border-radius: 30px; border: 7px solid #19375f;
  background: #f6f9ff; transform: rotate(10deg); flex-shrink: 0;
}
.mouse::before { content: ""; display: block; width: 9px; height: 20px; border-radius: 5px; background: #194fd1; margin: 10px auto 0; }
.devices { display: flex; align-items: center; }
.devices .gamepad { transform: scale(.58); position: absolute; bottom: 55px; right: -31px; }
.gamepad {
  position: relative; width: 219px; height: 133px; border-radius: 55px 55px 40px 40px;
  border: 8px solid #19375f; background: #f7faff; box-shadow: 0 11px #19375f;
}
.gamepad::before {
  content: ""; position: absolute; width: 49px; height: 49px; left: 29px; top: 27px; background: #194fd1;
  clip-path: polygon(34% 0, 66% 0, 66% 34%, 100% 34%, 100% 66%, 66% 66%, 66% 100%, 34% 100%, 34% 66%, 0 66%, 0 34%, 34% 34%);
}
.buttons { position: absolute; background: #194fd1; width: 15px; height: 15px; border-radius: 50%; right: 43px; top: 26px; box-shadow: 15px 15px #7497d7, -15px 15px #7497d7, 0 30px #194fd1; }
.analog { position: absolute; bottom: 18px; left: 80px; height: 19px; width: 19px; border-radius: 50%; background: #19375f; box-shadow: 27px 0 #19375f; }
.usb { width: 158px; height: 140px; border: 8px solid #19375f; border-radius: 19px; background: #194fd1; margin-top: 48px; }
.usb::before { content: ""; position: absolute; top: -63px; left: 28px; width: 86px; height: 56px; border: 8px solid #19375f; border-radius: 10px 10px 0 0; background: #f6f9ff; }
.usb::after { content: ""; position: absolute; top: -41px; left: 52px; width: 12px; height: 14px; background: #19375f; box-shadow: 27px 0 #19375f; }
.usb b { color: #fff; position: absolute; inset: 0; display: grid; place-items: center; font-size: 29px; }
.code {
  display: grid; gap: 16px; border-radius: 18px; background: #19375f;
  padding: 31px 34px; color: #fff; font-family: Consolas, monospace;
}
.code b { font-size: 46px; color: #8db7fc; }
.code span { font-size: 24px; letter-spacing: -.6px; }
.wave { display: flex; gap: 7px; align-items: center; margin-right: 25px; }
.bar { display: block; width: 8px; border-radius: 8px; height: var(--height); background: #194fd1; }
.microphone { position: relative; height: 115px; width: 66px; border-radius: 35px; border: 7px solid #19375f; background: #f6faff; }
.microphone::before {
  content: ""; position: absolute; border: solid #19375f; border-width: 0 6px 6px; border-radius: 0 0 39px 39px;
  width: 79px; height: 59px; left: -19px; bottom: -22px;
}
.microphone::after { content: ""; position: absolute; height: 19px; width: 6px; background: #19375f; left: 23px; bottom: -41px; }
"""


def icon(kind):
    keys = '<div class="keyboard">' + '<i class="key"></i>' * 21 + '</div>'
    controller = '<div class="gamepad"><i class="buttons"></i><i class="analog"></i></div>'
    if kind in ("keys", "input"):
        paired = keys + '<div class="mouse"></div>'
        return '<div class="icon devices">' + paired + (controller if kind == "input" else "") + '</div>'
    if kind == "controller":
        return '<div class="icon">' + controller + '</div>'
    if kind == "usb":
        return '<div class="icon usb"><b>USB</b></div>'
    if kind == "code":
        return '<div class="icon code"><b>&lt;C&gt;</b><span>interception.h</span></div>'
    if kind == "audio":
        bars = ''.join(f'<i class="bar" style="--height:{height}px"></i>'
                       for height in (20, 42, 64, 37, 81, 103, 75, 44, 25))
        return '<div class="icon devices"><div class="wave">' + bars + '</div><div class="microphone"></div></div>'
    raise ValueError(f"Unknown preview illustration {kind}")


def card(name, purpose, kind, language):
    heading = ' class="long"' if len(name) >= 27 else ""
    return f"""<!doctype html><html lang="{language}"><meta charset="utf-8"><style>{CSS}</style>
<header class="brand"><span class="mark" aria-hidden="true">T</span>TitanCSA</header>
<main><div><h1{heading}>{escape(name)}</h1><p>{escape(purpose)}</p></div>
<div class="scene" aria-hidden="true">{icon(kind)}</div></main><footer>titancsa.github.io</footer></html>"""


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path="C:/Program Files/Google/Chrome/Application/chrome.exe", headless=True)
        page = browser.new_page(viewport={"width": WIDTH, "height": HEIGHT}, device_scale_factor=1)
        for stem, name, purpose, kind, language in PREVIEWS.values():
            page.set_content(card(name, purpose, kind, language))
            assert page.evaluate("document.documentElement.scrollWidth===1200 && document.documentElement.scrollHeight===630")
            assert page.locator("h1").bounding_box()["height"] <= 202
            output = ROOT / "assets" / f"social-{stem}.png"
            page.screenshot(path=output, animations="disabled")
            assert output.stat().st_size < 200_000
            print(output.name)
        browser.close()


if __name__ == "__main__":
    main()

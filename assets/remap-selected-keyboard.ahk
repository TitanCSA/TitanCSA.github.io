#Requires AutoHotkey v2.0
#SingleInstance Force
#Include Lib\AutoHotInterception.ahk

AHI := AutoHotInterception()
keyboards := Map()
list := ""
for id, device in AHI.GetDeviceList() {
    if device.IsMouse
        continue
    keyboards[id] := true
    list .= Format("`n{}  (VID {:04X} / PID {:04X})", id, device.VID, device.PID)
}
if !keyboards.Count {
    MsgBox("No keyboard was detected. Check the driver and restart if required.")
    ExitApp()
}

selection := InputBox("Enter the keyboard ID observed in the input monitor.`n" list,
    "Select one keyboard")
if selection.Result != "OK"
    ExitApp()
if !RegExMatch(Trim(selection.Value), "^\d{1,3}$") {
    MsgBox("Enter a keyboard ID from the list.")
    ExitApp()
}
keyboard := Integer(Trim(selection.Value))
if !keyboards.Has(keyboard) {
    MsgBox("That ID is not an available keyboard.")
    ExitApp()
}

AHI.SubscribeKey(keyboard, GetKeySC("a"), true, Remap)
TrayTip("A becomes B on keyboard " keyboard ". Press F8 to exit.", "AutoHotInterceptor")
F8::ExitApp()

Remap(state) {
    global AHI, keyboard
    AHI.SendKeyEvent(keyboard, GetKeySC("b"), state)
}

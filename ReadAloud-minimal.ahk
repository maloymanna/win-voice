#Requires AutoHotkey v2.0
#SingleInstance Force

PYTHONW := "C:\Program Files\Python314\pythonw.exe"
SCRIPT  := "C:\Users\a123bc\read-aloud\read-aloud.py"

!1::
{
    ; Release Alt so the script's Ctrl+C is not modified to Alt+Ctrl+C
    Send("{Alt Up}")
    ; Small pause so the key is well and truly up before Python sends its own keys
    Sleep(50)
    ; Normal run: hidden, no console (pythonw)
    Run('"' PYTHONW '" "' SCRIPT '"', , "Hide")
    ; -- Debug version --
    ; If it still fails silently, comment the line above and uncomment below
    ; to flash a console so you can see Python errors / "No text found" messages.
    ; Run('"C:\Program Files\Python314\python.exe" "' SCRIPT '"')
}

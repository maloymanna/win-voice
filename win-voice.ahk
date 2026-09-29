#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk  —  Minimal launcher using Format() for clean quoting
; Hotkey: Alt+1
; Exit codes from Python:
;   0 = success (TTS started or stop signal sent)
;   2 = could not read page text from Edge
;   3 = no readable text found (image PDF or empty page)
;   other = generic error
; ============================================================

!1:: {
    procName := WinGetProcessName("A")
    if (procName != "msedge.exe") {
        TrayTip "Alt-1 pressed but Edge not active", "win-voice"
        return
    }

    pythonExe := "C:\Program Files\Python314\python.exe"
    scriptPath := "C:\Users\myuser\Apps\win-voice\win_voice.py"

    if (!FileExist(pythonExe)) {
        TrayTip "Python not found. Check path.", "win-voice error"
        return
    }
    if (!FileExist(scriptPath)) {
        TrayTip "Script not found. Check path.", "win-voice error"
        return
    }

    hwnd := WinGetID("A")
    ; Use Format with single-quoted format string to avoid quote-escaping hell
    cmd := Format('"{1}" "{2}" --hwnd {3}', pythonExe, scriptPath, hwnd)

    exitCode := RunWait(cmd,, "Hide")

    if (exitCode == 2) {
        TrayTip "Could not read page text from Edge. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode == 3) {
        TrayTip "No readable text found. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode != 0) {
        TrayTip "An error occurred. Check win_voice.log for details.", "win-voice"
    }
}

#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk v24 — Alt+1 text-to-speech
; Supports: Edge, Chrome, Notepad++
; Removed: Notepad (UIA EditControl unreliable on Win11)
;
; Stop toggle: pressing Alt+1 during playback deletes the
; playback.pid file; Python detects this and stops audio.
;
; Focus fix: after stop toggle, sends {Alt Up} and {Esc}
; to prevent browser menubar focus glitch.
; ============================================================

PID_FILE := A_ScriptDir . "\playback.pid"

!1:: {
    ; ---- Stop toggle ----
    if (FileExist(PID_FILE)) {
        FileDelete(PID_FILE)
        Sleep(100)
        ; Prevent browser from keeping Alt focus on "3 dots" menu
        Send "{Alt Up}"
        Sleep(50)
        Send "{Esc}"
        return
    }

    procName := WinGetProcessName("A")

    ; Case-insensitive regex matching for process names
    if (procName ~= "i)^msedge\.exe$") {
        appName := "edge"
    } else if (procName ~= "i)^chrome\.exe$") {
        appName := "chrome"
    } else if (procName ~= "i)^notepad\+\+\.exe$") {
        appName := "notepad++"
    } else {
        TrayTip "Alt-1 pressed but no supported app is active", "win-voice"
        return
    }

    hwnd := WinGetID("A")

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

    ; ---- Capture selection via clipboard (all apps) ----
    selectionFile := A_Temp . "\win_voice_selection.txt"
    if (FileExist(selectionFile)) {
        FileDelete(selectionFile)
    }

    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep(100)
    Send("^c")
    clipAvailable := ClipWait(1.0, 1)

    ; Retry once for slower apps
    if (!clipAvailable) {
        Sleep(200)
        Send("^c")
        clipAvailable := ClipWait(1.0, 1)
    }

    hasText := (clipAvailable && A_Clipboard != "")

    if (hasText) {
        FileAppend(A_Clipboard, selectionFile, "UTF-8")
    }

    A_Clipboard := ClipSaved
    ClipSaved := ""

    ; ---- Build and run Python command (non-blocking) ----
    cmd := Format('"{1}" "{2}" --app {3} --hwnd {4}', pythonExe, scriptPath, appName, hwnd)
    if (hasText) {
        cmd .= Format(' --selection-file "{1}"', selectionFile)
    }

    Run(cmd,, "Hide")
}

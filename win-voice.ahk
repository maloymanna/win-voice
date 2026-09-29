#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk  —  Hybrid: clipboard for selection, UIA for page mode
; Hotkey: Alt+1
; Exit codes from Python:
;   0 = success (TTS started or stop signal sent)
;   2 = could not read page text from Edge (page mode only)
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

    ; ---- Try clipboard selection first (proven working method) ----
    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep(50)
    Send("^c")
    clipAvailable := ClipWait(0.3, 1)

    selectionFile := A_Temp . "\win_voice_selection.txt"
    hasSelection := (clipAvailable && A_Clipboard != "")

    if (hasSelection) {
        ; Selection detected — write to file and pass to Python
        if (FileExist(selectionFile))
            FileDelete(selectionFile)
        FileAppend(A_Clipboard, selectionFile, "UTF-8")
        A_Clipboard := ClipSaved
        ClipSaved := ""
        cmd := Format('"{1}" "{2}" --selection-file "{3}"', pythonExe, scriptPath, selectionFile)
    } else {
        ; No selection — pass HWND for UIA page extraction
        A_Clipboard := ClipSaved
        ClipSaved := ""
        hwnd := WinGetID("A")
        cmd := Format('"{1}" "{2}" --hwnd {3}', pythonExe, scriptPath, hwnd)
    }

    exitCode := RunWait(cmd,, "Hide")

    if (exitCode == 2) {
        TrayTip "Could not read page text from Edge. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode != 0) {
        TrayTip "An error occurred. Check win_voice.log for details.", "win-voice"
    }
}

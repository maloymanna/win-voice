#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk  —  Minimal hotkey launcher for Edge TTS (AHK v2)
; Hotkey: Alt+1
; ============================================================

!1::
{
    ; Verify Edge is the active window
    procName := WinGetProcessName("A")
    if (procName != "msedge.exe") {
        TrayTip "Alt-1 pressed but Edge not active", "win-voice"
        return
    }

    ; Save clipboard and attempt to capture selection
    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep 50
    Send "^c"
    clipAvailable := ClipWait(0.3, 1)

    selectionFile := A_Temp "\win_voice_selection.txt"
    pythonExe := "C:\Program Files\Python314\python.exe"
    scriptPath := "C:\Users\myuser\Apps\win-voice\win_voice.py"

    if (clipAvailable && A_Clipboard != "") {
        ; ---- Text selection detected ----
        if FileExist(selectionFile)
            FileDelete selectionFile
        FileAppend A_Clipboard, selectionFile, "UTF-8"
        A_Clipboard := ClipSaved
        ClipSaved := ""
        cmd := Format('"{1}" "{2}" --selection-file "{3}"', pythonExe, scriptPath, selectionFile)
        Run cmd,, "Hide"
    } else {
        ; ---- No selection ---- pass active window handle
        A_Clipboard := ClipSaved
        ClipSaved := ""
        hwnd := WinGetID("A")
        cmd := Format('"{1}" "{2}" --hwnd {3}', pythonExe, scriptPath, hwnd)
        Run cmd,, "Hide"
    }
}

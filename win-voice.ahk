#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk  —  Corrected AHK v2 with proper quoting
; ============================================================

!1::
{
    procName := WinGetProcessName("A")
    if (procName != "msedge.exe") {
        TrayTip "Alt-1 pressed but Edge not active", "win-voice"
        return
    }

    ; Verify Python and script exist before trying to run
    pythonExe := "C:\Program Files\Python314\python.exe"
    scriptPath := "C:\Users\myuser\Apps\win-voice\win_voice.py"

    if (!FileExist(pythonExe)) {
        MsgBox "Python not found at:`n" . pythonExe, "win-voice error", "Iconx"
        return
    }
    if (!FileExist(scriptPath)) {
        MsgBox "Script not found at:`n" . scriptPath, "win-voice error", "Iconx"
        return
    }

    ; Save clipboard and attempt to capture selection
    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep(50)
    Send("^c")
    clipAvailable := ClipWait(0.3, 1)

    selectionFile := A_Temp . "\win_voice_selection.txt"

    if (clipAvailable && A_Clipboard != "") {
        ; ---- Selection mode ----
        if (FileExist(selectionFile))
            FileDelete(selectionFile)
        FileAppend(A_Clipboard, selectionFile, "UTF-8")
        A_Clipboard := ClipSaved
        ClipSaved := ""
        cmd := "`"" . pythonExe . "`" `"" . scriptPath . "`" --selection-file `"" . selectionFile . "`""
    } else {
        ; ---- Page mode ----
        A_Clipboard := ClipSaved
        ClipSaved := ""
        hwnd := WinGetID("A")
        cmd := "`"" . pythonExe . "`" `"" . scriptPath . "`" --hwnd " . hwnd
    }

    ; For debugging: uncomment the next line to see the exact command string
    ; MsgBox "Command:`n" . cmd, "win-voice debug", "Iconi"

    Run(cmd,, "Hide")
}

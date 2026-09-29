#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk  —  DEBUG VERSION with MsgBox tracing
; ============================================================

!1::
{
    MsgBox "DEBUG: Hotkey fired!", "win-voice debug", "Iconi"

    procName := WinGetProcessName("A")
    MsgBox "DEBUG: Active process = " procName, "win-voice debug", "Iconi"

    if (procName != "msedge.exe") {
        TrayTip "Alt-1 pressed but Edge not active", "win-voice"
        MsgBox "DEBUG: Not Edge. Exiting.", "win-voice debug", "Iconi"
        return
    }

    ; Save clipboard and attempt to capture selection
    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep 50
    Send "^c"
    clipAvailable := ClipWait(0.3, 1)

    MsgBox "DEBUG: clipAvailable = " clipAvailable "`nClipboard = " SubStr(A_Clipboard, 1, 200), "win-voice debug", "Iconi"

    selectionFile := A_Temp "\win_voice_selection.txt"
    pythonExe := "C:\Program Files\Python314\python.exe"
    scriptPath := "C:\Users\myuser\Apps\win-voice\win_voice.py"

    if (clipAvailable && A_Clipboard != "") {
        MsgBox "DEBUG: Selection mode", "win-voice debug", "Iconi"
        if FileExist(selectionFile)
            FileDelete selectionFile
        FileAppend A_Clipboard, selectionFile, "UTF-8"
        A_Clipboard := ClipSaved
        ClipSaved := ""
        cmd := Format('"{1}" "{2}" --selection-file "{3}"', pythonExe, scriptPath, selectionFile)
        MsgBox "DEBUG: About to Run:`n" cmd, "win-voice debug", "Iconi"
        try {
            Run cmd,, "Hide"
            MsgBox "DEBUG: Run command executed successfully.", "win-voice debug", "Iconi"
        } catch Error as e {
            MsgBox "DEBUG: Run FAILED!`n" e.Message "`n" e.Extra, "win-voice debug", "Iconx"
        }
    } else {
        MsgBox "DEBUG: Page mode (no selection)", "win-voice debug", "Iconi"
        A_Clipboard := ClipSaved
        ClipSaved := ""
        hwnd := WinGetID("A")
        cmd := Format('"{1}" "{2}" --hwnd {3}', pythonExe, scriptPath, hwnd)
        MsgBox "DEBUG: About to Run:`n" cmd, "win-voice debug", "Iconi"
        try {
            Run cmd,, "Hide"
            MsgBox "DEBUG: Run command executed successfully.", "win-voice debug", "Iconi"
        } catch Error as e {
            MsgBox "DEBUG: Run FAILED!`n" e.Message "`n" e.Extra, "win-voice debug", "Iconx"
        }
    }
}

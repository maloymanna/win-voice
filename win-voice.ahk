#NoEnv
#SingleInstance Force
SendMode Input
SetWorkingDir %A_ScriptDir%

; ============================================================
; win-voice.ahk  —  Minimal hotkey launcher for Edge TTS
; Hotkey: Alt+1
; ============================================================

!1::
    ; Verify Edge is the active window
    WinGet, procName, ProcessName, A
    if (procName != "msedge.exe") {
        TrayTip, win-voice, Alt-1 pressed but Edge not active, 2, 1
        return
    }

    ; Save clipboard and attempt to capture selection
    ClipSaved := ClipboardAll
    Clipboard := ""
    Sleep, 50
    Send, ^c
    ClipWait, 0.3, 1       ; wait up to 300 ms for any clipboard data

    selectionFile := A_Temp "\win_voice_selection.txt"
    pythonExe := "C:\Program Files\Python314\python.exe"
    scriptPath := "C:\Users\myuser\Apps\win-voice\win_voice.py"

    if (!ErrorLevel && Clipboard != "") {
        ; ---- Text selection detected ----
        FileDelete, %selectionFile%
        FileAppend, %Clipboard%, %selectionFile%, UTF-8
        ; Restore original clipboard
        Clipboard := ClipSaved
        ClipSaved := ""
        ; Launch Python (hidden, non-blocking)
        Run, "%pythonExe%" "%scriptPath%" --selection-file "%selectionFile%",, Hide
    } else {
        ; ---- No selection ---- pass active window handle
        Clipboard := ClipSaved
        ClipSaved := ""
        WinGet, hwnd, ID, A
        Run, "%pythonExe%" "%scriptPath%" --hwnd %hwnd%,, Hide
    }
    return

#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk  —  Alt+1 text-to-speech
; Supports: Edge, Chrome, Notepad, Notepad++
; Reads selected text only. Shows notification if nothing selected.
; ============================================================

!1:: {
    procName := WinGetProcessName("A")
    supported := Map("msedge.exe", true, "chrome.exe", true, "notepad.exe", true, "notepad++.exe", true)

    if (!supported.Has(procName)) {
        TrayTip "Alt-1 pressed but no supported app is active", "win-voice"
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
    appName := StrReplace(procName, ".exe", "")

    ; ---- Notepad++: skip clipboard, let Python use Scintilla API ----
    if (appName == "notepad++") {
        cmd := Format('"{1}" "{2}" --app notepad++ --hwnd {3}', pythonExe, scriptPath, hwnd)
        exitCode := RunWait(cmd,, "Hide")
        if (exitCode == 3) {
            TrayTip "No text selected. Please select text and press Alt+1.", "win-voice"
        } else if (exitCode == 2) {
            TrayTip "Could not read text. Please select text and press Alt+1.", "win-voice"
        } else if (exitCode != 0) {
            TrayTip "An error occurred. Check win_voice.log for details.", "win-voice"
        }
        return
    }

    ; ---- All other apps: capture selection via clipboard ----
    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep(50)
    Send("^c")
    clipAvailable := ClipWait(0.3, 1)

    selectionFile := A_Temp . "\win_voice_selection.txt"
    hasText := (clipAvailable && A_Clipboard != "")

    if (hasText) {
        if (FileExist(selectionFile))
            FileDelete(selectionFile)
        FileAppend(A_Clipboard, selectionFile, "UTF-8")
    }

    A_Clipboard := ClipSaved
    ClipSaved := ""

    cmd := Format('"{1}" "{2}" --app {3} --hwnd {4}', pythonExe, scriptPath, appName, hwnd)
    if (hasText) {
        cmd .= Format(' --selection-file "{1}"', selectionFile)
    }

    exitCode := RunWait(cmd,, "Hide")

    if (exitCode == 3) {
        TrayTip "No text selected. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode == 2) {
        TrayTip "Could not read text. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode != 0) {
        TrayTip "An error occurred. Check win_voice.log for details.", "win-voice"
    }
}

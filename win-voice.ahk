#Requires AutoHotkey v2.0
#SingleInstance Force
SendMode "Input"
SetWorkingDir A_ScriptDir

; ============================================================
; win-voice.ahk v14 — Alt+1 text-to-speech
; Supports: Edge, Chrome, Notepad, Notepad++
; Reads selected text only. Proven clipboard approach from v8.
; ============================================================

LOG_FILE := A_ScriptDir . "\ahk_debug.log"

WriteLog(msg) {
    global LOG_FILE
    timestamp := FormatTime(, "yyyy-MM-dd HH:mm:ss")
    FileAppend(timestamp . "  " . msg . "`n", LOG_FILE)
}

!1:: {
    WriteLog("=== Hotkey pressed ===")

    procName := WinGetProcessName("A")
    WriteLog("Active process: " . procName)

    ; Map exe name to app identifier expected by Python
    appMap := Map(
        "msedge.exe", "edge",
        "chrome.exe", "chrome",
        "notepad.exe", "notepad",
        "notepad++.exe", "notepad++"
    )

    if (!appMap.Has(procName)) {
        TrayTip "Alt-1 pressed but no supported app is active", "win-voice"
        WriteLog("Unsupported app, exiting.")
        return
    }

    appName := appMap[procName]
    hwnd := WinGetID("A")
    WriteLog("App=" . appName . " HWND=" . hwnd)

    pythonExe := "C:\Program Files\Python314\python.exe"
    scriptPath := "C:\Users\myuser\Apps\win-voice\win_voice.py"

    if (!FileExist(pythonExe)) {
        TrayTip "Python not found. Check path.", "win-voice error"
        WriteLog("Python not found: " . pythonExe)
        return
    }
    if (!FileExist(scriptPath)) {
        TrayTip "Script not found. Check path.", "win-voice error"
        WriteLog("Script not found: " . scriptPath)
        return
    }

    ; Always clean up old selection file first
    selectionFile := A_Temp . "\win_voice_selection.txt"
    if (FileExist(selectionFile)) {
        FileDelete(selectionFile)
        WriteLog("Deleted old selection file.")
    }

    ; ---- Notepad++: use Scintilla API, skip clipboard ----
    if (appName == "notepad++") {
        cmd := Format('"{1}" "{2}" --app notepad++ --hwnd {3}', pythonExe, scriptPath, hwnd)
        WriteLog("Notepad++ cmd: " . cmd)
        exitCode := RunWait(cmd,, "Hide")
        WriteLog("Notepad++ exit code: " . exitCode)
        if (exitCode == 3) {
            TrayTip "No text selected. Please select text and press Alt+1.", "win-voice"
        } else if (exitCode == 2) {
            TrayTip "Could not read text. Please select text and press Alt+1.", "win-voice"
        } else if (exitCode != 0) {
            TrayTip "An error occurred. Check win_voice.log for details.", "win-voice"
        }
        return
    }

    ; ---- All other apps: proven clipboard selection capture ----
    ClipSaved := ClipboardAll()
    A_Clipboard := ""
    Sleep(50)
    Send("^c")
    clipAvailable := ClipWait(0.5, 1)

    hasText := (clipAvailable && A_Clipboard != "")
    WriteLog("ClipWait result: " . clipAvailable . "  HasText: " . hasText . "  Len: " . StrLen(A_Clipboard))

    if (hasText) {
        FileAppend(A_Clipboard, selectionFile, "UTF-8")
        WriteLog("Wrote selection file: " . selectionFile . " (" . StrLen(A_Clipboard) . " chars)")
    }

    A_Clipboard := ClipSaved
    ClipSaved := ""

    if (hasText) {
        cmd := Format('"{1}" "{2}" --app {3} --hwnd {4} --selection-file "{5}"', pythonExe, scriptPath, appName, hwnd, selectionFile)
    } else {
        cmd := Format('"{1}" "{2}" --app {3} --hwnd {4}', pythonExe, scriptPath, appName, hwnd)
    }
    WriteLog("Cmd: " . cmd)

    exitCode := RunWait(cmd,, "Hide")
    WriteLog("Exit code: " . exitCode)

    if (exitCode == 3) {
        TrayTip "No text selected. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode == 2) {
        TrayTip "Could not read text. Please select text and press Alt+1.", "win-voice"
    } else if (exitCode != 0) {
        TrayTip "An error occurred. Check win_voice.log for details.", "win-voice"
    }
}

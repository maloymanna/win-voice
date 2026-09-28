#Requires AutoHotkey v2.0
; ReadAloud.ahk - Global hotkey to read aloud selected text
; Place this file anywhere (e.g. Desktop) and double-click to run it.
; Press Alt+1 to read the selected text in the active window.
; Press Alt+1 again while reading to stop.

; ============================================================================
; CONFIGURATION - adjust these paths to match your system
; ============================================================================
PYTHONW := "C:\Program Files\Python314\pythonw.exe"
SCRIPT  := "C:\Users\a123bc\read-aloud\read-aloud.py"

; ============================================================================
; HOTKEY
; ============================================================================
!1::
{
    ; If pythonw.exe is not found at the expected location, try to locate it
    if (!FileExist(PYTHONW)) {
        ; Try common install locations
        candidates := [
            A_AppData "\..\Local\Programs\Python\Python314\pythonw.exe",
            A_AppData "\..\Local\Microsoft\WindowsApps\pythonw.exe",
            "C:\Users\" A_UserName "\AppData\Local\Programs\Python\Python314\pythonw.exe",
            "C:\Users\" A_UserName "\AppData\Local\Microsoft\WindowsApps\pythonw.exe",
        ]
        for cand in candidates {
            if (FileExist(cand)) {
                PYTHONW := cand
                break
            }
        }
    }

    if (!FileExist(PYTHONW)) {
        MsgBox("Could not find pythonw.exe. Please set the PYTHONW path in ReadAloud.ahk.")
        return
    }

    if (!FileExist(SCRIPT)) {
        MsgBox("Could not find read-aloud.py. Please set the SCRIPT path in ReadAloud.ahk.")
        return
    }

    ; Run the script hidden (no console window).
    ; Using pythonw ensures zero console windows appear,
    ; so focus stays on the browser/editor where text is selected.
    Run('"' PYTHONW '" "' SCRIPT '"', , "Hide")
}

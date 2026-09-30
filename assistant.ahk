; ---------- Voice Assistant ----------
#Requires AutoHotkey v2.0
RunVoice(mode) {
    py := "C:\Program Files\Python314\python.exe"
    script := "C:\Users\Apps\voiceassistant\assistant.py"
    Run('"' py '" "' script '" ' mode, , "Hide")
}
#w::RunVoice("echo")
#c::RunVoice("stt")
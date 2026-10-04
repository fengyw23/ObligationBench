from pathlib import Path
p=Path('/app/src/voice-broadcast/models/VoiceBroadcastPlayback.ts')
s=p.read_text()
start=s.index('    private updateLiveness(): void {')
end=s.index('    public get currentState()',start)
s=s[:start]+'    private updateLiveness(): void {\n        switch (this.infoState) {\n            case VoiceBroadcastInfoState.Started:\n            case VoiceBroadcastInfoState.Resumed:\n                this.setLiveness("live");\n                break;\n            case VoiceBroadcastInfoState.Paused:\n                this.setLiveness("grey");\n                break;\n            default:\n                this.setLiveness("not-live");\n        }\n    }\n\n'+s[end:]
old='        if (!Object.values(VoiceBroadcastInfoState).includes(state)) {\n            // Do not handle unknown voice broadcast states\n            return;\n        }\n\n'
assert old in s
s=s.replace(old,'',1)
p.write_text(s)
print('Broadcast liveness now follows info state; unknown states default to not-live')

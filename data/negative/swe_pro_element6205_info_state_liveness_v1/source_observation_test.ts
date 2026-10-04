import { VoiceBroadcastPlayback } from "../../../src/voice-broadcast/models/VoiceBroadcastPlayback";
test("observes the current info liveness mapping", () => {
    for (const infoState of ["started", "resumed", "paused", "stopped", "future-state", undefined]) {
        const subject = Object.create(VoiceBroadcastPlayback.prototype);
        subject.infoState = infoState;
        subject.state = 0;
        subject.liveness = "not-live";
        subject.emit = jest.fn();
        subject.updateLiveness();
        console.log("Info liveness observed:", infoState, subject.getLiveness());
    }
});

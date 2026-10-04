import { VoiceBroadcastPlayback } from "../../../src/voice-broadcast/models/VoiceBroadcastPlayback";

jest.mock("../../../src/events/RelationsHelper", () => ({
    RelationsHelper: class {
        getCurrent() { return []; }
        on() { return this; }
        async emitFetchCurrent() { return; }
        destroy() { return; }
    },
    RelationsHelperEvent: { Add: "add" },
}));

describe("Broadcast info state liveness", () => {
    test.each([
        ["started", "live"], ["resumed", "live"], ["paused", "grey"],
        ["stopped", "not-live"], ["future-state", "not-live"], [undefined, "not-live"],
    ])("%s produces %s regardless of playback progress", (infoState, expected) => {
        const subject = Object.create(VoiceBroadcastPlayback.prototype);
        subject.infoState = infoState;
        subject.liveness = "not-live";
        subject.emit = jest.fn();
        subject.updateLiveness();
        expect(subject.getLiveness()).toBe(expected);
        subject.state = 0;
        subject.currentlyPlaying = null;
        subject.updateLiveness();
        expect(subject.getLiveness()).toBe(expected);
    });

    test("new info transitions update liveness including undefined and unknown states", async () => {
        const initialEvent = { getTs: () => 0, getContent: () => ({ state: "started" }), on: jest.fn() };
        const subject = new VoiceBroadcastPlayback(initialEvent as any, {} as any) as any;
        let timestamp = 0;
        for (const [state, expected] of [
            ["started", "live"], ["paused", "grey"], ["resumed", "live"],
            ["unknown", "not-live"], ["started", "live"], [undefined, "not-live"],
            ["stopped", "not-live"],
        ]) {
            timestamp++;
            const ts = timestamp;
            subject.addInfoEvent({ getTs: () => ts, getContent: () => ({ state }) });
            expect(subject.getLiveness()).toBe(expected);
        }
        await Promise.resolve();
        await Promise.resolve();
        subject.destroy();
    });
});

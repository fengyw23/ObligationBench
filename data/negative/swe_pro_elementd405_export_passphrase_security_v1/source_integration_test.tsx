import React from "react";
import { fireEvent, render, waitFor, cleanup } from "@testing-library/react";
import { Crypto } from "@peculiar/webcrypto";
import nodeCrypto from "crypto";
import FileSaver from "file-saver";
let ExportE2eKeysDialog: typeof import("../src/async-components/views/dialogs/security/ExportE2eKeysDialog").default;
import { createTestClient } from "./test-utils";
import { MatrixClientPeg } from "../src/MatrixClientPeg";
import SdkConfig from "../src/SdkConfig";
let decryptMegolmKeyFile: typeof import("../src/utils/MegolmExportEncryption").decryptMegolmKeyFile;

jest.mock("file-saver", () => ({ saveAs: jest.fn() }));
const strong = "mT7!gX9$uP2#dR6@vN4&kL8";
const keys = [
    { room_id: "!synthetic:example.org", session_id: "fixture-session", session_key: "fixture-sensitive-room-key" },
];

beforeEach(() => {
    Object.defineProperty(window, "crypto", {
        configurable: true,
        value: {
            getRandomValues: (a: Uint8Array) => nodeCrypto.randomFillSync(a),
            subtle: new Crypto().subtle,
        },
    });
    ExportE2eKeysDialog = require("../src/async-components/views/dialogs/security/ExportE2eKeysDialog").default;
    decryptMegolmKeyFile = require("../src/utils/MegolmExportEncryption").decryptMegolmKeyFile;
    jest.clearAllMocks();
});
afterEach(async () => {
    await new Promise((r) => setTimeout(r, 300));
    cleanup();
    jest.restoreAllMocks();
});

function setup() {
    const client = createTestClient();
    jest.spyOn(MatrixClientPeg, "get").mockReturnValue(client);
    client.exportRoomKeys = jest.fn().mockResolvedValue(keys);
    client.getUserIdLocalpart = jest.fn().mockReturnValue("fixture-user");
    const finished = jest.fn();
    const view = render(<ExportE2eKeysDialog matrixClient={client} onFinished={finished} />);
    const first = view.getByLabelText("Enter passphrase") as HTMLInputElement;
    const second = view.getByLabelText("Confirm passphrase") as HTMLInputElement;
    const submit = () => fireEvent.submit(first.closest("form")!);
    const fill = (a: string, b: string) => {
        fireEvent.change(first, { target: { value: a } });
        fireEvent.change(second, { target: { value: b } });
    };
    return { ...view, client, finished, first, second, submit, fill };
}

test.each([
    ["empty", "", "", "Passphrase must not be empty"],
    ["weak", "password", "password", "Please choose a stronger passphrase"],
    ["mismatch", strong, strong + "x", "Passphrases must match"],
])("rejects %s before requesting room keys", async (_, a, b, error) => {
    const v = setup();
    v.fill(a, b);
    v.submit();
    await waitFor(() => expect(v.getByText(error)).toBeTruthy());
    expect(v.client.exportRoomKeys).not.toHaveBeenCalled();
    expect(FileSaver.saveAs).not.toHaveBeenCalled();
    expect(v.finished).not.toHaveBeenCalled();
    console.log(`REJECT ${_}: key requests=0 saved files=0`);
});

test("shows real-time native strength feedback and rejects unsafe override", async () => {
    jest.spyOn(SdkConfig, "get").mockImplementation((key: string) =>
        key === "dangerously_allow_unsafe_and_insecure_passwords" ? true : undefined,
    );
    const v = setup();
    fireEvent.focus(v.first);
    v.fill("password", "password");
    await waitFor(() => expect(document.querySelector("progress")?.getAttribute("value")).toBe("0"));
    v.submit();
    await waitFor(() => expect(v.getByText("Please choose a stronger passphrase")).toBeTruthy());
    expect(v.client.exportRoomKeys).not.toHaveBeenCalled();
    console.log("NATIVE STRENGTH password score=0; unsafe override still blocked for key export");
});

test("encrypts a strong matching export once and clears both fields before completion", async () => {
    const v = setup();
    v.fill(strong, strong);
    v.finished.mockImplementation((ok) => {
        expect(ok).toBe(true);
        expect(v.first.value).toBe("");
        expect(v.second.value).toBe("");
    });
    v.submit();
    v.submit();
    await waitFor(() => expect(v.finished).toHaveBeenCalledTimes(1), { timeout: 10000 });
    expect(v.client.exportRoomKeys).toHaveBeenCalledTimes(1);
    expect(FileSaver.saveAs).toHaveBeenCalledTimes(1);
    const [blob, name] = (FileSaver.saveAs as jest.Mock).mock.calls[0];
    expect(name).toBe("element-keys.txt");
    const bytes = await new Promise<ArrayBuffer>((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result as ArrayBuffer);
        reader.onerror = reject;
        reader.readAsArrayBuffer(blob);
    });
    const text = await decryptMegolmKeyFile(bytes, strong);
    expect(JSON.parse(text)).toEqual(keys);
    await expect(decryptMegolmKeyFile(bytes, "password")).rejects.toMatchObject({ message: expect.any(String) });
    console.log(
        "ENCRYPTED EXPORT correct passphrase round-trip=exact fixture keys; wrong passphrase rejected; key requests=1 saves=1; both fields empty before finished=true",
    );
});

test("cancel discards both sensitive input values without export", () => {
    const v = setup();
    v.fill(strong, strong);
    v.finished.mockImplementation((ok) => {
        expect(ok).toBe(false);
        expect(v.first.value).toBe("");
        expect(v.second.value).toBe("");
    });
    fireEvent.click(v.getByText("Cancel"));
    expect(v.finished).toHaveBeenCalledWith(false);
    expect(v.client.exportRoomKeys).not.toHaveBeenCalled();
    expect(FileSaver.saveAs).not.toHaveBeenCalled();
    console.log("CANCEL fields empty; key requests=0 saves=0");
});

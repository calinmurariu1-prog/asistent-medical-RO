import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import ts from "typescript";

async function setup({ fail = false, writeFail = false } = {}) {
  const calls = [];
  globalThis.__exportMocks = {
    Capacitor: { isNativePlatform: () => true },
    filesystem: {
      Directory: { Cache: "CACHE" },
      Filesystem: {
        mkdir: async () => { throw Error("already exists"); },
        readdir: async () => ({ files: [
          { name: `1000000000000-00000000-0000-0000-0000-000000000000` },
          { name: `${Date.now()}-00000000-0000-0000-0000-000000000000` },
          { name: "unrelated-folder" }, { name: "../outside" },
        ] }),
        rmdir: async args => calls.push(["delete", args]),
        writeFile: async args => {
          calls.push(["write", args]);
          if (writeFail) throw Error("secret native file path");
          return { uri: "file://private/cache/export.json" };
        },
      },
    },
    share: { Share: {
      canShare: async () => ({ value: true }),
      share: async args => { calls.push(["share", args]); if (fail) throw Error("secret canceled"); },
    } },
  };
  const source = readFileSync(new URL("../src/lib/file-export.ts", import.meta.url), "utf8")
    .replace('import { Capacitor } from "@capacitor/core";', 'const {Capacitor} = globalThis.__exportMocks;')
    .replace('import("@capacitor/filesystem")', 'Promise.resolve(globalThis.__exportMocks.filesystem)')
    .replace('import("@capacitor/share")', 'Promise.resolve(globalThis.__exportMocks.share)');
  const code = ts.transpileModule(source, { compilerOptions: {
    target: ts.ScriptTarget.ES2022, module: ts.ModuleKind.ES2022,
  } }).outputText;
  const module = await import("data:text/javascript;base64," +
    Buffer.from(code + `\n//${Math.random()}`).toString("base64"));
  return { ...module, calls };
}

test("native export writes exact bytes privately, shares only URI and expires old owned folders", async () => {
  const { saveExport, calls } = await setup();
  const bytes = new Uint8Array([0, 255, 128, 65]);
  assert.match(await saveExport(new Blob([bytes]), "../../patient.json"), /salvarea nu este confirmată/);
  assert.equal(calls.filter(c => c[0] === "delete").length, 1);
  const written = calls.find(c => c[0] === "write")[1];
  assert.match(written.path, /^medical-exports\/\d{13}-[0-9a-f-]{36}\/export.json$/);
  assert.equal(written.directory, "CACHE");
  assert.deepEqual(Buffer.from(written.data, "base64"), Buffer.from(bytes));
  assert.deepEqual(calls.at(-1)[1].files, ["file://private/cache/export.json"]);
  assert.equal(calls.at(-1)[0], "share"); // Do not delete before recipient has read.
});

test("native cancellation and write errors are visible without private path leakage", async () => {
  for (const options of [{ fail: true }, { writeFail: true }]) {
    const { saveExport, calls } = await setup(options);
    await assert.rejects(saveExport(new Blob(["synthetic"]), "test.json"), error => {
      assert.match(error.message, /nu a fost confirmat/);
      assert.doesNotMatch(error.message, /secret/); return true;
    });
    if (options.writeFail) assert.equal(calls.some(c => c[0] === "share"), false);
  }
});

test("native size limit prevents writing and sharing", async () => {
  const { saveExport, calls } = await setup();
  await assert.rejects(saveExport({ size: 26 * 1024 * 1024 }, "test.json"), /25 MB/);
  assert.equal(calls.length, 0);
});

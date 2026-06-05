/**
 * CIRCUITPY firmware deploy — browser tool using File System Access API.
 * Copy semantics aligned with tools/utils.py (copy_firmware_tree / update settings).
 */

const IGNORE_NAMES = new Set([
  ".git",
  ".DS_Store",
  "__pycache__",
  ".gitignore",
  ".idea",
  ".vscode",
]);

const IGNORE_SUFFIXES = [".pyc", ".pyo"];
const SETTINGS_FILES = ["settings.toml", "startup.toml"];
const MARKER_CODE = "code.py";
const MARKER_BOOT = "boot.toml";

/** @type {FileSystemDirectoryHandle | null} */
let sourceHandle = null;
/** @type {FileSystemDirectoryHandle | null} */
let destHandle = null;
/** @type {{ path: string, file: File }[] | null} */
let sourceFileList = null;

const compat = detectCompatibility();

const els = {
  compatPanel: document.getElementById("compat-panel"),
  btnPickSource: document.getElementById("btn-pick-source"),
  btnPickDest: document.getElementById("btn-pick-dest"),
  btnDeploy: document.getElementById("btn-deploy"),
  btnDownloadZip: document.getElementById("btn-download-zip"),
  sourceSummary: document.getElementById("source-summary"),
  destSummary: document.getElementById("dest-summary"),
  destValidation: document.getElementById("dest-validation"),
  sourceFallbackLabel: document.getElementById("source-fallback-label"),
  inputSourceDir: document.getElementById("input-source-dir"),
  optPreserveSettings: document.getElementById("opt-preserve-settings"),
  optInstallToolsSettings: document.getElementById("opt-install-tools-settings"),
  progressPanel: document.getElementById("progress-panel"),
  progressBar: document.getElementById("progress-bar"),
  progressText: document.getElementById("progress-text"),
  log: document.getElementById("log"),
  reportPanel: document.getElementById("report-panel"),
  reportStats: document.getElementById("report-stats"),
  reportNote: document.getElementById("report-note"),
};

init();

function init() {
  renderCompatPanel();
  els.btnPickSource.disabled = !compat.canPickDirectories;
  els.btnPickDest.disabled = !compat.canWriteToDevice;
  els.btnDeploy.disabled = !compat.canWriteToDevice;
  els.btnDownloadZip.disabled = false;

  if (!compat.canPickDirectories) {
    els.sourceFallbackLabel.classList.remove("hidden");
  }

  els.btnPickSource.addEventListener("click", pickSourceDirectory);
  els.btnPickDest.addEventListener("click", pickDestDirectory);
  els.btnDeploy.addEventListener("click", runDeploy);
  els.btnDownloadZip.addEventListener("click", downloadFirmwareZip);
  els.inputSourceDir.addEventListener("change", onSourceDirUpload);

  updateDeployButtonState();
}

/**
 * @returns {{
 *   canPickDirectories: boolean,
 *   canWriteToDevice: boolean,
 *   browserName: string,
 *   level: 'ok' | 'warn' | 'err',
 *   messages: string[],
 * }}
 */
function detectCompatibility() {
  const ua = navigator.userAgent;
  let browserName = "Unknown browser";
  if (/Edg\//.test(ua)) browserName = "Microsoft Edge";
  else if (/Chrome\//.test(ua) && !/Edg\//.test(ua)) browserName = "Google Chrome";
  else if (/OPR\//.test(ua) || /Opera/.test(ua)) browserName = "Opera";
  else if (/Firefox\//.test(ua)) browserName = "Firefox";
  else if (/Safari\//.test(ua) && !/Chrome/.test(ua)) browserName = "Safari";

  const canPick =
    typeof window.showDirectoryPicker === "function" &&
    typeof FileSystemHandle !== "undefined";
  const canWrite = canPick;
  const messages = [];

  if (canWrite) {
    messages.push(
      `${browserName} supports folder pickers and writing to CIRCUITPY.`,
    );
    messages.push(
      "Serve this page over http://localhost (see README) — opening index.html as file:// may block APIs.",
    );
    if (/Brave/.test(ua)) {
      messages.push(
        "Brave may require enabling the File System Access API in brave://flags.",
      );
    }
    return {
      canPickDirectories: true,
      canWriteToDevice: true,
      browserName,
      level: "ok",
      messages,
    };
  }

  const hasDirUpload =
    typeof HTMLInputElement !== "undefined" &&
    "webkitdirectory" in document.createElement("input");

  if (hasDirUpload) {
    messages.push(
      `${browserName} cannot write directly to CIRCUITPY (no showDirectoryPicker).`,
    );
    messages.push(
      "You can still pick a source folder and download a ZIP to copy manually.",
    );
    messages.push(
      "For full deploy (including settings preserve), use Chrome or Edge on desktop.",
    );
    return {
      canPickDirectories: false,
      canWriteToDevice: false,
      browserName,
      level: "warn",
      messages,
    };
  }

  messages.push(
    `${browserName} does not support the APIs needed for this tool.`,
  );
  messages.push("Use Chrome or Edge on desktop, or tools/deploy.ipynb.");
  return {
    canPickDirectories: false,
    canWriteToDevice: false,
    browserName,
    level: "err",
    messages,
  };
}

function renderCompatPanel() {
  const { level, browserName, messages } = compat;
  els.compatPanel.className = `panel compat ${level}`;
  els.compatPanel.innerHTML = `
    <strong>Browser: ${escapeHtml(browserName)}</strong>
    <ul>${messages.map((m) => `<li>${escapeHtml(m)}</li>`).join("")}</ul>
  `;
}

async function pickSourceDirectory() {
  try {
    const handle = await window.showDirectoryPicker({ mode: "read" });
    const ok = await validateSourceHandle(handle);
    if (!ok) return;
    sourceHandle = handle;
    sourceFileList = null;
    els.sourceSummary.textContent = `Source: ${handle.name}/ (${await countFilesInTree(handle)} files)`;
    updateDeployButtonState();
    logLine(`Selected source: ${handle.name}`);
  } catch (e) {
    if (e.name !== "AbortError") logLine(`Source pick failed: ${e.message}`, true);
  }
}

async function onSourceDirUpload(ev) {
  const files = /** @type {FileList} */ (ev.target.files);
  if (!files?.length) return;
  const list = [];
  let hasCodePy = false;
  for (const file of files) {
    const path = file.webkitRelativePath || file.name;
    const rel = path.includes("/") ? path.split("/").slice(1).join("/") : path;
    if (rel === MARKER_CODE || rel.endsWith(`/${MARKER_CODE}`)) hasCodePy = true;
    if (shouldSkipName(path.split("/").pop() || path)) continue;
    const norm = rel.replace(/^\/+/, "");
    if (!norm || shouldSkipPath(norm)) continue;
    list.push({ path: norm, file });
  }
  if (!hasCodePy) {
    alert(`Selected folder must contain ${MARKER_CODE} at the top level.`);
    return;
  }
  sourceHandle = null;
  sourceFileList = list;
  els.sourceSummary.textContent = `Source (upload): ${list.length} files`;
  updateDeployButtonState();
  logLine(`Source from folder upload: ${list.length} files`);
}

async function pickDestDirectory() {
  try {
    const handle = await window.showDirectoryPicker({ mode: "readwrite" });
    destHandle = handle;
    els.destSummary.textContent = `Destination: ${handle.name}/`;
    await validateDestination(handle);
    updateDeployButtonState();
    logLine(`Selected destination: ${handle.name}`);
  } catch (e) {
    if (e.name !== "AbortError") logLine(`Destination pick failed: ${e.message}`, true);
  }
}

async function validateSourceHandle(handle) {
  try {
    await handle.getFileHandle(MARKER_CODE);
    return true;
  } catch {
    alert(
      `“${handle.name}” does not contain ${MARKER_CODE}. Select the repo firmware/ folder.`,
    );
    return false;
  }
}

async function validateDestination(handle) {
  const el = els.destValidation;
  el.hidden = false;
  let hasCode = false;
  let hasBoot = false;
  try {
    await handle.getFileHandle(MARKER_CODE);
    hasCode = true;
  } catch {
    /* missing */
  }
  try {
    await handle.getFileHandle(MARKER_BOOT);
    hasBoot = true;
  } catch {
    /* missing */
  }

  if (hasBoot) {
    el.className = "validation ok";
    el.textContent =
      "Update path: boot.toml found — existing board (settings can be preserved).";
  } else if (hasCode) {
    el.className = "validation warn";
    el.textContent =
      "code.py present but no boot.toml — treated as new-board style copy.";
  } else {
    el.className = "validation warn";
    el.textContent =
      "No code.py on device yet — ensure this is the CIRCUITPY root.";
  }
}

function updateDeployButtonState() {
  const hasSource = sourceHandle != null || (sourceFileList?.length ?? 0) > 0;
  els.btnDeploy.disabled = !compat.canWriteToDevice || !hasSource || !destHandle;
  els.btnDownloadZip.disabled = !hasSource;
}

function shouldSkipName(name) {
  if (IGNORE_NAMES.has(name)) return true;
  if (name.toLowerCase() === "readme.md") return true;
  return IGNORE_SUFFIXES.some((s) => name.endsWith(s));
}

function shouldSkipPath(relPath) {
  const parts = relPath.split("/");
  return parts.some((p) => shouldSkipName(p));
}

/**
 * Collect copy jobs: top-level entries of src, mirroring utils._collect_firmware_copy_jobs.
 * @param {FileSystemDirectoryHandle} srcDir
 * @returns {Promise<{ relPath: string, getBlob: () => Promise<Blob> }[]>}
 */
async function collectJobsFromHandle(srcDir) {
  const jobs = [];

  async function walkDir(dirHandle, prefix) {
    for await (const [name, handle] of dirHandle.entries()) {
      if (shouldSkipName(name)) continue;
      const rel = prefix ? `${prefix}/${name}` : name;
      if (handle.kind === "directory") {
        await walkDir(handle, rel);
      } else {
        jobs.push({
          relPath: rel,
          getBlob: async () => {
            const fh = /** @type {FileSystemFileHandle} */ (handle);
            const f = await fh.getFile();
            return f;
          },
        });
      }
    }
  }

  const entries = [];
  for await (const entry of srcDir.entries()) {
    entries.push(entry);
  }
  entries.sort((a, b) => a[0].localeCompare(b[0], undefined, { sensitivity: "base" }));

  for (const [name, handle] of entries) {
    if (shouldSkipName(name)) continue;
    if (handle.kind === "directory") {
      await walkDir(handle, name);
    } else {
      const fh = /** @type {FileSystemFileHandle} */ (handle);
      jobs.push({
        relPath: name,
        getBlob: () => fh.getFile(),
      });
    }
  }
  return jobs;
}

function collectJobsFromFileList(list) {
  return list
    .filter(({ path }) => !shouldSkipPath(path))
    .map(({ path, file }) => ({
      relPath: path,
      getBlob: async () => file,
    }));
}

async function getAllJobs() {
  if (sourceHandle) return collectJobsFromHandle(sourceHandle);
  if (sourceFileList) return collectJobsFromFileList(sourceFileList);
  throw new Error("No firmware source selected.");
}

/**
 * @param {FileSystemDirectoryHandle} root
 * @param {string} relPath
 */
async function writeFileToDest(root, relPath, blob) {
  const parts = relPath.split("/");
  const fileName = parts.pop();
  let dir = root;
  for (const part of parts) {
    dir = await dir.getDirectoryHandle(part, { create: true });
  }
  const fileHandle = await dir.getFileHandle(fileName, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(blob);
  await writable.close();
}

/**
 * @param {FileSystemDirectoryHandle} root
 * @param {string} name
 */
async function readFileBytes(root, name) {
  try {
    const fh = await root.getFileHandle(name);
    const file = await fh.getFile();
    return new Uint8Array(await file.arrayBuffer());
  } catch {
    return null;
  }
}

/**
 * @param {FileSystemDirectoryHandle} root
 * @param {string} name
 * @param {Uint8Array} data
 */
async function writeFileBytes(root, name, data) {
  const fh = await root.getFileHandle(name, { create: true });
  const writable = await fh.createWritable();
  await writable.write(data);
  await writable.close();
}

async function fileExists(root, name) {
  try {
    await root.getFileHandle(name);
    return true;
  } catch {
    return false;
  }
}

async function countFilesInTree(dirHandle) {
  const jobs = await collectJobsFromHandle(dirHandle);
  return jobs.length;
}

async function runDeploy() {
  if (!destHandle) return;
  els.progressPanel.classList.remove("hidden");
  els.reportPanel.classList.add("hidden");
  els.log.textContent = "";
  els.progressBar.value = 0;

  const preserve = els.optPreserveSettings.checked;
  const stats = { copied: 0, skipped: 0, failed: 0, restored: 0 };

  try {
    const jobs = await getAllJobs();
    const total = jobs.length;
    els.progressBar.max = total;

    const backups = {};
    if (preserve) {
      for (const name of SETTINGS_FILES) {
        const data = await readFileBytes(destHandle, name);
        if (data) {
          backups[name] = data;
          logLine(`Backed up ${name} (${data.byteLength} bytes)`);
        }
      }
    }

    const skipSettingsDuringCopy =
      preserve && Object.keys(backups).length > 0;

    for (let i = 0; i < jobs.length; i++) {
      const { relPath, getBlob } = jobs[i];
      els.progressText.textContent = `${i + 1} / ${total}: ${relPath}`;
      els.progressBar.value = i + 1;

      const base = relPath.split("/").pop();
      if (
        skipSettingsDuringCopy &&
        SETTINGS_FILES.includes(base) &&
        backups[base]
      ) {
        stats.skipped++;
        continue;
      }

      try {
        const blob = await getBlob();
        await writeFileToDest(destHandle, relPath, blob);
        stats.copied++;
        if ((i + 1) % 25 === 0 || i === total - 1) {
          logLine(`Copied ${i + 1}/${total} …`);
        }
      } catch (e) {
        stats.failed++;
        logLine(`FAILED ${relPath}: ${e.message}`, true);
      }
    }

    if (preserve && Object.keys(backups).length) {
      for (const [name, data] of Object.entries(backups)) {
        await writeFileBytes(destHandle, name, data);
        stats.restored++;
        logLine(`Restored ${name}`);
      }
    }

    if (els.optInstallToolsSettings.checked) {
      await tryInstallBundledSettings();
    }

    showReport(stats, total);
    logLine("Deploy finished. Eject CIRCUITPY safely before unplugging.");
  } catch (e) {
    logLine(`Deploy aborted: ${e.message}`, true);
    alert(e.message);
  }
}

async function tryInstallBundledSettings() {
  try {
    const res = await fetch("../settings.toml");
    if (!res.ok) {
      logLine("tools/settings.toml not available from this server path.", true);
      return;
    }
    const text = await res.text();
    const blob = new Blob([text], { type: "application/toml" });
    await writeFileToDest(destHandle, "settings.toml", blob);
    logLine("Installed default tools/settings.toml onto device.");
  } catch (e) {
    logLine(`Could not install tools/settings.toml: ${e.message}`, true);
  }
}

function showReport(stats, total) {
  els.reportPanel.classList.remove("hidden");
  els.reportStats.innerHTML = `
    <dt>Files planned</dt><dd>${total}</dd>
    <dt>Copied</dt><dd>${stats.copied}</dd>
    <dt>Skipped (preserved settings)</dt><dd>${stats.skipped}</dd>
    <dt>Failed</dt><dd>${stats.failed}</dd>
    <dt>Settings restored</dt><dd>${stats.restored}</dd>
  `;
  els.reportNote.textContent =
    stats.failed === 0
      ? "Copy completed. Safely eject the CIRCUITPY volume before disconnecting USB."
      : "Some files failed — retry after closing serial monitors and ejecting other apps using the port.";
}

async function downloadFirmwareZip() {
  els.progressPanel.classList.remove("hidden");
  els.log.textContent = "";
  logLine("Building ZIP…");
  try {
    const jobs = await getAllJobs();
    const zipBlob = await buildStoredZip(jobs);
    const a = document.createElement("a");
    a.href = URL.createObjectURL(zipBlob);
    a.download = "firmware-circuitpy.zip";
    a.click();
    URL.revokeObjectURL(a.href);
    logLine(`ZIP ready (${jobs.length} files). Unzip onto CIRCUITPY.`);
  } catch (e) {
    logLine(`ZIP failed: ${e.message}`, true);
    alert(e.message);
  }
}

/**
 * Minimal ZIP (store only, no compression).
 * @param {{ relPath: string, getBlob: () => Promise<Blob> }[]} jobs
 */
async function buildStoredZip(jobs) {
  const chunks = [];
  const central = [];
  let offset = 0;

  for (const { relPath, getBlob } of jobs) {
    const blob = await getBlob();
    const buf = new Uint8Array(await blob.arrayBuffer());
    const nameBytes = new TextEncoder().encode(relPath.replace(/\\/g, "/"));
    const crc = crc32(buf);
    const localHeader = new Uint8Array(30 + nameBytes.length);
    const view = new DataView(localHeader.buffer);
    view.setUint32(0, 0x04034b50, true);
    view.setUint16(6, 0, true);
    view.setUint16(8, 0, true);
    view.setUint16(10, 0, true);
    view.setUint16(12, 0, true);
    view.setUint32(14, crc, true);
    view.setUint32(18, buf.length, true);
    view.setUint32(22, buf.length, true);
    view.setUint16(26, nameBytes.length, true);
    view.setUint16(28, 0, true);
    localHeader.set(nameBytes, 30);
    chunks.push(localHeader, buf);

    const cd = new Uint8Array(46 + nameBytes.length);
    const cdv = new DataView(cd.buffer);
    cdv.setUint32(0, 0x02014b50, true);
    cdv.setUint16(8, 0, true);
    cdv.setUint16(10, 0, true);
    cdv.setUint16(12, 0, true);
    cdv.setUint16(14, 0, true);
    cdv.setUint32(16, crc, true);
    cdv.setUint32(20, buf.length, true);
    cdv.setUint32(24, buf.length, true);
    cdv.setUint16(28, nameBytes.length, true);
    cdv.setUint16(30, 0, true);
    cdv.setUint16(32, 0, true);
    cdv.setUint16(34, 0, true);
    cdv.setUint32(38, 0, true);
    cdv.setUint32(42, offset, true);
    cd.set(nameBytes, 46);
    central.push(cd);
    offset += localHeader.length + buf.length;
  }

  const centralSize = central.reduce((s, c) => s + c.length, 0);
  const end = new Uint8Array(22);
  const endv = new DataView(end.buffer);
  endv.setUint32(0, 0x06054b50, true);
  endv.setUint16(8, jobs.length, true);
  endv.setUint16(10, jobs.length, true);
  endv.setUint32(12, centralSize, true);
  endv.setUint32(16, offset, true);
  endv.setUint16(20, 0, true);

  return new Blob([...chunks, ...central, end], { type: "application/zip" });
}

/** CRC-32 (IEEE) for ZIP */
function crc32(data) {
  let c = 0xffffffff;
  const table = crc32.table || (crc32.table = makeCrcTable());
  for (let i = 0; i < data.length; i++) {
    c = table[(c ^ data[i]) & 0xff] ^ (c >>> 8);
  }
  return (c ^ 0xffffffff) >>> 0;
}

function makeCrcTable() {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) {
      c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    }
    t[n] = c;
  }
  return t;
}

function logLine(msg, isErr = false) {
  const line = `[${new Date().toLocaleTimeString()}] ${msg}\n`;
  els.log.textContent += line;
  if (isErr) console.error(msg);
  else console.log(msg);
  els.log.scrollTop = els.log.scrollHeight;
}

function escapeHtml(s) {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

const state = {
  users: [],
  samples: [],
  dirty: false,
  submittedNote: "",
};

const roleSelect = document.querySelector("#role-select");
const sampleSelect = document.querySelector("#sample-select");
const loadSampleButton = document.querySelector("#load-sample");
const noteText = document.querySelector("#note-text");
const persistNote = document.querySelector("#persist-note");
const includeDebug = document.querySelector("#include-debug");
const runCodeButton = document.querySelector("#run-code");
const message = document.querySelector("#message");
const results = document.querySelector("#results");
const summary = document.querySelector("#summary");
const globalFlags = document.querySelector("#global-flags");
const diagnosisTable = document.querySelector("#diagnosis-table");
const procedureTable = document.querySelector("#procedure-table");

function setMessage(text, isError = false) {
  message.textContent = text;
  message.className = isError ? "message error" : "message";
  if (isError) {
    message.setAttribute("role", "alert");
    message.focus();
  } else {
    message.removeAttribute("role");
  }
}

async function loadJson(url) {
  const response = await fetch(url);
  const body = await response.json();
  if (!response.ok || !body.success) {
    throw new Error(body.error?.message || "Request failed");
  }
  return body.data;
}

function populateUsers(users) {
  roleSelect.innerHTML = users.map((user) => {
    return `<option value="${user.username}">${user.display_name} (${user.role})</option>`;
  }).join("");
}

function populateSamples(samples) {
  sampleSelect.innerHTML = samples.map((sample) => {
    return `<option value="${sample.id}">${sample.title}</option>`;
  }).join("");
}

function selectedSample() {
  return state.samples.find((sample) => sample.id === sampleSelect.value);
}

function loadSelectedSample() {
  const sample = selectedSample();
  if (!sample) return;
  if (state.dirty && !confirm("Replace the current note with this sample?")) {
    return;
  }
  noteText.value = sample.note_text;
  state.dirty = false;
  setMessage(`Loaded sample: ${sample.title}`);
}

function score(value) {
  return `${Math.round(Number(value) * 100)}%`;
}

function flagsList(flags) {
  if (!flags || flags.length === 0) {
    return "<span class=\"muted\">None</span>";
  }
  return `<ul>${flags.map((flag) => `<li><strong>${flag.type}</strong>: ${flag.message}</li>`).join("")}</ul>`;
}

function evidenceList(evidence) {
  if (!evidence || evidence.length === 0) {
    return "<span class=\"muted\">No evidence</span>";
  }
  return `<ul>${evidence.map((item) => {
    return `<li><code>chars ${item.start}-${item.end}</code> <span class="snippet">${item.redacted_snippet}</span></li>`;
  }).join("")}</ul>`;
}

function renderRecommendations(title, target, rows) {
  if (!rows || rows.length === 0) {
    target.innerHTML = `<h3>${title}</h3><p class="muted">No recommendations.</p>`;
    return;
  }
  target.innerHTML = `
    <h3>${title}</h3>
    <table>
      <caption>${title} recommendations</caption>
      <thead>
        <tr>
          <th scope="col">Status</th>
          <th scope="col">Code</th>
          <th scope="col">Description</th>
          <th scope="col">Confidence</th>
          <th scope="col">Evidence</th>
          <th scope="col">Flags</th>
        </tr>
      </thead>
      <tbody>
        ${rows.map((row) => `
          <tr>
            <td><span class="status ${row.status}">${row.status}</span></td>
            <td><strong>${row.code}</strong><br><span class="muted">${row.validation_status}</span></td>
            <td>${row.description || "No configured-corpus description"}</td>
            <td>
              <strong>${score(row.confidence)}</strong>
              <dl>
                <dt>Retrieval</dt><dd>${score(row.retrieval_score)}</dd>
                <dt>Evidence</dt><dd>${score(row.evidence_score)}</dd>
                <dt>Validation</dt><dd>${score(row.validation_score)}</dd>
              </dl>
            </td>
            <td>${evidenceList(row.evidence)}</td>
            <td>${flagsList(row.review_flags)}</td>
          </tr>
        `).join("")}
      </tbody>
    </table>
  `;
}

function renderResults(data) {
  summary.innerHTML = `
    <p><strong>Case:</strong> ${data.case_id}</p>
    <p><strong>Corpus:</strong> ${data.corpus_version}</p>
    ${data.debug ? `<p><strong>Trace:</strong> ${data.debug.trace_id} (${data.debug.timing_ms} ms)</p>` : ""}
  `;
  globalFlags.innerHTML = `<h3>Review Flags</h3>${flagsList(data.review_flags)}`;
  renderRecommendations("Diagnosis", diagnosisTable, data.diagnosis_codes);
  renderRecommendations("Procedure", procedureTable, data.procedure_codes);
  results.focus();
}

async function runCoding() {
  const note = noteText.value.trim();
  if (!note) {
    setMessage("Enter or load a note before running coding.", true);
    return;
  }
  state.submittedNote = note;
  results.setAttribute("aria-busy", "true");
  setMessage("Coding in progress...");
  runCodeButton.disabled = true;
  try {
    const sample = selectedSample();
    const response = await fetch("/api/code", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        case_id: sample?.id || "ad-hoc-case",
        note_text: state.submittedNote,
        include_debug: includeDebug.checked,
        persist_note: persistNote.checked,
      }),
    });
    const body = await response.json();
    if (!response.ok || !body.success) {
      throw new Error(body.error?.message || "Coding request failed");
    }
    renderResults(body.data);
    setMessage("Coding complete.");
  } catch (error) {
    setMessage(error.message || "Coding request failed.", true);
  } finally {
    runCodeButton.disabled = false;
    results.setAttribute("aria-busy", "false");
  }
}

async function init() {
  try {
    const [users, samples] = await Promise.all([
      loadJson("/api/users"),
      loadJson("/api/samples"),
    ]);
    state.users = users;
    state.samples = samples;
    populateUsers(users);
    populateSamples(samples);
    setMessage("Ready.");
  } catch (error) {
    setMessage(error.message || "Unable to initialize demo.", true);
  }
}

noteText.addEventListener("input", () => {
  state.dirty = true;
});
loadSampleButton.addEventListener("click", loadSelectedSample);
runCodeButton.addEventListener("click", runCoding);

init();

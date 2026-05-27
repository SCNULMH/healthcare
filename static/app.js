const form = document.querySelector("#risk-form");
const result = document.querySelector("#result");
const screenTitle = document.querySelector("#screen-title");
const navButtons = [...document.querySelectorAll("[data-screen-target]")];
const backButton = document.querySelector("[data-back]");
const loadDemo = document.querySelector("#load-demo");
const loadPublicSample = document.querySelector("#load-public-sample");
const publicSampleStatus = document.querySelector("#public-sample-status");
const ocrDemo = document.querySelector("#ocr-demo");
const ocrStatus = document.querySelector("#ocr-status");
const ocrFile = document.querySelector("#ocr-file");
const accountStatus = document.querySelector("#account-status");
const accountEmail = document.querySelector("#account-email");
const accountPassword = document.querySelector("#account-password");
const accountRegister = document.querySelector("#account-register");
const accountLogin = document.querySelector("#account-login");
const accountAuthForm = document.querySelector("#account-auth-form");
const accountAuthActions = document.querySelector("#account-auth-actions");
const profileName = document.querySelector("#profile-name");
const profileBirthYear = document.querySelector("#profile-birth-year");
const profileMedicalNote = document.querySelector("#profile-medical-note");
const profileSave = document.querySelector("#profile-save");
const recordMemo = document.querySelector("#record-memo");
const recordSave = document.querySelector("#record-save");
const scoreHelpToggle = document.querySelector("#score-help-toggle");
const scoreHelpPanel = document.querySelector("#score-help-panel");

const screenOrder = ["home", "account", "basic", "checkup", "activity", "lifestyle", "result"];
let currentScreen = "home";
let currentUser = getStoredUser();
let activeClientId = currentUser?.user_id || getClientId();
let latestAnalysis = null;
let activeResultPanel = "result-panel-criteria";

const healthFields = [
  "age",
  "sex",
  "height_cm",
  "weight_kg",
  "waist_cm",
  "systolic_bp",
  "diastolic_bp",
  "fasting_glucose",
  "total_cholesterol",
  "hdl",
  "ldl",
  "triglyceride",
];

const optionalNumericFields = new Set(["waist_cm"]);

const lifestyleFields = [
  "breakfast",
  "sugary_drinks_per_week",
  "late_meals_per_week",
  "exercise_per_week",
  "eating_out_per_week",
  "sleep_hours",
  "avg_steps",
  "smoking",
  "drinking",
  "available_minutes_per_day",
  "can_prepare_meals",
];

const levelLabels = {
  high: "높음",
  caution: "주의",
  normal: "안정",
};

function goToScreen(name) {
  const next = document.querySelector(`#screen-${name}`);
  if (!next) return;

  document.querySelectorAll(".screen").forEach((screen) => {
    screen.classList.toggle("active", screen === next);
  });

  currentScreen = name;
  screenTitle.textContent = next.dataset.title || "검진AI 리셋코치";

  document.querySelectorAll(".bottom-nav button").forEach((button) => {
    const target = button.dataset.screenTarget;
    button.classList.toggle("active", target === name);
  });
}

function goBack() {
  const index = screenOrder.indexOf(currentScreen);
  if (index > 0) {
    goToScreen(screenOrder[index - 1]);
  }
}

function getClientId() {
  const key = "resetCoachClientId";
  const existing = localStorage.getItem(key);
  if (existing) return existing;
  const next = `rc-${globalThis.crypto?.randomUUID ? globalThis.crypto.randomUUID() : Date.now().toString(36)}`;
  localStorage.setItem(key, next);
  return next;
}

function readPayload() {
  const data = new FormData(form);
  const health = {};
  const lifestyle = {};

  for (const field of healthFields) {
    const value = data.get(field);
    if (field === "sex") {
      health[field] = value;
    } else if (optionalNumericFields.has(field) && String(value).trim() === "") {
      health[field] = null;
    } else {
      health[field] = Number(value);
    }
  }

  for (const field of lifestyleFields) {
    if (field === "can_prepare_meals") {
      lifestyle[field] = data.get(field) === "on";
    } else if (["breakfast", "smoking", "drinking"].includes(field)) {
      lifestyle[field] = data.get(field);
    } else {
      lifestyle[field] = Number(data.get(field));
    }
  }

  return { client_id: activeClientId, health, lifestyle };
}

function fillForm(payload) {
  for (const values of Object.values(payload)) {
    if (!values || typeof values !== "object") continue;
    for (const [key, value] of Object.entries(values)) {
      const input = form.elements[key];
      if (!input) continue;
      if (input.type === "checkbox") {
        input.checked = Boolean(value);
      } else {
        input.value = value;
      }
    }
  }
}

function renderLoading() {
  result.innerHTML = `
    <div class="analysis-panel">
      <div class="analysis-topbar">
        <strong>분석 엔진</strong>
        <span class="live-pill"><i></i> LIVE</span>
      </div>
      <div class="analysis-hero">
        <div class="score-ring" style="--value:45%">
          <div>AI</div>
        </div>
        <h2>분석 중...</h2>
        <p>검진 수치와 생활패턴을 바탕으로 위험 요인과 오늘의 개선 행동을 계산하고 있습니다.</p>
      </div>
    </div>
  `;
  goToScreen("result");
}

function render(data) {
  latestAnalysis = data;
  const primaryRisk = [...data.risks].sort((a, b) => b.probability - a.probability)[0];
  const aiSteps = data.ai_explanation?.steps || [];
  const criteria = data.ai_explanation?.criteria || [];
  const inputNotes = (data.input_notes || []).map((note) => `<p class="engine-note">${note}</p>`).join("");
  const comparison = renderComparison(data.comparison);
  const reliability = renderReliability(data.reliability);

  const risks = data.risks
    .map(
      (risk) => `
        <article class="result-card risk-card ${risk.level}">
          <div class="risk-card-top">
            <div>
              <h3>${risk.label}</h3>
              <p class="muted">AI 판단 근거 · 검진 수치와 생활패턴 기반</p>
            </div>
            <span class="risk-level ${risk.level}">${levelLabels[risk.level] || risk.level}</span>
          </div>
          <div class="meter" style="--value:${risk.probability}%"><span></span></div>
          <p class="risk-score">${risk.probability}% · ${risk.summary}</p>
          <p class="muted">${risk.reasons.join("<br />")}</p>
        </article>
      `,
    )
    .join("");

  const actions = data.plan.today_actions
    .map(
      (action) => `
        <article class="action-card">
          <h3>${action.title}</h3>
          <p>${action.detail}</p>
          <p class="muted">난이도: ${action.difficulty}</p>
          ${action.impact ? `<p class="impact-note">${action.impact}</p>` : ""}
        </article>
      `,
    )
    .join("");

  const goals = data.plan.weekly_goals
    .map((goal) => `<article class="weekly-card"><p>${goal}</p></article>`)
    .join("");

  const impactSummary = (data.plan.impact_summary || [])
    .map(
      (item) => `
        <article class="impact-card">
          <strong>${item.factor}</strong>
          <p>현재 ${item.current} · 목표 ${item.threshold}</p>
          <span>${item.impact}</span>
        </article>
      `,
    )
    .join("");

  const aiExplanation = aiSteps
    .map(
      (step, index) => `
        <article class="ai-step-card">
          <span>${index + 1}</span>
          <div>
            <h3>${step.title}</h3>
            <p>${step.description}</p>
          </div>
        </article>
      `,
    )
    .join("");

  const criteriaCards = criteria
    .map(
      (item) => `
        <article class="criteria-card">
          <h3>${item.name}</h3>
          <p><strong>측정 기준</strong>${item.primary}</p>
          <p><strong>낮추는 행동</strong>${item.lifestyle}</p>
        </article>
      `,
    )
    .join("");

  result.innerHTML = `
    <div class="analysis-panel">
      <div class="analysis-topbar">
        <strong>분석 엔진</strong>
        <span class="live-pill"><i></i> 완료</span>
      </div>
      <div class="analysis-hero">
        <div class="score-ring" style="--value:${primaryRisk.probability}%">
          <div>${primaryRisk.probability}</div>
        </div>
        <h2>${primaryRisk.label} 가능성이 가장 크게 예측되었습니다.</h2>
        <p>${primaryRisk.summary} BMI ${data.bmi}와 검진 수치, 생활패턴을 함께 반영했습니다.</p>
        <p class="engine-note">예측 엔진: ${data.engine?.mode || "rule"} · ${data.engine?.message || "설명 가능한 규칙 기반 AI 엔진을 사용했습니다."}</p>
        ${inputNotes}
        ${comparison}
        <button id="save-analysis" class="primary wide save-analysis-button" type="button">진단결과 저장</button>
        <p id="save-analysis-status" class="muted save-analysis-status">저장 버튼을 누를 때만 이전 기록에 반영됩니다.</p>
      </div>
    </div>

    <div class="result-tabbar" role="tablist" aria-label="검진 결과 보기">
      <button class="active" type="button" data-result-panel="result-panel-criteria">기준</button>
      <button type="button" data-result-panel="result-panel-risks">위험도</button>
      <button type="button" data-result-panel="result-panel-reliability">신뢰도</button>
      <button type="button" data-result-panel="result-panel-actions">추천</button>
      <button type="button" data-result-panel="result-panel-weekly">1주</button>
    </div>

    <div id="result-carousel" class="result-carousel" aria-label="검진 결과 탭">
      <section id="result-panel-criteria" class="result-section result-panel ai-explain-section">
      <div class="screen-heading">
        <h2>${data.ai_explanation?.title || "AI가 이렇게 판단했어요"}</h2>
        <p>${data.ai_explanation?.model_note || ""}</p>
      </div>
      <div class="ai-step-list">${aiExplanation}</div>
      <div class="criteria-list">${criteriaCards}</div>
    </section>

      <section id="result-panel-risks" class="result-section result-panel">
      <div class="screen-heading">
        <h2>AI 질환별 위험도</h2>
        <p>${data.disclaimer}</p>
      </div>
      <div class="risk-list">${risks}</div>
    </section>

    ${reliability}

      <section id="result-panel-actions" class="result-section result-panel">
      <div class="screen-heading">
        <h2>AI 개인화 추천</h2>
        <p>${data.plan.title}</p>
      </div>
      <div class="action-list">${actions}</div>
      <div class="impact-list">${impactSummary}</div>
    </section>

      <section id="result-panel-weekly" class="result-section result-panel">
      <div class="screen-heading">
        <h2>1주 체크리스트</h2>
        <p>${data.plan.safety_note}</p>
      </div>
        <div class="weekly-list">${goals}</div>
      </section>
    </div>
  `;
  goToScreen("result");
  bindResultTabs();
  document.querySelector("#save-analysis").addEventListener("click", saveLatestAnalysis);
}

function bindResultTabs() {
  const tabbar = document.querySelector(".result-tabbar");
  const carousel = document.querySelector("#result-carousel");
  if (!tabbar || !carousel) return;

  const tabs = [...tabbar.querySelectorAll("[data-result-panel]")];
  const panels = tabs
    .map((tab) => document.querySelector(`#${tab.dataset.resultPanel}`))
    .filter(Boolean);

  function activate(panelId) {
    activeResultPanel = panelId;
    tabs.forEach((tab) => {
      tab.classList.toggle("active", tab.dataset.resultPanel === panelId);
      tab.setAttribute("aria-selected", String(tab.dataset.resultPanel === panelId));
    });
    panels.forEach((panel) => {
      panel.classList.toggle("active", panel.id === panelId);
    });
  }

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const panel = document.querySelector(`#${tab.dataset.resultPanel}`);
      if (!panel) return;
      carousel.scrollTo({ left: panel.offsetLeft - carousel.offsetLeft, behavior: "smooth" });
      activate(tab.dataset.resultPanel);
    });
  });

  activate(activeResultPanel);

  carousel.addEventListener("scroll", () => {
    const left = carousel.scrollLeft;
    const nearest = panels.reduce(
      (best, panel) => {
        const distance = Math.abs(panel.offsetLeft - carousel.offsetLeft - left);
        return distance < best.distance ? { panel, distance } : best;
      },
      { panel: panels[0], distance: Number.POSITIVE_INFINITY },
    ).panel;
    if (nearest) activate(nearest.id);
  }, { passive: true });
}

async function saveLatestAnalysis() {
  const status = document.querySelector("#save-analysis-status");
  if (!latestAnalysis) return;
  try {
    status.textContent = "진단결과를 저장하는 중입니다.";
    const payload = {
      client_id: activeClientId,
      health: readPayload().health,
      lifestyle: readPayload().lifestyle,
      bmi: latestAnalysis.bmi,
      risks: latestAnalysis.risks,
      plan: latestAnalysis.plan,
    };
    const response = await fetch("/risk/save-result", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.detail || "저장에 실패했습니다.");
    latestAnalysis.comparison = data.comparison;
    status.textContent = data.comparison?.message || "진단결과를 저장했습니다.";
    const button = document.querySelector("#save-analysis");
    button.disabled = true;
    button.textContent = "저장 완료";
    refreshHistory();
  } catch (error) {
    status.textContent = error.message;
  }
}

function renderReliability(reliability) {
  if (!reliability) return "";
  const cards = (reliability.cards || [])
    .map((item) => {
      const avg = item.training_positive_rate == null ? "기준 없음" : `${item.training_positive_rate}%`;
      const diff = item.difference_from_training_rate == null
        ? ""
        : `사용자 결과가 학습 데이터 위험군 비율보다 ${item.difference_from_training_rate > 0 ? "+" : ""}${item.difference_from_training_rate}%p`;
      const metrics = item.roc_auc == null
        ? "규칙 기반 또는 학습 제외"
        : `ROC-AUC ${item.roc_auc} · 재현율 ${item.recall ?? "-"} · 정밀도 ${item.precision ?? "-"}`;
      return `
        <article class="reliability-card">
          <div>
            <h3>${item.label}</h3>
            <p>내 결과 ${item.user_probability}% · 학습 평균 ${avg}</p>
            <span>${diff}</span>
          </div>
          <em>${metrics}</em>
        </article>
      `;
    })
    .join("");
  return `
    <section id="result-panel-reliability" class="result-section result-panel reliability-section">
      <div class="screen-heading">
        <h2>신뢰도와 평균 비교</h2>
        <p>입력값 완성도 ${reliability.input_completeness}% · 예측 엔진 ${reliability.engine_mode}</p>
      </div>
      <div class="reliability-list">${cards}</div>
      <p class="muted reliability-caution">${reliability.caution}</p>
    </section>
  `;
}

function renderComparison(comparison) {
  if (!comparison) return "";
  if (comparison.status === "first_record") {
    return `<p class="change-note neutral">${comparison.message}</p>`;
  }
  const delta = comparison.risk_delta;
  const className = delta < 0 ? "good" : delta > 0 ? "bad" : "neutral";
  const deltaText = delta === 0 ? "변화 없음" : `${delta > 0 ? "+" : ""}${delta}%p`;
  return `
    <div class="change-panel ${className}">
      <strong>이전 분석 대비 ${deltaText}</strong>
      <p>${comparison.message}</p>
      <span>BMI 변화 ${comparison.bmi_delta > 0 ? "+" : ""}${comparison.bmi_delta}</span>
    </div>
  `;
}

async function refreshHistory() {
  const homeScore = document.querySelector("#home-score");
  const homeScoreLabel = document.querySelector("#home-score-label");
  const homeScoreSummary = document.querySelector("#home-score-summary");
  const homeScoreBand = document.querySelector("#home-score-band");
  const historySummary = document.querySelector("#history-summary");
  if (!historySummary) return;
  try {
    const response = await fetch(`/risk/history/${encodeURIComponent(activeClientId)}?limit=5`);
    if (!response.ok) throw new Error("이전 분석 기록을 불러오지 못했습니다.");
    const data = await response.json();
    const latest = data.items?.[0];
    if (!latest) {
      homeScore.textContent = "--";
      homeScoreLabel.textContent = "오늘의 건강 리셋 점수";
      homeScoreBand.textContent = "저장된 분석 없음";
      homeScoreBand.className = "score-band";
      homeScoreSummary.textContent = "검진 수치와 생활패턴을 함께 분석합니다.";
      historySummary.innerHTML = `
        <strong>이전 분석 기록</strong>
        <p>아직 저장된 분석 결과가 없습니다. 첫 분석 후 변화 추이를 확인할 수 있습니다.</p>
      `;
      return;
    }
    const resetScore = Math.max(5, 100 - latest.primary_risk_probability);
    const scoreBand = scoreBandLabel(resetScore);
    const summary = data.summary || {};
    const riskDelta = summary.risk_delta_from_oldest || 0;
    const deltaText = data.items.length > 1
      ? `첫 기록 대비 주요 위험도 ${riskDelta > 0 ? "+" : ""}${riskDelta}%p`
      : "다음 분석부터 변화 비교";
    homeScore.textContent = resetScore;
    homeScoreLabel.textContent = "최근 건강 리셋 점수";
    homeScoreBand.textContent = `${scoreBand.range} · ${scoreBand.label}`;
    homeScoreBand.className = `score-band ${scoreBand.level}`;
    homeScoreSummary.textContent = `${latest.primary_risk_label} ${latest.primary_risk_probability}% 기준입니다.`;
    historySummary.innerHTML = `
      <strong>이전 값 변화</strong>
      <p>${deltaText}</p>
      <div class="history-mini-list">
        ${data.items
          .slice(0, 3)
          .map(
            (item) => `
              <span>
                <b>${item.primary_risk_probability}%</b>
                ${item.primary_risk_label}
              </span>
            `,
          )
          .join("")}
      </div>
    `;
  } catch (error) {
    historySummary.innerHTML = `<strong>이전 분석 기록</strong><p>${error.message}</p>`;
  }
}

function scoreBandLabel(score) {
  if (score >= 70) return { range: "70~100", label: "안정권", level: "normal" };
  if (score >= 40) return { range: "40~69", label: "주의권", level: "caution" };
  return { range: "0~39", label: "위험군", level: "high" };
}

function getStoredUser() {
  try {
    return JSON.parse(localStorage.getItem("resetCoachUser") || "null");
  } catch {
    return null;
  }
}

function setCurrentUser(user) {
  currentUser = user;
  activeClientId = user?.user_id || getClientId();
  if (user) {
    localStorage.setItem("resetCoachUser", JSON.stringify(user));
    const displayId = user.email || user.user_id;
    accountStatus.textContent = `${displayId} 아이디로 로그인되었습니다.`;
    document.body.classList.add("logged-in");
    accountAuthForm.hidden = true;
    accountAuthActions.hidden = true;
    accountAuthForm.style.display = "none";
    accountAuthActions.style.display = "none";
    accountPassword.value = "";
    fillAccountProfile(user.profile || {});
  } else {
    localStorage.removeItem("resetCoachUser");
    accountStatus.textContent = "로그인하면 분석 결과와 이전 진료기록을 Firebase에 저장합니다.";
    document.body.classList.remove("logged-in");
    accountAuthForm.hidden = false;
    accountAuthActions.hidden = false;
    accountAuthForm.style.display = "";
    accountAuthActions.style.display = "";
  }
  refreshHistory();
}

function fillAccountProfile(profile) {
  profileName.value = profile.name || "";
  profileBirthYear.value = profile.birth_year || "";
  profileMedicalNote.value = profile.medical_note ? dedupeMedicalNote(profile.medical_note) : "";
}

async function accountRequest(path, body, method = "POST") {
  const response = await fetch(path, {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.detail || "계정 처리에 실패했습니다.");
  return data;
}

async function registerAccount() {
  try {
    if (!accountEmail.value || accountPassword.value.length < 8) {
      accountStatus.textContent = "이메일과 8자 이상 비밀번호를 입력해 주세요.";
      return;
    }
    accountStatus.textContent = "계정을 생성하는 중입니다.";
    const data = await accountRequest("/account/register", {
      email: accountEmail.value,
      password: accountPassword.value,
      profile: buildProfilePayload(),
    });
    setCurrentUser(data.user);
  } catch (error) {
    accountStatus.textContent = error.message;
  }
}

async function loginAccount() {
  try {
    if (!accountEmail.value || accountPassword.value.length < 8) {
      accountStatus.textContent = "이메일과 8자 이상 비밀번호를 입력해 주세요.";
      return;
    }
    accountStatus.textContent = "로그인하는 중입니다.";
    const data = await accountRequest("/account/login", {
      email: accountEmail.value,
      password: accountPassword.value,
    });
    setCurrentUser(data.user);
  } catch (error) {
    accountStatus.textContent = error.message;
  }
}

function buildProfilePayload() {
  const medicalNote = profileMedicalNote.value.trim();
  const payload = {};
  if (profileName.value.trim()) payload.name = profileName.value.trim();
  if (profileBirthYear.value) payload.birth_year = Number(profileBirthYear.value);
  if (medicalNote) payload.medical_note = dedupeMedicalNote(medicalNote);
  return payload;
}

function dedupeMedicalNote(value) {
  const parts = value
    .split("/")
    .map((part) => part.trim())
    .filter(Boolean);
  return [...new Set(parts)].join(" / ");
}

async function saveProfile() {
  if (!currentUser) {
    accountStatus.textContent = "먼저 가입 또는 로그인해 주세요.";
    return;
  }
  try {
    const data = await accountRequest(`/account/profile/${currentUser.user_id}`, buildProfilePayload(), "PUT");
    setCurrentUser(data.user);
    accountStatus.textContent = "개인정보를 저장했습니다.";
  } catch (error) {
    accountStatus.textContent = error.message;
  }
}

async function saveMedicalRecord() {
  if (!currentUser) {
    accountStatus.textContent = "먼저 가입 또는 로그인해 주세요.";
    return;
  }
  try {
    await accountRequest(`/account/medical-records/${currentUser.user_id}`, {
      memo: recordMemo.value.trim(),
    });
    recordMemo.value = "";
    accountStatus.textContent = "이전 진료기록을 저장했습니다.";
  } catch (error) {
    accountStatus.textContent = error.message;
  }
}

navButtons.forEach((button) => {
  button.addEventListener("click", () => goToScreen(button.dataset.screenTarget));
});

backButton.addEventListener("click", goBack);

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    renderLoading();
    const response = await fetch("/risk/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readPayload()),
    });
    if (!response.ok) throw new Error("입력값을 다시 확인해 주세요.");
    render(await response.json());
  } catch (error) {
    result.innerHTML = `
      <div class="empty-result">
        <h2>입력 확인 필요</h2>
        <p>${error.message}</p>
        <button class="primary wide" type="button" data-screen-target="lifestyle">다시 입력하기</button>
      </div>
    `;
    goToScreen("result");
  }
});

loadDemo.addEventListener("click", async () => {
  const response = await fetch("/risk/demo");
  fillForm(await response.json());
  publicSampleStatus.textContent = "데모 입력값을 불러왔습니다. 하단 입력 탭에서 확인할 수 있습니다.";
});

loadPublicSample.addEventListener("click", async () => {
  try {
    publicSampleStatus.textContent = "공공데이터 샘플을 불러오는 중입니다.";
    const response = await fetch("/data/checkup/prefill");
    if (!response.ok) throw new Error("공공데이터 샘플 조회에 실패했습니다.");

    const data = await response.json();
    if (!data.prefill) throw new Error(data.message || "변환 가능한 샘플이 없습니다.");
    fillForm(data.prefill);
    publicSampleStatus.textContent = data.source?.year
      ? `${data.source.year}년 건강검진정보 샘플을 입력폼에 반영했습니다.`
      : data.message;
  } catch (error) {
    publicSampleStatus.textContent = error.message;
  }
});

ocrDemo.addEventListener("click", async () => {
  try {
    const formData = new FormData();
    if (ocrFile.files.length > 0) {
      formData.append("file", ocrFile.files[0]);
    }

    const response =
      ocrFile.files.length > 0
        ? await fetch("/risk/ocr/extract", { method: "POST", body: formData })
        : await fetch("/risk/ocr/demo", { method: "POST" });
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new Error(errorData.detail || "OCR 처리에 실패했습니다.");
    }

    const data = await response.json();
    fillForm(data.prefill);
    const provider = data.provider ? `[${data.provider}] ` : "";
    const prefix = data.filename ? `${data.filename}: ` : "";
    ocrStatus.textContent = `${provider}${prefix}${data.message} 검진 수치 화면에서 확인해 주세요.`;
    goToScreen("checkup");
  } catch (error) {
    ocrStatus.textContent = error.message;
  }
});

accountRegister.addEventListener("click", registerAccount);
accountLogin.addEventListener("click", loginAccount);
profileSave.addEventListener("click", saveProfile);
recordSave.addEventListener("click", saveMedicalRecord);
scoreHelpToggle.addEventListener("click", () => {
  const nextHidden = !scoreHelpPanel.hidden ? true : false;
  scoreHelpPanel.hidden = nextHidden;
  scoreHelpToggle.setAttribute("aria-expanded", String(!nextHidden));
});

[accountEmail, accountPassword].forEach((input) => {
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      loginAccount();
    }
  });
});

document.addEventListener("click", (event) => {
  const dynamicTarget = event.target.closest("[data-screen-target]");
  if (dynamicTarget) {
    goToScreen(dynamicTarget.dataset.screenTarget);
  }
});

refreshHistory();
if (currentUser) setCurrentUser(currentUser);
goToScreen("home");

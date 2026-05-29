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
const accountLogout = document.querySelector("#account-logout");
const accountAuthForm = document.querySelector("#account-auth-form");
const accountAuthActions = document.querySelector("#account-auth-actions");
const profileName = document.querySelector("#profile-name");
const profileBirthYear = document.querySelector("#profile-birth-year");
const profileSex = document.querySelector("#profile-sex");
const profileAge = document.querySelector("#profile-age");
const profileHeightCm = document.querySelector("#profile-height-cm");
const profileWeightKg = document.querySelector("#profile-weight-kg");
const profileWaistCm = document.querySelector("#profile-waist-cm");
const profileLoadBasic = document.querySelector("#profile-load-basic");
const profileMedicalNote = document.querySelector("#profile-medical-note");
const profileSave = document.querySelector("#profile-save");
const recordMemo = document.querySelector("#record-memo");
const recordSave = document.querySelector("#record-save");
const scoreHelpToggle = document.querySelector("#score-help-toggle");
const scoreHelpPanel = document.querySelector("#score-help-panel");
const lipidCard = document.querySelector("#lipid-card");

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
const unknownableHealthFields = new Set([
  "systolic_bp",
  "diastolic_bp",
  "fasting_glucose",
  "total_cholesterol",
  "hdl",
  "ldl",
  "triglyceride",
]);
const bpFields = new Set(["systolic_bp", "diastolic_bp"]);
const glucoseFields = new Set(["fasting_glucose"]);
const lipidFields = new Set(["total_cholesterol", "hdl", "ldl", "triglyceride"]);

const lifestyleFields = [
  "breakfast_per_week",
  "sugary_drinks_per_week",
  "late_meals_per_week",
  "exercise_per_week",
  "eating_out_per_week",
  "sleep_hours",
  "avg_steps",
  "smoking",
  "drinking_per_week",
  "drinking_per_month",
  "drinks_per_session",
  "available_minutes_per_day",
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
  const unknownFields = [...unknownableHealthFields].filter((field) => data.get(`unknown_${field}`) === "on");
  const unknownSet = new Set(unknownFields);

  for (const field of healthFields) {
    const value = data.get(field);
    if (field === "sex") {
      health[field] = value;
    } else if (unknownSet.has(field)) {
      health[field] = null;
    } else if (optionalNumericFields.has(field) && String(value).trim() === "") {
      health[field] = null;
    } else {
      health[field] = Number(value);
    }
  }
  health.unknown_fields = unknownFields;
  health.bp_unknown = [...bpFields].every((field) => unknownSet.has(field));
  health.glucose_unknown = unknownSet.has("fasting_glucose");
  health.lipid_unknown = [...lipidFields].every((field) => unknownSet.has(field));

  for (const field of lifestyleFields) {
    if (["smoking"].includes(field)) {
      lifestyle[field] = data.get(field);
    } else {
      lifestyle[field] = Number(data.get(field));
    }
  }

  return { client_id: activeClientId, health, lifestyle };
}

function profileContext() {
  const payload = readPayload();
  const profile = currentUser?.profile || {};
  const birthYear = Number(profile.birth_year || profileBirthYear.value || 0);
  const age = birthYear ? new Date().getFullYear() - birthYear : payload.health.age;
  const sex = profile.sex || profileSex?.value || payload.health.sex;
  const decade = Math.max(20, Math.min(80, Math.floor(age / 10) * 10));
  return { age, decade, sex, sexLabel: sex === "female" ? "여성" : "남성" };
}

const benchmarkTable = {
  20: { systolic: "110~120mmHg", diastolic: "70~78mmHg", glucose: "85~95mg/dL", total_cholesterol: "170~190mg/dL", hdl: "50~65mg/dL", ldl: "90~115mg/dL", triglyceride: "80~120mg/dL" },
  30: { systolic: "115~125mmHg", diastolic: "72~80mmHg", glucose: "88~98mg/dL", total_cholesterol: "180~200mg/dL", hdl: "48~62mg/dL", ldl: "100~125mg/dL", triglyceride: "90~135mg/dL" },
  40: { systolic: "120~130mmHg", diastolic: "75~85mmHg", glucose: "90~100mg/dL", total_cholesterol: "190~210mg/dL", hdl: "45~60mg/dL", ldl: "110~130mg/dL", triglyceride: "100~150mg/dL" },
  50: { systolic: "125~135mmHg", diastolic: "78~86mmHg", glucose: "92~105mg/dL", total_cholesterol: "195~215mg/dL", hdl: "43~58mg/dL", ldl: "115~135mg/dL", triglyceride: "110~160mg/dL" },
  60: { systolic: "130~140mmHg", diastolic: "78~88mmHg", glucose: "95~110mg/dL", total_cholesterol: "190~215mg/dL", hdl: "42~57mg/dL", ldl: "110~135mg/dL", triglyceride: "110~165mg/dL" },
  70: { systolic: "130~145mmHg", diastolic: "75~85mmHg", glucose: "95~112mg/dL", total_cholesterol: "185~210mg/dL", hdl: "40~55mg/dL", ldl: "105~130mg/dL", triglyceride: "105~160mg/dL" },
  80: { systolic: "130~145mmHg", diastolic: "72~84mmHg", glucose: "95~112mg/dL", total_cholesterol: "180~205mg/dL", hdl: "40~55mg/dL", ldl: "100~125mg/dL", triglyceride: "100~155mg/dL" },
};

function updateBenchmarks() {
  const context = profileContext();
  const table = benchmarkTable[context.decade] || benchmarkTable[40];
  document.querySelectorAll("[data-benchmark]").forEach((item) => {
    const key = item.dataset.benchmark;
    item.textContent = `${context.decade}대 ${context.sexLabel} 평균 ${table[key]}`;
  });
}

function renderBenchmarkSummary() {
  const context = profileContext();
  const table = benchmarkTable[context.decade] || benchmarkTable[40];
  const payload = readPayload();
  const drinking = drinkingProfile(payload.lifestyle);
  const lipidText = payload.health.lipid_unknown
    ? "지질 수치는 모두 모름으로 표시되어 결과에서 직접 수치 비교를 제외했습니다."
    : payload.health.unknown_fields?.some((field) => lipidFields.has(field))
      ? "일부 지질 수치는 모름으로 표시되어 입력된 항목만 결과에 반영했습니다."
    : `지질 평균: 총콜레스테롤 ${table.total_cholesterol}, LDL ${table.ldl}, 중성지방 ${table.triglyceride}`;
  return `
    <div class="benchmark-summary">
      <strong>${context.decade}대 ${context.sexLabel} 평균 기준</strong>
      <p>혈압 ${table.systolic}/${table.diastolic}, 공복혈당 ${table.glucose}</p>
      <p>${lipidText}</p>
      <p>음주 기준: 주간 횟수×4 + 월간 추가 횟수로 월 음주 횟수를 계산하고, 1회 평균 잔 수를 함께 봅니다. 현재 입력값은 <strong>${drinking.label}</strong>입니다.</p>
      ${renderDrinkingMap(drinking.level)}
    </div>
  `;
}

function drinkingProfile(lifestyle) {
  const weekly = Number(lifestyle.drinking_per_week || 0);
  const monthlyExtra = Number(lifestyle.drinking_per_month || 0);
  const drinks = Number(lifestyle.drinks_per_session || 0);
  const monthlySessions = weekly * 4 + monthlyExtra;
  if (weekly <= 0 && monthlyExtra <= 0) {
    return { level: "none", label: "안 함", monthlySessions, drinks };
  }
  if (monthlySessions <= 3 && drinks <= 2) {
    return { level: "light", label: "가벼움", monthlySessions, drinks };
  }
  if (monthlySessions <= 8 && drinks <= 4) {
    return { level: "moderate", label: "보통", monthlySessions, drinks };
  }
  return { level: "heavy", label: "잦음", monthlySessions, drinks };
}

function renderDrinkingMap(activeLevel) {
  const levels = [
    ["none", "안 함", "월 0회"],
    ["light", "가벼움", "월 1~3회 · 2잔 이하"],
    ["moderate", "보통", "월 4~8회 또는 4잔 이하"],
    ["heavy", "잦음", "월 9회 이상 또는 5잔 이상"],
  ];
  return `
    <div class="drinking-map" aria-label="음주 입력값 변환 기준">
      ${levels
        .map(([level, label, rule]) => `
          <span class="drinking-chip ${level === activeLevel ? "active" : ""}">
            <strong>${label}</strong>
            <em>${rule}</em>
          </span>
        `)
        .join("")}
    </div>
  `;
}

function updateUnknownState() {
  unknownableHealthFields.forEach((field) => {
    const checked = Boolean(form.elements[`unknown_${field}`]?.checked);
    const input = form.elements[field];
    if (input) input.disabled = checked;
    input?.closest("label")?.classList.toggle("muted-field", checked);
  });
  lipidCard?.classList.toggle("muted-card", [...lipidFields].every((field) => form.elements[`unknown_${field}`]?.checked));
}

function fillForm(payload) {
  const unknownFields = new Set(payload?.health?.unknown_fields || []);
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
  if (unknownFields.size) {
    unknownableHealthFields.forEach((field) => {
      const input = form.elements[`unknown_${field}`];
      if (input) input.checked = unknownFields.has(field);
    });
  }
  updateUnknownState();
}

function renderLoading() {
  result.innerHTML = `
    <div class="analysis-panel">
      <div class="analysis-topbar">
        <strong>분석 중</strong>
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
        <h2>${primaryRisk.label} 신호가 가장 크게 나타났습니다.</h2>
        <p>${primaryRisk.summary} BMI ${data.bmi}와 검진 수치, 생활패턴을 함께 반영했습니다.</p>
        <p class="engine-note">분석 방식: ${data.engine?.mode || "rule"} · ${data.engine?.message || "검진 기준과 생활패턴 기준을 함께 적용했습니다."}</p>
        ${inputNotes}
        ${renderBenchmarkSummary()}
        ${comparison}
        <button id="save-analysis" class="primary wide save-analysis-button" type="button">분석 결과 저장</button>
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
        <h2>${data.ai_explanation?.title || "이렇게 계산했어요"}</h2>
        <p>${data.ai_explanation?.model_note || ""}</p>
      </div>
      <div class="ai-step-list">${aiExplanation}</div>
      <div class="criteria-list">${criteriaCards}</div>
    </section>

      <section id="result-panel-risks" class="result-section result-panel">
      <div class="screen-heading">
        <h2>질환별 위험 신호</h2>
        <p>${data.disclaimer}</p>
      </div>
      <div class="risk-list">${risks}</div>
    </section>

    ${reliability}

      <section id="result-panel-actions" class="result-section result-panel">
      <div class="screen-heading">
        <h2>내 프로필 맞춤 행동</h2>
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
  if (!currentUser) {
    status.textContent = "로그인하면 분석 결과를 저장할 수 있습니다. 오른쪽 위 계정 아이콘에서 로그인해 주세요.";
    goToScreen("account");
    return;
  }
  try {
    status.textContent = "분석 결과를 저장하는 중입니다.";
    const payload = {
      client_id: activeClientId,
      user_id: currentUser.user_id,
      session_token: currentUser.session_token,
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
    status.textContent = data.comparison?.message || "분석 결과를 저장했습니다.";
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
        <h2>입력 완성도와 평균 비교</h2>
        <p>입력값 완성도 ${reliability.input_completeness}% · 분석 방식 ${reliability.engine_mode}</p>
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
    accountLogout.hidden = false;
    accountAuthForm.style.display = "none";
    accountAuthActions.style.display = "none";
    accountLogout.style.display = "";
    accountPassword.value = "";
    fillAccountProfile(user.profile || {});
  } else {
    localStorage.removeItem("resetCoachUser");
    accountStatus.textContent = "로그인하면 분석 결과와 이전 진료기록을 Firebase에 저장합니다.";
    document.body.classList.remove("logged-in");
    accountAuthForm.hidden = false;
    accountAuthActions.hidden = false;
    accountLogout.hidden = true;
    accountAuthForm.style.display = "";
    accountAuthActions.style.display = "";
    accountLogout.style.display = "none";
  }
  refreshHistory();
}

function logoutAccount() {
  setCurrentUser(null);
  accountEmail.value = "";
  accountPassword.value = "";
  profileName.value = "";
  profileBirthYear.value = "";
  if (profileSex) profileSex.value = "";
  if (profileAge) profileAge.value = "";
  if (profileHeightCm) profileHeightCm.value = "";
  if (profileWeightKg) profileWeightKg.value = "";
  if (profileWaistCm) profileWaistCm.value = "";
  profileMedicalNote.value = "";
  recordMemo.value = "";
  accountStatus.textContent = "로그아웃되었습니다. 다시 저장하려면 로그인해 주세요.";
  goToScreen("account");
}

function fillAccountProfile(profile) {
  profileName.value = profile.name || "";
  profileBirthYear.value = profile.birth_year || "";
  if (profileSex) profileSex.value = profile.sex || "";
  if (profileAge) profileAge.value = profile.age || "";
  if (profileHeightCm) profileHeightCm.value = profile.height_cm || "";
  if (profileWeightKg) profileWeightKg.value = profile.weight_kg || "";
  if (profileWaistCm) profileWaistCm.value = profile.waist_cm || "";
  profileMedicalNote.value = profile.medical_note ? dedupeMedicalNote(profile.medical_note) : "";
  updateBenchmarks();
}

function loadBasicInfoToProfile() {
  const age = form.elements.age?.value;
  const sex = form.elements.sex?.value;
  const height = form.elements.height_cm?.value;
  const weight = form.elements.weight_kg?.value;
  const waist = form.elements.waist_cm?.value;
  if (profileAge && age) profileAge.value = age;
  if (profileSex && sex) profileSex.value = sex;
  if (profileHeightCm && height) profileHeightCm.value = height;
  if (profileWeightKg && weight) profileWeightKg.value = weight;
  if (profileWaistCm) profileWaistCm.value = waist || "";
  accountStatus.textContent = "기본정보 탭의 값을 개인정보 입력칸에 불러왔습니다.";
  updateBenchmarks();
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
  if (currentUser?.email) payload.email = currentUser.email;
  if (profileName.value.trim()) payload.name = profileName.value.trim();
  if (profileBirthYear.value) payload.birth_year = Number(profileBirthYear.value);
  if (profileSex?.value) payload.sex = profileSex.value;
  if (profileAge?.value) payload.age = Number(profileAge.value);
  if (profileHeightCm?.value) payload.height_cm = Number(profileHeightCm.value);
  if (profileWeightKg?.value) payload.weight_kg = Number(profileWeightKg.value);
  if (profileWaistCm?.value) payload.waist_cm = Number(profileWaistCm.value);
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
    setCurrentUser({ ...data.user, session_token: currentUser.session_token });
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
accountLogout?.addEventListener("click", logoutAccount);
profileSave.addEventListener("click", saveProfile);
profileLoadBasic?.addEventListener("click", loadBasicInfoToProfile);
recordSave.addEventListener("click", saveMedicalRecord);
document.querySelectorAll("[name^='unknown_']").forEach((input) => {
  input.addEventListener("change", updateUnknownState);
});
form.elements.age?.addEventListener("input", updateBenchmarks);
form.elements.sex?.addEventListener("change", updateBenchmarks);
profileBirthYear?.addEventListener("input", updateBenchmarks);
profileSex?.addEventListener("change", updateBenchmarks);
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
updateUnknownState();
updateBenchmarks();
goToScreen("home");

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

const screenOrder = ["home", "basic", "checkup", "activity", "lifestyle", "ocr", "result"];
let currentScreen = "home";

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

function readPayload() {
  const data = new FormData(form);
  const health = {};
  const lifestyle = {};

  for (const field of healthFields) {
    health[field] = field === "sex" ? data.get(field) : Number(data.get(field));
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

  return { health, lifestyle };
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
  const primaryRisk = [...data.risks].sort((a, b) => b.probability - a.probability)[0];
  const aiSteps = data.ai_explanation?.steps || [];

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
        </article>
      `,
    )
    .join("");

  const goals = data.plan.weekly_goals
    .map((goal) => `<article class="weekly-card"><p>${goal}</p></article>`)
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
      </div>
    </div>

    <section class="result-section ai-explain-section">
      <div class="screen-heading">
        <h2>${data.ai_explanation?.title || "AI가 이렇게 판단했어요"}</h2>
        <p>${data.ai_explanation?.model_note || ""}</p>
      </div>
      <div class="ai-step-list">${aiExplanation}</div>
    </section>

    <section class="result-section">
      <div class="screen-heading">
        <h2>AI 질환별 위험도</h2>
        <p>${data.disclaimer}</p>
      </div>
      <div class="risk-list">${risks}</div>
    </section>

    <section class="result-section">
      <div class="screen-heading">
        <h2>AI 개인화 추천</h2>
        <p>${data.plan.title}</p>
      </div>
      <div class="action-list">${actions}</div>
    </section>

    <section class="result-section">
      <div class="screen-heading">
        <h2>1주 체크리스트</h2>
        <p>${data.plan.safety_note}</p>
      </div>
      <div class="weekly-list">${goals}</div>
    </section>
  `;
  goToScreen("result");
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
    ocrStatus.textContent = `${provider}${prefix}${data.message}`;
  } catch (error) {
    ocrStatus.textContent = error.message;
  }
});

document.addEventListener("click", (event) => {
  const dynamicTarget = event.target.closest("[data-screen-target]");
  if (dynamicTarget) {
    goToScreen(dynamicTarget.dataset.screenTarget);
  }
});

goToScreen("home");

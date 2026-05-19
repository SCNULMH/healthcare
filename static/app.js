const form = document.querySelector("#risk-form");
const result = document.querySelector("#result");
const loadDemo = document.querySelector("#load-demo");
const loadPublicSample = document.querySelector("#load-public-sample");
const publicSampleStatus = document.querySelector("#public-sample-status");
const ocrDemo = document.querySelector("#ocr-demo");
const ocrStatus = document.querySelector("#ocr-status");
const ocrFile = document.querySelector("#ocr-file");

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

function render(data) {
  const risks = data.risks
    .map(
      (risk) => `
        <article class="risk-card">
          <strong>${risk.label}</strong>
          <div class="meter" style="--value:${risk.probability}%"><span></span></div>
          <p>${risk.probability}% · ${risk.summary}</p>
          <p class="muted">${risk.reasons.join("<br />")}</p>
        </article>
      `,
    )
    .join("");

  const actions = data.plan.today_actions
    .map(
      (action) => `
        <article class="action">
          <strong>${action.title}</strong>
          <p>${action.detail}</p>
          <span class="muted">난이도: ${action.difficulty}</span>
        </article>
      `,
    )
    .join("");

  const goals = data.plan.weekly_goals.map((goal) => `<li>${goal}</li>`).join("");

  result.innerHTML = `
    <section class="result-card">
      <h2>위험예측 결과</h2>
      <p class="muted">BMI ${data.bmi} · ${data.disclaimer}</p>
      <div class="risk-grid">${risks}</div>
    </section>
    <section class="result-card">
      <h2>오늘의 작은 개선</h2>
      <p class="muted">${data.plan.title}</p>
      <div class="habit-header">
        <span>오늘 실천</span>
        <b>${data.plan.today_actions.length}건</b>
      </div>
      <div class="actions">${actions}</div>
    </section>
    <section class="result-card">
      <h2>1주 목표</h2>
      <ul>${goals}</ul>
      <p class="muted">${data.plan.safety_note}</p>
    </section>
  `;
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    const response = await fetch("/risk/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(readPayload()),
    });
    if (!response.ok) throw new Error("입력값을 다시 확인해 주세요.");
    render(await response.json());
  } catch (error) {
    result.innerHTML = `<section class="result-card"><h2>입력 확인 필요</h2><p class="muted">${error.message}</p></section>`;
  }
});

loadDemo.addEventListener("click", async () => {
  const response = await fetch("/risk/demo");
  fillForm(await response.json());
  publicSampleStatus.textContent = "데모 입력값을 불러왔습니다.";
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
    if (!response.ok) throw new Error("OCR 데모 처리에 실패했습니다.");

    const data = await response.json();
    fillForm(data.prefill);
    ocrStatus.textContent = data.filename ? `${data.filename}: ${data.message}` : data.message;
  } catch (error) {
    ocrStatus.textContent = error.message;
  }
});

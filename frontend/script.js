const appShell = document.querySelector(".app-shell");
const authScreen = document.getElementById("auth-screen");
const authViews = document.querySelectorAll("[data-auth-view]");
const authSwitchButtons = document.querySelectorAll("[data-auth-target]");
const loginForm = document.getElementById("login-form");
const registerForm = document.getElementById("register-form");
const forgotForm = document.getElementById("forgot-form");
const resetForm = document.getElementById("reset-form");
const loginMessage = document.getElementById("login-message");
const registerMessage = document.getElementById("register-message");
const forgotMessage = document.getElementById("forgot-message");
const resetMessage = document.getElementById("reset-message");
const userAvatar = document.getElementById("user-avatar");
const userName = document.getElementById("user-name");
const userEmail = document.getElementById("user-email");
const profileSummary = document.getElementById("profile-summary");
const logoutButton = document.getElementById("logout-button");
const profileLogoutButton = document.getElementById("profile-logout-button");
const pages = document.querySelectorAll(".page");
const navButtons = document.querySelectorAll("[data-page]");
const textarea = document.getElementById("case-description");
const charCount = document.getElementById("char-count");
const form = document.getElementById("diagnosis-form");
const clearButton = document.getElementById("clear-case");
const exampleButton = document.getElementById("example-case");
const symptomSearch = document.getElementById("symptom-search");
const symptomList = document.getElementById("symptom-list");
const selectedCount = document.getElementById("selected-count");
const formMessage = document.getElementById("form-message");
const historySearch = document.getElementById("history-search");
const historyList = document.getElementById("history-list");
const resultTitle = document.getElementById("result-title");
const resultSubtitle = document.getElementById("result-subtitle");
const scoreLabel = document.getElementById("score-label");
const confidenceValue = document.getElementById("confidence-value");
const confidenceBar = document.getElementById("confidence-bar");
const resultNote = document.getElementById("result-note");
const medicationList = document.getElementById("medication-list");
const precautionList = document.getElementById("precaution-list");
const careList = document.getElementById("care-list");
const topPredictions = document.getElementById("top-predictions");
const topPredictionsTitle = document.getElementById("top-predictions-title");
const warningText = document.getElementById("warning-text");
const saveResultButton = document.getElementById("save-result");
const summaryDiagnosis = document.getElementById("summary-diagnosis");
const summaryMedicationName = document.getElementById("summary-medication-name");
const summaryDrugGroup = document.getElementById("summary-drug-group");
const suggestedSymptomsCard = document.getElementById("suggested-symptoms-card");
const suggestedSymptomsList = document.getElementById("suggested-symptoms-list");

const AUTH_TOKEN_KEY = "pharmaPredictAuthToken";
const AUTH_USER_KEY = "pharmaPredictUser";

const sampleCase =
  "Bệnh nhân bị ngứa da, phát ban, nổi nốt trên da và có mảng đổi màu da trong 3 ngày gần đây.";

let symptoms = [];
const selectedSymptoms = new Set();
let currentResult = null;
let savedResults = [];
let authToken = localStorage.getItem(AUTH_TOKEN_KEY) || "";
let currentUser = null;
let symptomsLoaded = false;
try {
  currentUser = JSON.parse(localStorage.getItem(AUTH_USER_KEY) || "null");
} catch {
  currentUser = null;
}

function historyStorageKey() {
  return currentUser ? `pharmaPredictHistory:${currentUser.email}` : "pharmaPredictHistory:guest";
}

function loadSavedHistory() {
  try {
    savedResults = JSON.parse(localStorage.getItem(historyStorageKey()) || "[]");
    if (!Array.isArray(savedResults)) {
      savedResults = [];
    }
  } catch {
    savedResults = [];
  }
}

function showAuthView(viewName) {
  authViews.forEach((view) => {
    view.classList.toggle("is-hidden", view.dataset.authView !== viewName);
  });
}

function setAuthMessage(element, message, isError = false) {
  if (!element) {
    return;
  }
  element.textContent = message;
  element.classList.toggle("is-error", isError);
}

async function authRequest(endpoint, payload) {
  const response = await fetch(endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || "Không xử lý được yêu cầu.");
  }
  return data;
}

function initialsForName(name, email) {
  const source = (name || email || "ND").trim();
  const words = source.split(/\s+/).filter(Boolean);
  if (words.length >= 2) {
    return `${words[0][0]}${words[words.length - 1][0]}`.toUpperCase();
  }
  return source.slice(0, 2).toUpperCase();
}

function updateUserUi() {
  const displayName = currentUser?.name || "Người dùng";
  const displayEmail = currentUser?.email || "";
  userName.textContent = displayName;
  userEmail.textContent = displayEmail;
  userAvatar.textContent = initialsForName(displayName, displayEmail);
  profileSummary.textContent = `${displayName} (${displayEmail}) đang đăng nhập vào hệ thống hỗ trợ nhập triệu chứng tiếng Việt và gợi ý nhóm thuốc khi dữ liệu đủ tin cậy.`;
  updateAdminUi();
}

function showAuthenticatedApp() {
  authScreen.classList.add("is-hidden");
  appShell.classList.remove("is-hidden");
  updateUserUi();
  loadSavedHistory();
  renderSavedHistory();
  renderRecentActivity();
  if (!symptomsLoaded) {
    loadSymptoms();
  }
  loadSamplePicker(); // US29: nạp danh sách bệnh án mẫu vào Trang Chủ
}

function showAuthScreen(viewName = "login") {
  appShell.classList.add("is-hidden");
  authScreen.classList.remove("is-hidden");
  showAuthView(viewName);
}

function handleAuthSuccess(data) {
  authToken = data.token;
  currentUser = data.user;
  localStorage.setItem(AUTH_TOKEN_KEY, authToken);
  localStorage.setItem(AUTH_USER_KEY, JSON.stringify(currentUser));
  showAuthenticatedApp();
  showPage("home");
}

async function initializeAuth() {
  appShell.classList.add("is-hidden");

  if (!authToken) {
    showAuthScreen("login");
    return;
  }

  try {
    const response = await fetch("/api/auth/me", {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Phiên đăng nhập hết hạn.");
    }
    currentUser = data.user;
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(currentUser));
    showAuthenticatedApp();
  } catch {
    localStorage.removeItem(AUTH_TOKEN_KEY);
    localStorage.removeItem(AUTH_USER_KEY);
    authToken = "";
    currentUser = null;
    showAuthScreen("login");
  }
}

function isAdminUser() {
  return currentUser?.role === "admin";
}

function updateAdminUi() {
  // US19: chỉ hiển thị mục Dashboard khi user có quyền admin.
  const admin = isAdminUser();
  document.querySelectorAll(".admin-only").forEach((el) => {
    el.classList.toggle("is-hidden", !admin);
  });
}

const ADMIN_PAGES = new Set(["dashboard", "dictionary", "samples"]);

function showPage(pageName) {
  // US19/US27: chặn trang admin nếu không phải admin (kể cả khi gọi trực tiếp).
  if (ADMIN_PAGES.has(pageName) && !isAdminUser()) {
    pageName = "home";
  }

  pages.forEach((page) => {
    page.classList.toggle("is-active", page.id === `page-${pageName}`);
  });

  navButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.page === pageName);
  });

  if (pageName === "dashboard") {
    loadDashboard();
  } else if (pageName === "dictionary") {
    loadDictionary(1);
  } else if (pageName === "samples") {
    loadSamples();
  }

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateCharCount() {
  charCount.textContent = `${textarea.value.length} / 2000 ký tự`;
}

function setMessage(message, isError = false) {
  formMessage.textContent = message;
  formMessage.classList.toggle("is-error", isError);
}

function formatError(error) {
  const message = error && error.message ? error.message : "Đã có lỗi xảy ra.";
  if (message === "Failed to fetch" || (error && error.name === "TypeError")) {
    return "Mất kết nối tới máy chủ. Kiểm tra mạng hoặc khởi động backend (python backend/app.py) rồi thử lại.";
  }
  return message;
}

function updateSelectedCount() {
  selectedCount.textContent = `${selectedSymptoms.size} đã chọn`;
}

function renderSymptoms(filter = "") {
  const query = filter.trim().toLowerCase();
  const visibleSymptoms = symptoms
    .filter((symptom) => {
      const viLabel = (symptom.label_vi || symptom.label || "").toLowerCase();
      const enLabel = (symptom.label_en || "").toLowerCase();
      return viLabel.includes(query) || enLabel.includes(query);
    })
    .slice(0, 80);

  symptomList.innerHTML = "";

  if (visibleSymptoms.length === 0) {
    symptomList.innerHTML = '<p class="muted-text">Không tìm thấy triệu chứng phù hợp.</p>';
    return;
  }

  visibleSymptoms.forEach((symptom) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "symptom-chip";
    button.dataset.symptom = symptom.id;
    button.textContent = symptom.label;
    button.classList.toggle("is-selected", selectedSymptoms.has(symptom.id));
    button.addEventListener("click", () => {
      if (selectedSymptoms.has(symptom.id)) {
        selectedSymptoms.delete(symptom.id);
      } else {
        selectedSymptoms.add(symptom.id);
      }
      updateSelectedCount();
      renderSymptoms(symptomSearch.value);
    });
    symptomList.appendChild(button);
  });
}

function renderList(element, items, fallback) {
  element.innerHTML = "";
  const safeItems = items && items.length ? items : [fallback];
  safeItems.forEach((item) => {
    const li = document.createElement("li");
    li.textContent = item;
    element.appendChild(li);
  });
}

function renderCaseSummary(result) {
  const summary = result.case_summary || {};
  summaryDiagnosis.textContent = summary.diagnosis || "Cần bổ sung thông tin";
  summaryMedicationName.textContent = summary.medication_name || "Chưa đủ dữ liệu để gợi ý thuốc";
  summaryDrugGroup.textContent = summary.drug_group || "Chưa đủ dữ liệu để gợi ý thuốc";
}

function renderSuggestedSymptoms(result) {
  const items = result.suggested_symptoms || [];
  if (!suggestedSymptomsCard || !suggestedSymptomsList) {
    return;
  }

  suggestedSymptomsList.innerHTML = "";
  suggestedSymptomsCard.classList.toggle("is-hidden", items.length === 0);
  if (items.length === 0) {
    return;
  }

  items.forEach((symptom) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "suggested-symptom-chip";
    button.dataset.symptom = symptom.id;
    button.textContent = symptom.label_vi || symptom.label;
    if (symptom.hint) {
      button.title = symptom.hint;
    }
    button.addEventListener("click", async () => {
      selectedSymptoms.add(symptom.id);
      updateSelectedCount();
      renderSymptoms(symptomSearch.value);
      button.disabled = true;
      try {
        await predict();
      } catch (error) {
        setMessage(formatError(error), true);
      }
    });
    suggestedSymptomsList.appendChild(button);
  });
}

function saveHistory() {
  localStorage.setItem(historyStorageKey(), JSON.stringify(savedResults.slice(0, 20)));
}

function createHistoryCard(entry) {
  const card = document.createElement("article");
  card.className = "history-card user-history-card";
  card.dataset.search = `${entry.disease} ${entry.notes} ${entry.symptoms.join(" ")} ${entry.savedAt}`.toLowerCase();

  const topLine = document.createElement("div");
  topLine.className = "card-topline";

  const status = document.createElement("span");
  status.className = "status-pill status-success";
  status.textContent = "Đã lưu";

  const time = document.createElement("time");
  time.textContent = entry.savedAt;

  const title = document.createElement("h2");
  title.textContent = entry.disease;

  const summary = document.createElement("p");
  summary.textContent = `${entry.symptoms.join(", ") || "Chưa rõ triệu chứng"} - ${entry.notes || "Không có mô tả."}`;

  const button = document.createElement("button");
  button.className = "icon-button";
  button.type = "button";
  button.setAttribute("aria-label", "Xem chi tiet");

  const icon = document.createElement("span");
  icon.className = "material-symbols-outlined";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "chevron_right";

  topLine.append(status, time);
  button.appendChild(icon);
  card.append(topLine, title, summary, button);
  return card;
}

function renderSavedHistory() {
  document.querySelectorAll(".user-history-card").forEach((card) => card.remove());
  savedResults
    .slice()
    .reverse()
    .forEach((entry) => {
      historyList.prepend(createHistoryCard(entry));
    });
  updateHistoryEmptyState();
}

function updateHistoryEmptyState() {
  const empty = document.getElementById("history-empty");
  if (!empty) {
    return;
  }
  const cards = historyList.querySelectorAll(".history-card");
  const anyVisible = Array.from(cards).some((card) => !card.classList.contains("is-hidden"));
  empty.classList.toggle("is-hidden", anyVisible);
  const title = empty.querySelector("h2");
  const desc = empty.querySelector("p");
  if (title && desc) {
    if (cards.length === 0) {
      title.textContent = "Chưa có lịch sử dự đoán";
      desc.textContent = "Các kết quả bạn lưu sẽ xuất hiện ở đây. Hãy thử tạo một dự đoán mới.";
    } else {
      title.textContent = "Không tìm thấy kết quả";
      desc.textContent = "Không có mục nào khớp với từ khóa tìm kiếm.";
    }
  }
}

function renderRecentActivity() {
  const container = document.getElementById("home-activity");
  if (!container) {
    return;
  }
  container.innerHTML = "";
  const recent = savedResults.slice(-3).reverse();
  if (recent.length === 0) {
    const placeholder = document.createElement("p");
    placeholder.className = "muted-text";
    placeholder.textContent = "Chưa có hoạt động. Kết quả bạn lưu sẽ hiển thị ở đây.";
    container.appendChild(placeholder);
    return;
  }
  recent.forEach((entry) => {
    const card = document.createElement("article");
    card.className = "activity-card";

    const icon = document.createElement("span");
    icon.className = "activity-icon material-symbols-outlined";
    icon.setAttribute("aria-hidden", "true");
    icon.textContent = "medication";

    const title = document.createElement("h3");
    title.textContent = entry.disease;

    const desc = document.createElement("p");
    desc.textContent = entry.symptoms.join(", ") || entry.notes || "Không có mô tả.";

    const time = document.createElement("span");
    time.textContent = entry.savedAt;

    card.append(icon, title, desc, time);
    container.appendChild(card);
  });
}

function setFormLoading(button, loading) {
  if (!button) {
    return;
  }
  button.disabled = loading;
  button.setAttribute("aria-busy", String(loading));
}

function setConfidenceLevel(level) {
  const box = confidenceBar.closest(".confidence-box");
  if (!box) {
    return;
  }
  box.dataset.level = level;
  const tag = box.querySelector(".confidence-tag");
  if (tag) {
    const labels = {
      high: "Tin cậy cao",
      mid: "Tin cậy trung bình",
      low: "Tin cậy thấp",
      rule: "Sàng lọc theo quy tắc (không phải xác suất)",
      none: "Chưa đủ dữ liệu",
    };
    tag.textContent = labels[level] || "";
  }
}

function renderPrediction(result) {
  const isRuleBased = result.score_type === "rule";
  const confidence = result.confidence === null || result.confidence === undefined ? "0.0" : (result.confidence * 100).toFixed(1);
  const isUncertain = Boolean(result.needs_more_input);
  const matchedCount = (result.matched_symptoms_vi || result.matched_symptoms || []).length;
  const unsupportedLabels = (result.unsupported_symptoms || []).map((symptom) => symptom.label_vi);
  const scoreText = result.score_label || "Độ tin cậy";

  currentResult = result;
  renderCaseSummary(result);
  renderSuggestedSymptoms(result);
  resetFeedbackBox(true); // US18: cho phép đánh giá khi đã có gợi ý
  if (scoreLabel) {
    scoreLabel.textContent = isRuleBased ? "Cơ chế gợi ý" : scoreText;
  }
  // P1: rule là heuristic, KHÔNG phải xác suất -> không hiển thị 100%, không thanh phần trăm.
  confidenceValue.textContent = isRuleBased ? "Quy tắc" : `${confidence}%`;
  confidenceBar.style.width = isRuleBased ? "0%" : `${confidence}%`;
  const confidencePct = parseFloat(confidence);
  let confidenceLevel;
  if (isRuleBased) {
    confidenceLevel = "rule";
  } else if (isUncertain || confidencePct < 50) {
    confidenceLevel = "low";
  } else if (confidencePct < 75) {
    confidenceLevel = "mid";
  } else {
    confidenceLevel = "high";
  }
  setConfidenceLevel(confidenceLevel);
  resultTitle.textContent = result.display_title || result.disease_vi || result.disease;
  resultSubtitle.textContent = `${matchedCount} triệu chứng đã map sang đặc trưng tiếng Anh`;
  if (unsupportedLabels.length > 0) {
    resultSubtitle.textContent += `; chưa hỗ trợ: ${unsupportedLabels.join(", ")}`;
  }

  const guidanceSourceText =
    result.guidance_source && result.guidance_source !== "symptom_fallback"
      ? " Gợi ý lấy từ dữ liệu train mới."
      : " Gợi ý chăm sóc đang dùng fallback theo triệu chứng.";

  if (isUncertain) {
    const suggestedLabel = result.disease_vi || result.disease || "khả năng gần nhất";
    resultNote.textContent = `${result.quality_message || "Dữ liệu đầu vào chưa đủ để kết luận."} Khả năng gần nhất trong dữ liệu: ${suggestedLabel}.${guidanceSourceText}`;
    renderList(medicationList, result.medications, "Chưa đủ dữ liệu để gợi ý nhóm thuốc.");
    renderList(precautionList, result.precautions, "Hãy bổ sung thêm triệu chứng cụ thể hoặc tham khảo bác sĩ nếu triệu chứng kéo dài/nặng.");
    renderList(careList, [...(result.diets || []), ...(result.workouts || [])].slice(0, 8), "Bổ sung thêm triệu chứng, thời gian khởi phát và mức độ nặng.");
  } else {
    const reasonPrefix = result.reason ? `${result.reason} ` : "";
    resultNote.textContent = `${reasonPrefix}${result.description || "Dữ liệu tham chiếu chưa có mô tả cho bệnh này."}${guidanceSourceText}`;
    renderList(medicationList, result.medications, "Dữ liệu tham chiếu chưa có thuốc gợi ý.");
    renderList(precautionList, result.precautions, "Dữ liệu tham chiếu chưa có lưu ý phòng ngừa.");
    renderList(careList, [...(result.diets || []), ...(result.workouts || [])].slice(0, 8), "Dữ liệu tham chiếu chưa có thông tin chăm sóc.");
  }

  if (warningText) {
    warningText.textContent =
      result.warning ||
      (isUncertain
        ? "Không dùng kết quả này để tự chẩn đoán hoặc tự dùng thuốc. Nếu triệu chứng nặng lên, cần đi khám."
        : "Không thay thế chẩn đoán của bác sĩ. Dữ liệu này phù hợp cho học máy và hỗ trợ tham khảo, không dùng để kê đơn thật.");
  }

  topPredictionsTitle.textContent =
    result.score_type === "rule"
      ? "Kết quả theo rule triệu chứng"
      : result.score_type === "cosine_similarity"
        ? "Độ tương đồng từ mô hình"
        : "Xác suất từ mô hình";
  topPredictions.innerHTML = "";
  if (result.score_type === "rule") {
    const li = document.createElement("li");
    li.textContent = "Rule an toàn được ưu tiên hơn xác suất model.";
    topPredictions.appendChild(li);
  }
  (result.top_predictions || []).forEach((prediction) => {
    const score = prediction.similarity_score ?? prediction.probability;
    const pct = Math.max(0, Math.min(100, Math.round((score || 0) * 100)));

    const li = document.createElement("li");
    li.className = "prediction-row";

    const name = document.createElement("span");
    name.className = "prediction-name";
    name.textContent = prediction.disease_vi || prediction.disease;

    const value = document.createElement("span");
    value.className = "prediction-value";
    value.textContent = `${pct}%`;

    const track = document.createElement("span");
    track.className = "prediction-track";
    const fill = document.createElement("span");
    fill.className = "prediction-fill";
    fill.style.width = `${pct}%`;
    track.appendChild(fill);

    li.append(name, value, track);
    topPredictions.appendChild(li);
  });

  showPage("result");
}

function renderInsufficientInput(result) {
  const matchedLabels = result.matched_symptoms_vi || result.matched_symptom_labels || [];

  currentResult = null;
  renderCaseSummary(result);
  renderSuggestedSymptoms(result);
  resetFeedbackBox(false); // US18: chưa đủ dữ liệu thì không có gì để đánh giá
  if (scoreLabel) {
    scoreLabel.textContent = "Trạng thái";
  }
  confidenceValue.textContent = "Chưa đủ";
  confidenceBar.style.width = "0%";
  setConfidenceLevel("none");
  resultTitle.textContent = result.display_title || "Chưa đủ dữ liệu để gợi ý nhóm thuốc";
  resultSubtitle.textContent = matchedLabels.length
    ? `${matchedLabels.length} triệu chứng đã map: ${matchedLabels.join(", ")}`
    : "Chưa nhận diện đủ triệu chứng trong tập train";
  resultNote.textContent =
    result.error ||
    "Hãy mô tả thêm triệu chứng đi kèm, thời gian khởi phát, mức độ nặng, bệnh nền hoặc thuốc đang dùng.";

  renderList(medicationList, result.medications || [], "Không hiển thị thuốc khi độ tin cậy thấp hoặc dữ liệu đầu vào chưa đủ.");
  renderList(precautionList, result.precautions || [], "Không tự dùng thuốc theo kết quả mô hình. Hãy bổ sung triệu chứng hoặc hỏi bác sĩ/dược sĩ.");
  renderList(careList, result.diets || [], "Ghi thêm bối cảnh như sốt, buồn nôn, nhìn mờ, đau cổ gáy, thời gian khởi phát và mức độ nặng.");
  if (warningText) {
    warningText.textContent = result.warning || "Kết quả đã bị chặn vì chưa đủ tin cậy để gợi ý nhóm thuốc.";
  }
  topPredictionsTitle.textContent = "Không hiển thị dự đoán";
  topPredictions.innerHTML = "";
  showPage("result");
}

async function predict() {
  setMessage("Đang tiền xử lý tiếng Việt và gọi mô hình đã train...");

  const response = await fetch("/api/predict", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      symptoms: [...selectedSymptoms],
      notes: textarea.value,
    }),
  });

  const result = await response.json();
  if (!response.ok) {
    if (result.needs_more_input) {
      renderInsufficientInput(result);
    }
    throw new Error(result.error || "Không gợi ý được nhóm thuốc.");
  }

  setMessage("Dự đoán xong.");
  renderPrediction(result);
}

async function loadSymptoms() {
  try {
    const response = await fetch("/api/symptoms");
    if (!response.ok) {
      throw new Error("Không tải được danh sách triệu chứng.");
    }
    const data = await response.json();
    symptoms = data.symptoms;
    symptomsLoaded = true;
    renderSymptoms();
  } catch (error) {
    symptomList.innerHTML = '<p class="muted-text">Không kết nối được API. Hãy chạy bằng lệnh python backend/app.py.</p>';
    setMessage(error.message, true);
  }
}

// ── US19: DASHBOARD ADMIN ────────────────────────────────────────────────────
const dashboardMessage = document.getElementById("dashboard-message");
const dashboardFrom = document.getElementById("dashboard-from");
const dashboardTo = document.getElementById("dashboard-to");
const dashboardRefresh = document.getElementById("dashboard-refresh");
let dashboardLoading = false;

function setDashboardMessage(message, isError = false) {
  if (!dashboardMessage) return;
  dashboardMessage.textContent = message || "";
  dashboardMessage.classList.toggle("is-error", isError);
}

// SCRUM-80: biểu đồ vẽ bằng Chart.js (vendor cục bộ frontend/vendor/chart.umd.min.js).
let barsChart = null;
let donutChart = null;

function cssVar(name, fallback) {
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
}

// Plugin nhỏ: vẽ % Đồng ý ở tâm donut.
const donutCenterText = {
  id: "donutCenterText",
  afterDraw(chart) {
    const txt = chart.config.options.plugins?.centerText?.text;
    if (!txt) return;
    const { ctx, chartArea } = chart;
    const x = (chartArea.left + chartArea.right) / 2;
    const y = (chartArea.top + chartArea.bottom) / 2;
    ctx.save();
    ctx.font = "700 26px Inter, sans-serif";
    ctx.fillStyle = cssVar("--text", "#0e1b2b");
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(txt, x, y);
    ctx.restore();
  },
};

function renderDashboard(stats) {
  document.getElementById("stat-total-predictions").textContent = (stats.total_predictions || 0).toLocaleString("vi-VN");
  document.getElementById("stat-agree-rate").textContent =
    stats.agree_rate === null || stats.agree_rate === undefined ? "—" : `${stats.agree_rate}%`;
  document.getElementById("stat-feedback-total").textContent = (stats.feedback_total || 0).toLocaleString("vi-VN");

  // Biểu đồ cột: ca dự đoán theo ngày (Chart.js).
  const series = stats.predictions_over_time || [];
  document.getElementById("dashboard-bars-empty").classList.toggle("is-hidden", series.length > 0);
  const barsCanvas = document.getElementById("dashboard-bars-canvas");
  if (barsChart) barsChart.destroy();
  barsChart = new Chart(barsCanvas, {
    type: "bar",
    data: {
      labels: series.map((p) => (p.date || "").slice(5)),
      datasets: [{
        label: "Số ca",
        data: series.map((p) => p.count || 0),
        backgroundColor: cssVar("--primary", "#0b5fb5"),
        borderRadius: 6,
        maxBarThickness: 48,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  // Donut: Đồng ý vs Không đồng ý (Chart.js doughnut).
  const agree = stats.agree_count || 0;
  const disagree = stats.disagree_count || 0;
  const total = agree + disagree;
  const agreePct = total ? Math.round((agree / total) * 100) : 0;
  document.getElementById("dashboard-donut-empty").classList.toggle("is-hidden", total > 0);
  const donutCanvas = document.getElementById("dashboard-donut-canvas");
  if (donutChart) donutChart.destroy();
  donutChart = new Chart(donutCanvas, {
    type: "doughnut",
    data: {
      labels: ["Đồng ý", "Không đồng ý"],
      datasets: [{
        data: total ? [agree, disagree] : [0, 0],
        backgroundColor: [cssVar("--success", "#16a34a"), cssVar("--danger", "#dc2626")],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "62%",
      plugins: {
        legend: { position: "bottom" },
        centerText: { text: total ? `${agreePct}%` : "" },
      },
    },
    plugins: [donutCenterText],
  });

  // Top nhóm thuốc.
  const topGroups = document.getElementById("dashboard-top-groups");
  topGroups.innerHTML = "";
  const groups = stats.top_groups || [];
  if (groups.length === 0) {
    const li = document.createElement("li");
    li.className = "muted-text";
    li.textContent = "Chưa có dữ liệu.";
    topGroups.appendChild(li);
  } else {
    const maxGroup = groups.reduce((m, g) => Math.max(m, g.count || 0), 0) || 1;
    groups.forEach((g) => {
      const li = document.createElement("li");
      li.className = "prediction-row";
      const name = document.createElement("span");
      name.className = "prediction-name";
      name.textContent = g.group;
      const value = document.createElement("span");
      value.className = "prediction-value";
      value.textContent = g.count;
      const track = document.createElement("span");
      track.className = "prediction-track";
      const fill = document.createElement("span");
      fill.className = "prediction-fill";
      fill.style.width = `${Math.round(((g.count || 0) / maxGroup) * 100)}%`;
      track.appendChild(fill);
      li.append(name, value, track);
      topGroups.appendChild(li);
    });
  }
}

async function loadDashboard() {
  if (!isAdminUser() || dashboardLoading) return;
  dashboardLoading = true;
  setDashboardMessage("Đang tải số liệu thống kê...");
  const params = new URLSearchParams();
  if (dashboardFrom?.value) params.set("from", dashboardFrom.value);
  if (dashboardTo?.value) params.set("to", dashboardTo.value);
  const query = params.toString();
  try {
    const response = await fetch(`/api/admin/stats${query ? `?${query}` : ""}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Không tải được số liệu thống kê.");
    }
    renderDashboard(data);
    setDashboardMessage(data.total_predictions === 0 ? "Chưa có ca dự đoán nào được ghi nhận." : "");
    await loadFeedbackStats(query);
    await loadGroupStats(query);
  } catch (error) {
    setDashboardMessage(formatError(error), true);
  } finally {
    dashboardLoading = false;
  }
}

// US22: tải + render thống kê lý do "Không đồng ý".
let rejectBarsChart = null;

function fillTopList(elId, items, labelKey, fallback) {
  const el = document.getElementById(elId);
  if (!el) return;
  el.innerHTML = "";
  if (!items || items.length === 0) {
    const li = document.createElement("li");
    li.className = "muted-text";
    li.textContent = fallback;
    el.appendChild(li);
    return;
  }
  const max = items.reduce((m, it) => Math.max(m, it.count || 0), 0) || 1;
  items.forEach((it) => {
    const li = document.createElement("li");
    li.className = "prediction-row";
    const name = document.createElement("span");
    name.className = "prediction-name";
    name.textContent = it[labelKey];
    const value = document.createElement("span");
    value.className = "prediction-value";
    value.textContent = it.count;
    const track = document.createElement("span");
    track.className = "prediction-track";
    const fill = document.createElement("span");
    fill.className = "prediction-fill";
    fill.style.width = `${Math.round(((it.count || 0) / max) * 100)}%`;
    track.appendChild(fill);
    li.append(name, value, track);
    el.appendChild(li);
  });
}

function renderFeedbackStats(stats) {
  const pill = document.getElementById("reject-total-pill");
  if (pill) pill.textContent = `${(stats.reject_total || 0).toLocaleString("vi-VN")} lượt không đồng ý`;

  const series = stats.reject_over_time || [];
  document.getElementById("reject-bars-empty").classList.toggle("is-hidden", series.length > 0);
  const canvas = document.getElementById("reject-bars-canvas");
  if (rejectBarsChart) rejectBarsChart.destroy();
  rejectBarsChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: series.map((p) => (p.date || "").slice(5)),
      datasets: [{
        label: "Không đồng ý",
        data: series.map((p) => p.count || 0),
        backgroundColor: cssVar("--danger", "#dc2626"),
        borderRadius: 6,
        maxBarThickness: 48,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { y: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  fillTopList("reject-keywords", stats.top_keywords, "keyword", "Chưa có ghi chú lý do.");
  fillTopList("reject-by-group", stats.reject_by_group, "group", "Chưa có dữ liệu.");
}

async function loadFeedbackStats(query) {
  try {
    const response = await fetch(`/api/admin/feedback-stats${query ? `?${query}` : ""}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Không tải được thống kê phản hồi.");
    renderFeedbackStats(data);
  } catch (error) {
    setDashboardMessage(formatError(error), true);
  }
}

// US23: Top nhóm thuốc được dự đoán nhiều nhất (biểu đồ ngang + xếp hạng %).
let groupBarsChart = null;

function renderGroupStats(stats) {
  const groups = stats.groups || [];
  const pill = document.getElementById("group-stats-pill");
  if (pill) pill.textContent = `${stats.distinct_groups || 0} nhóm`;

  document.getElementById("group-bars-empty").classList.toggle("is-hidden", groups.length > 0);
  const canvas = document.getElementById("group-bars-canvas");
  if (groupBarsChart) groupBarsChart.destroy();
  groupBarsChart = new Chart(canvas, {
    type: "bar",
    data: {
      labels: groups.map((g) => g.group),
      datasets: [{
        label: "Số ca dự đoán",
        data: groups.map((g) => g.count || 0),
        backgroundColor: cssVar("--primary", "#0b5fb5"),
        borderRadius: 6,
      }],
    },
    options: {
      indexAxis: "y", // biểu đồ thanh NGANG cho dễ đọc tên nhóm
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: { x: { beginAtZero: true, ticks: { precision: 0 } } },
    },
  });

  // Xếp hạng: tên nhóm + count (percent%)
  const rank = document.getElementById("group-rank");
  rank.innerHTML = "";
  if (groups.length === 0) {
    const li = document.createElement("li");
    li.className = "muted-text";
    li.textContent = "Chưa có dữ liệu.";
    rank.appendChild(li);
    return;
  }
  const max = groups.reduce((m, g) => Math.max(m, g.count || 0), 0) || 1;
  groups.forEach((g, i) => {
    const li = document.createElement("li");
    li.className = "prediction-row";
    const name = document.createElement("span");
    name.className = "prediction-name";
    name.textContent = `${i + 1}. ${g.group}`;
    const value = document.createElement("span");
    value.className = "prediction-value";
    value.textContent = `${g.count} (${g.percent}%)`;
    const track = document.createElement("span");
    track.className = "prediction-track";
    const fill = document.createElement("span");
    fill.className = "prediction-fill";
    fill.style.width = `${Math.round(((g.count || 0) / max) * 100)}%`;
    track.appendChild(fill);
    li.append(name, value, track);
    rank.appendChild(li);
  });
}

async function loadGroupStats(query) {
  try {
    const response = await fetch(`/api/admin/group-stats${query ? `?${query}&limit=10` : "?limit=10"}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Không tải được thống kê nhóm thuốc.");
    renderGroupStats(data);
  } catch (error) {
    setDashboardMessage(formatError(error), true);
  }
}

// ── US27: Từ điển triệu chứng — tìm kiếm nhanh + phân trang ───────────────────
const dictionarySearch = document.getElementById("dictionary-search");
const dictionaryRows = document.getElementById("dictionary-rows");
const dictionaryEmpty = document.getElementById("dictionary-empty");
const dictionaryTotal = document.getElementById("dictionary-total");
const dictionaryMessage = document.getElementById("dictionary-message");
const dictPageInfo = document.getElementById("dict-page-info");
const dictPrev = document.getElementById("dict-prev");
const dictNext = document.getElementById("dict-next");
const DICT_PER_PAGE = 10;
let dictPage = 1;
let dictTotalPages = 0;
let dictDebounce = null;

function renderDictionary(data) {
  const items = data.trieu_chung || [];
  dictTotalPages = data.total_pages || 0;
  dictPage = data.page || 1;
  if (dictionaryTotal) dictionaryTotal.textContent = `${(data.total || 0).toLocaleString("vi-VN")} triệu chứng`;
  dictionaryEmpty.classList.toggle("is-hidden", items.length > 0);
  dictionaryRows.innerHTML = "";
  const startIdx = (dictPage - 1) * DICT_PER_PAGE;
  items.forEach((it, i) => {
    const tr = document.createElement("tr");
    tr.className = "dict-row-clickable";
    tr.title = "Bấm để xem nhóm thuốc liên quan";
    const td0 = document.createElement("td");
    td0.textContent = startIdx + i + 1;
    const td1 = document.createElement("td");
    td1.textContent = it.ten;
    const td2 = document.createElement("td");
    td2.className = "muted-text";
    td2.textContent = it.tu_khoa || "—";
    tr.append(td0, td1, td2);
    tr.addEventListener("click", () => openMappingModal(it.ma, it.ten)); // US28
    dictionaryRows.appendChild(tr);
  });
  if (dictPageInfo) dictPageInfo.textContent = dictTotalPages ? `Trang ${dictPage} / ${dictTotalPages}` : "Trang 0";
  if (dictPrev) dictPrev.disabled = dictPage <= 1;
  if (dictNext) dictNext.disabled = dictPage >= dictTotalPages;
}

async function loadDictionary(page) {
  if (!isAdminUser()) return;
  dictPage = page || 1;
  const q = dictionarySearch ? dictionarySearch.value.trim() : "";
  if (dictionaryMessage) dictionaryMessage.textContent = "Đang tìm...";
  const params = new URLSearchParams({ page: String(dictPage), per_page: String(DICT_PER_PAGE) });
  if (q) params.set("q", q);
  try {
    const response = await fetch(`/api/admin/db/trieu-chung?${params.toString()}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Không tìm được triệu chứng.");
    renderDictionary(data);
    if (dictionaryMessage) dictionaryMessage.textContent = "";
  } catch (error) {
    if (dictionaryMessage) {
      dictionaryMessage.textContent = formatError(error);
      dictionaryMessage.classList.add("is-error");
    }
  }
}

if (dictionarySearch) {
  // Tìm THỜI GIAN THỰC (debounce 250ms), reset về trang 1 khi gõ.
  dictionarySearch.addEventListener("input", () => {
    clearTimeout(dictDebounce);
    dictDebounce = setTimeout(() => loadDictionary(1), 250);
  });
}
if (dictPrev) dictPrev.addEventListener("click", () => { if (dictPage > 1) loadDictionary(dictPage - 1); });
if (dictNext) dictNext.addEventListener("click", () => { if (dictPage < dictTotalPages) loadDictionary(dictPage + 1); });

// ── US28: Modal ánh xạ chi tiết triệu chứng ↔ nhóm thuốc ─────────────────────
const mappingModal = document.getElementById("mapping-modal");
const mappingModalTitle = document.getElementById("mapping-modal-title");
const mappingModalSub = document.getElementById("mapping-modal-sub");
const mappingModalMessage = document.getElementById("mapping-modal-message");
const mappingModalGroups = document.getElementById("mapping-modal-groups");
const mappingModalClose = document.getElementById("mapping-modal-close");

function closeMappingModal() {
  if (mappingModal) mappingModal.classList.add("is-hidden");
}

async function openMappingModal(ma, ten) {
  if (!mappingModal) return;
  mappingModalTitle.textContent = ten || "Chi tiết triệu chứng";
  mappingModalGroups.innerHTML = "";
  mappingModalMessage.textContent = "Đang tải ánh xạ...";
  mappingModalMessage.classList.remove("is-error");
  mappingModal.classList.remove("is-hidden");
  try {
    const response = await fetch(`/api/admin/symptom-mapping?ma=${encodeURIComponent(ma)}`, {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Không tải được ánh xạ.");
    const groups = data.groups || [];
    mappingModalSub.textContent =
      `${data.distinct_groups || 0} nhóm thuốc liên quan · ${(data.total_cases || 0).toLocaleString("vi-VN")} ca trong dữ liệu huấn luyện.`;
    mappingModalMessage.textContent = groups.length ? "" : "Triệu chứng này chưa có ánh xạ nhóm thuốc trong dữ liệu.";
    const max = groups.reduce((m, g) => Math.max(m, g.count || 0), 0) || 1;
    groups.forEach((g, i) => {
      const li = document.createElement("li");
      li.className = "prediction-row";
      const name = document.createElement("span");
      name.className = "prediction-name";
      name.textContent = `${i + 1}. ${g.group}`;
      const value = document.createElement("span");
      value.className = "prediction-value";
      value.textContent = `${g.count.toLocaleString("vi-VN")} (${g.percent}%)`;
      const track = document.createElement("span");
      track.className = "prediction-track";
      const fill = document.createElement("span");
      fill.className = "prediction-fill";
      fill.style.width = `${Math.round(((g.count || 0) / max) * 100)}%`;
      track.appendChild(fill);
      li.append(name, value, track);
      mappingModalGroups.appendChild(li);
    });
  } catch (error) {
    mappingModalMessage.textContent = formatError(error);
    mappingModalMessage.classList.add("is-error");
  }
}

if (mappingModalClose) mappingModalClose.addEventListener("click", closeMappingModal);
if (mappingModal) {
  mappingModal.addEventListener("click", (e) => {
    if (e.target === mappingModal) closeMappingModal(); // bấm nền ngoài -> đóng
  });
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeMappingModal();
});

if (dashboardRefresh) {
  dashboardRefresh.addEventListener("click", () => {
    dashboardLoading = false;
    loadDashboard();
  });
}

// ── US18: phản hồi Đồng ý / Không đồng ý ─────────────────────────────────────
const feedbackBox = document.getElementById("feedback-box");
const feedbackApprove = document.getElementById("feedback-approve");
const feedbackReject = document.getElementById("feedback-reject");
const feedbackThanks = document.getElementById("feedback-thanks");
const feedbackReason = document.getElementById("feedback-reason");
const feedbackReasonText = document.getElementById("feedback-reason-text");
const feedbackReasonSubmit = document.getElementById("feedback-reason-submit");
const feedbackReasonCancel = document.getElementById("feedback-reason-cancel");

function resetFeedbackBox(show) {
  if (!feedbackBox) return;
  feedbackBox.classList.toggle("is-hidden", !show);
  if (feedbackThanks) feedbackThanks.classList.add("is-hidden");
  if (feedbackReason) feedbackReason.classList.add("is-hidden");
  if (feedbackReasonText) feedbackReasonText.value = "";
  [feedbackApprove, feedbackReject].forEach((b) => {
    if (b) {
      b.disabled = false;
      b.classList.remove("is-chosen");
    }
  });
}

async function sendFeedback(verdict, note, button) {
  const group = currentResult?.case_summary?.drug_group || null;
  [feedbackApprove, feedbackReject].forEach((b) => b && (b.disabled = true));
  if (button) button.classList.add("is-chosen");
  try {
    const response = await fetch("/api/feedback", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      },
      body: JSON.stringify({ verdict, predicted_group: group, note: note || "" }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Không gửi được phản hồi.");
    }
    if (feedbackReason) feedbackReason.classList.add("is-hidden");
    if (feedbackThanks) feedbackThanks.classList.remove("is-hidden");
  } catch (error) {
    setMessage(formatError(error), true);
    [feedbackApprove, feedbackReject].forEach((b) => b && (b.disabled = false));
    if (button) button.classList.remove("is-chosen");
  }
}

// Đồng ý: gửi ngay. Không đồng ý (US22): mở ô nhập LÝ DO trước khi gửi.
if (feedbackApprove) feedbackApprove.addEventListener("click", () => sendFeedback("APPROVE", "", feedbackApprove));
if (feedbackReject) {
  feedbackReject.addEventListener("click", () => {
    feedbackReject.classList.add("is-chosen");
    if (feedbackReason) feedbackReason.classList.remove("is-hidden");
    if (feedbackReasonText) feedbackReasonText.focus();
  });
}
if (feedbackReasonSubmit) {
  feedbackReasonSubmit.addEventListener("click", () =>
    sendFeedback("REJECT", feedbackReasonText ? feedbackReasonText.value.trim() : "", feedbackReject)
  );
}
if (feedbackReasonCancel) {
  feedbackReasonCancel.addEventListener("click", () => {
    if (feedbackReason) feedbackReason.classList.add("is-hidden");
    if (feedbackReject) feedbackReject.classList.remove("is-chosen");
    [feedbackApprove, feedbackReject].forEach((b) => b && (b.disabled = false));
  });
}

authSwitchButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showAuthView(button.dataset.authTarget);
  });
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAuthMessage(loginMessage, "Đang đăng nhập...");
  try {
    const data = await authRequest("/api/auth/login", {
      email: document.getElementById("login-email").value,
      password: document.getElementById("login-password").value,
    });
    setAuthMessage(loginMessage, "");
    handleAuthSuccess(data);
  } catch (error) {
    setAuthMessage(loginMessage, formatError(error), true);
  }
});

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAuthMessage(registerMessage, "Đang tạo tài khoản...");
  try {
    const data = await authRequest("/api/auth/register", {
      name: document.getElementById("register-name").value,
      email: document.getElementById("register-email").value,
      password: document.getElementById("register-password").value,
    });
    setAuthMessage(registerMessage, "");
    handleAuthSuccess(data);
  } catch (error) {
    setAuthMessage(registerMessage, formatError(error), true);
  }
});

forgotForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  const email = document.getElementById("forgot-email").value;
  setAuthMessage(forgotMessage, "Đang tạo mã đặt lại...");
  try {
    const data = await authRequest("/api/auth/forgot-password", { email });
    document.getElementById("reset-email").value = email;
    if (data.reset_code) {
      document.getElementById("reset-code").value = data.reset_code;
      setAuthMessage(forgotMessage, `${data.message} Mã của bạn: ${data.reset_code}`);
      setAuthMessage(resetMessage, "Mã đặt lại đã được điền tự động.");
    } else {
      setAuthMessage(forgotMessage, data.message);
      setAuthMessage(resetMessage, data.message);
    }
    showAuthView("reset");
  } catch (error) {
    setAuthMessage(forgotMessage, formatError(error), true);
  }
});

resetForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAuthMessage(resetMessage, "Đang đặt lại mật khẩu...");
  try {
    const data = await authRequest("/api/auth/reset-password", {
      email: document.getElementById("reset-email").value,
      reset_code: document.getElementById("reset-code").value,
      password: document.getElementById("reset-password").value,
    });
    setAuthMessage(resetMessage, "");
    handleAuthSuccess(data);
  } catch (error) {
    setAuthMessage(resetMessage, formatError(error), true);
  }
});

async function logoutCurrentUser() {
  if (authToken) {
    try {
      await fetch("/api/auth/logout", {
        method: "POST",
        headers: { Authorization: `Bearer ${authToken}` },
      });
    } catch {
      // Local logout still clears the browser session if the API is unavailable.
    }
  }

  authToken = "";
  currentUser = null;
  savedResults = [];
  localStorage.removeItem(AUTH_TOKEN_KEY);
  localStorage.removeItem(AUTH_USER_KEY);
  document.querySelectorAll(".user-history-card").forEach((card) => card.remove());
  showAuthScreen("login");
}

logoutButton.addEventListener("click", logoutCurrentUser);
profileLogoutButton.addEventListener("click", logoutCurrentUser);

navButtons.forEach((button) => {
  button.addEventListener("click", () => showPage(button.dataset.page));
});

textarea.addEventListener("input", updateCharCount);

clearButton.addEventListener("click", () => {
  textarea.value = "";
  selectedSymptoms.clear();
  updateCharCount();
  updateSelectedCount();
  renderSymptoms(symptomSearch.value);
  textarea.focus();
});

exampleButton.addEventListener("click", () => {
  textarea.value = sampleCase;
  selectedSymptoms.clear();
  updateCharCount();
  updateSelectedCount();
  renderSymptoms(symptomSearch.value);
  textarea.focus();
});

// ── US29: bệnh án mẫu — picker Trang Chủ (SCRUM-119) + quản lý admin (SCRUM-116) ──
const samplePicker = document.getElementById("sample-picker");
const sampleSelect = document.getElementById("sample-select");
const sampleForm = document.getElementById("sample-form");
const sampleFormMessage = document.getElementById("sample-form-message");
const samplesList = document.getElementById("samples-list");
const samplesCount = document.getElementById("samples-count");
const samplesEmpty = document.getElementById("samples-empty");
let sampleCache = [];

async function fetchSamples() {
  const response = await fetch("/api/benh-an-mau", {
    headers: { Authorization: `Bearer ${authToken}` },
  });
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || "Không tải được bệnh án mẫu.");
  sampleCache = data.benh_an_mau || [];
  return sampleCache;
}

async function loadSamplePicker() {
  if (!sampleSelect) return;
  try {
    const items = await fetchSamples();
    sampleSelect.innerHTML = '<option value="">— Chọn bệnh án mẫu —</option>';
    items.forEach((s) => {
      const opt = document.createElement("option");
      opt.value = String(s.ma);
      opt.textContent = s.tieu_de;
      sampleSelect.appendChild(opt);
    });
    if (samplePicker) samplePicker.classList.toggle("is-hidden", items.length === 0);
  } catch {
    if (samplePicker) samplePicker.classList.add("is-hidden");
  }
}

if (sampleSelect) {
  // SCRUM-119: chọn mẫu -> nạp nội dung vào ô nhập liệu.
  sampleSelect.addEventListener("change", () => {
    const s = sampleCache.find((x) => String(x.ma) === sampleSelect.value);
    if (!s) return;
    textarea.value = s.noi_dung;
    selectedSymptoms.clear();
    updateCharCount();
    updateSelectedCount();
    renderSymptoms(symptomSearch.value);
    setMessage(`Đã nạp bệnh án mẫu: ${s.tieu_de}`);
    textarea.focus();
  });
}

function renderSamplesAdmin() {
  if (!samplesList) return;
  samplesList.innerHTML = "";
  if (samplesCount) samplesCount.textContent = `${sampleCache.length} mẫu`;
  if (samplesEmpty) samplesEmpty.classList.toggle("is-hidden", sampleCache.length > 0);
  sampleCache.forEach((s) => {
    const card = document.createElement("article");
    card.className = "history-card";
    const title = document.createElement("h2");
    title.textContent = s.tieu_de;
    const body = document.createElement("p");
    body.textContent = s.noi_dung;
    const meta = document.createElement("p");
    meta.className = "muted-text";
    meta.textContent = s.mo_ta || "";
    const del = document.createElement("button");
    del.className = "secondary-button compact";
    del.type = "button";
    del.textContent = "Xóa";
    del.addEventListener("click", () => deleteSample(s.ma));
    card.append(title, body, meta, del);
    samplesList.appendChild(card);
  });
}

async function loadSamples() {
  if (!isAdminUser()) return;
  try {
    await fetchSamples();
    renderSamplesAdmin();
  } catch (error) {
    if (sampleFormMessage) {
      sampleFormMessage.textContent = formatError(error);
      sampleFormMessage.classList.add("is-error");
    }
  }
}

async function deleteSample(ma) {
  try {
    const response = await fetch(`/api/admin/benh-an-mau/${ma}`, {
      method: "DELETE",
      headers: { Authorization: `Bearer ${authToken}` },
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Không xóa được.");
    }
    await loadSamples();
    loadSamplePicker();
  } catch (error) {
    if (sampleFormMessage) {
      sampleFormMessage.textContent = formatError(error);
      sampleFormMessage.classList.add("is-error");
    }
  }
}

if (sampleForm) {
  sampleForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    sampleFormMessage.classList.remove("is-error");
    sampleFormMessage.textContent = "Đang lưu...";
    try {
      const response = await fetch("/api/admin/benh-an-mau", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({
          tieu_de: document.getElementById("sample-tieu-de").value,
          noi_dung: document.getElementById("sample-noi-dung").value,
          mo_ta: document.getElementById("sample-mo-ta").value,
        }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "Không thêm được mẫu.");
      sampleForm.reset();
      sampleFormMessage.textContent = "Đã thêm bệnh án mẫu.";
      await loadSamples();
      loadSamplePicker();
    } catch (error) {
      sampleFormMessage.textContent = formatError(error);
      sampleFormMessage.classList.add("is-error");
    }
  });
}

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  const submitButton = form.querySelector('button[type="submit"]');
  setFormLoading(submitButton, true);
  try {
    await predict();
  } catch (error) {
    setMessage(formatError(error), true);
  } finally {
    setFormLoading(submitButton, false);
  }
});

symptomSearch.addEventListener("input", (event) => {
  renderSymptoms(event.target.value);
});

historySearch.addEventListener("input", (event) => {
  const query = event.target.value.trim().toLowerCase();

  document.querySelectorAll(".history-card").forEach((card) => {
    const haystack = card.dataset.search.toLowerCase();
    card.classList.toggle("is-hidden", query !== "" && !haystack.includes(query));
  });
  updateHistoryEmptyState();
});

saveResultButton.addEventListener("click", () => {
  if (currentResult) {
    savedResults.push({
      disease: currentResult.display_title || currentResult.disease_vi || currentResult.disease,
      symptoms: currentResult.matched_symptoms_vi || [],
      notes: textarea.value.trim(),
      savedAt: new Date().toLocaleDateString("vi-VN"),
    });
    saveHistory();
    historyList.prepend(createHistoryCard(savedResults[savedResults.length - 1]));
    updateHistoryEmptyState();
    renderRecentActivity();
  }
  showPage("history");
});

const THEME_KEY = "pharmaPredictTheme";
const themeToggles = document.querySelectorAll(".theme-toggle");

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.setAttribute("data-theme", isDark ? "dark" : "light");
  const actionLabel = isDark ? "Chuyển sang giao diện sáng" : "Chuyển sang giao diện tối";
  themeToggles.forEach((button) => {
    button.setAttribute("aria-pressed", String(isDark));
    button.setAttribute("aria-label", actionLabel);
    button.setAttribute("title", actionLabel);
    const icon = button.querySelector(".material-symbols-outlined");
    if (icon) {
      icon.textContent = isDark ? "light_mode" : "dark_mode";
    }
    const label = button.querySelector(".theme-toggle-label");
    if (label) {
      label.textContent = isDark ? "Giao diện sáng" : "Giao diện tối";
    }
  });
}

function initTheme() {
  let stored = null;
  try {
    stored = localStorage.getItem(THEME_KEY);
  } catch {
    stored = null;
  }
  const prefersDark = window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches;
  applyTheme(stored || (prefersDark ? "dark" : "light"));
}

themeToggles.forEach((button) => {
  button.addEventListener("click", () => {
    const next = document.documentElement.getAttribute("data-theme") === "dark" ? "light" : "dark";
    try {
      localStorage.setItem(THEME_KEY, next);
    } catch {
      // Bỏ qua nếu localStorage không khả dụng; vẫn đổi theme trong phiên.
    }
    applyTheme(next);
  });
});

initTheme();
updateCharCount();
updateSelectedCount();
initializeAuth();

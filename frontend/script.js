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
}

function showAuthenticatedApp() {
  authScreen.classList.add("is-hidden");
  appShell.classList.remove("is-hidden");
  updateUserUi();
  loadSavedHistory();
  renderSavedHistory();
  if (!symptomsLoaded) {
    loadSymptoms();
  }
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

function showPage(pageName) {
  pages.forEach((page) => {
    page.classList.toggle("is-active", page.id === `page-${pageName}`);
  });

  navButtons.forEach((button) => {
    button.classList.toggle("is-active", button.dataset.page === pageName);
  });

  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateCharCount() {
  charCount.textContent = `${textarea.value.length} / 2000 ký tự`;
}

function setMessage(message, isError = false) {
  formMessage.textContent = message;
  formMessage.classList.toggle("is-error", isError);
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
        setMessage(error.message, true);
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
  if (scoreLabel) {
    scoreLabel.textContent = scoreText;
  }
  confidenceValue.textContent = isRuleBased ? "Theo rule" : `${confidence}%`;
  confidenceBar.style.width = isRuleBased ? "100%" : `${confidence}%`;
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
    resultNote.textContent = `${result.description || "Dữ liệu tham chiếu chưa có mô tả cho bệnh này."}${guidanceSourceText}`;
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
    const li = document.createElement("li");
    const score = prediction.similarity_score ?? prediction.probability;
    li.textContent = `${prediction.disease_vi || prediction.disease}: ${Math.round(score * 100)}%`;
    topPredictions.appendChild(li);
  });

  showPage("result");
}

function renderInsufficientInput(result) {
  const matchedLabels = result.matched_symptoms_vi || result.matched_symptom_labels || [];

  currentResult = null;
  renderCaseSummary(result);
  renderSuggestedSymptoms(result);
  if (scoreLabel) {
    scoreLabel.textContent = "Trạng thái";
  }
  confidenceValue.textContent = "Chưa đủ";
  confidenceBar.style.width = "0%";
  resultTitle.textContent = "Chưa đủ dữ liệu để gợi ý nhóm thuốc";
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
    setAuthMessage(loginMessage, error.message, true);
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
    setAuthMessage(registerMessage, error.message, true);
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
    setAuthMessage(forgotMessage, error.message, true);
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
    setAuthMessage(resetMessage, error.message, true);
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

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await predict();
  } catch (error) {
    setMessage(error.message, true);
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
  }
  showPage("history");
});

updateCharCount();
updateSelectedCount();
initializeAuth();

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
const profileForm = document.getElementById("profile-form");
const profileFullname = document.getElementById("profile-fullname");
const profileEmail = document.getElementById("profile-email");
const profilePhone = document.getElementById("profile-phone");
const profileSpecialty = document.getElementById("profile-specialty");
const profileMessage = document.getElementById("profile-message");
const profileCancelButton = document.getElementById("profile-cancel");

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

const API_BASE_URL = "http://127.0.0.1:5000"; 

async function authRequest(endpoint, payload) {
  const response = await fetch(API_BASE_URL + endpoint, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.message || data.error || "Không xử lý được yêu cầu.");
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
  renderRecentActivity();
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

function setProfileMessage(message, isError = false) {
  if (!profileMessage) return;
  profileMessage.textContent = message;
  profileMessage.classList.toggle("is-error", isError);
}

function setFormLoading(button, isLoading) {
  if (!button) return;
  button.disabled = isLoading;
  const icon = button.querySelector(".material-symbols-outlined");
  if (icon) {
    icon.style.opacity = isLoading ? "0.5" : "1";
  }
}

async function loadProfileData() {
  try {
    const response = await fetch("/api/users/profile", {
      headers: { Authorization: `Bearer ${authToken}` },
    });
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || "Không thể tải dữ liệu hồ sơ.");
    }
    
    // Populate form with current data
    profileFullname.value = data.fullName || "";
    profileEmail.value = data.email || "";
    profilePhone.value = data.phoneNumber || "";
    profileSpecialty.value = data.specialty || "";
  } catch (error) {
    setProfileMessage(formatError(error), true);
  }
}

async function saveProfileData(event) {
  event.preventDefault();
  
  // Validation
  if (!profileFullname.value.trim()) {
    setProfileMessage("Vui lòng nhập họ tên.", true);
    return;
  }
  
  const submitButton = profileForm.querySelector('button[type="submit"]');
  setFormLoading(submitButton, true);
  setProfileMessage("");
  
  try {
    const response = await fetch("/api/users/profile", {
      method: "PUT",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${authToken}`,
      },
      body: JSON.stringify({
        fullName: profileFullname.value.trim(),
        phoneNumber: profilePhone.value.trim(),
        specialty: profileSpecialty.value.trim(),
      }),
    });
    
    const data = await response.json();
    if (!response.ok) {
      throw new Error(data.error || data.message || "Không thể cập nhật hồ sơ.");
    }
    
    // Update local user data
    currentUser = data;
    localStorage.setItem(AUTH_USER_KEY, JSON.stringify(currentUser));
    updateUserUi();
    
    setProfileMessage("Cập nhật hồ sơ thành công!", false);
    setTimeout(() => {
      setProfileMessage("");
    }, 3000);
  } catch (error) {
    setProfileMessage(formatError(error), true);
  } finally {
    setFormLoading(submitButton, false);
  }
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

authSwitchButtons.forEach((button) => {
  button.addEventListener("click", () => {
    showAuthView(button.dataset.authTarget);
  });
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();
  setAuthMessage(loginMessage, "Đang xác thực với máy chủ...");
  
  const inputEmail = document.getElementById("login-email").value;
  const inputPassword = document.getElementById("login-password").value;

  try {
    const data = await authRequest("/api/login", {
      email: inputEmail,
      password: inputPassword,
    });
    
    setAuthMessage(loginMessage, "");
    
    handleAuthSuccess({
      token: data.token,
      user: data.user || { name: "Bác sĩ", email: inputEmail },
    });
    
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
      await authRequest("/api/logout", {});
    } catch (e) {
      console.log("Backend không phản hồi, tiến hành đăng xuất local:", e);
    }
  }

  authToken = "";
  currentUser = null;
  savedResults = [];
  localStorage.removeItem(AUTH_TOKEN_KEY); 
  localStorage.removeItem(AUTH_USER_KEY);     
  document.querySelectorAll(".user-history-card").forEach((card) => card.remove());
  showAuthScreen("login"); 
  alert("Bạn đã đăng xuất an toàn khỏi hệ thống!");
}

logoutButton.addEventListener("click", logoutCurrentUser);
if (profileLogoutButton) profileLogoutButton.addEventListener("click", logoutCurrentUser);

navButtons.forEach((button) => {
  button.addEventListener("click", () => {
      showPage(button.dataset.page);
      // Tự động load dữ liệu hồ sơ khi bấm vào tab "Hồ sơ"
      if (button.dataset.page === "about") {
          loadProfileData();
      }
  });
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

// --- GẮN SỰ KIỆN KÍCH HOẠT SCRUM-40 VÀO NÚT LƯU ---
if (profileForm) {
    profileForm.addEventListener("submit", saveProfileData);
}

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
    }
    applyTheme(next);
  });
});
// --- XỬ LÝ ĐỔI MẬT KHẨU ---
const passwordForm = document.getElementById("password-form");
if (passwordForm) {
    passwordForm.addEventListener("submit", async (e) => {
        e.preventDefault();
        const oldPassword = document.getElementById("old-password").value;
        const newPassword = document.getElementById("new-password").value;
        const confirmPassword = document.getElementById("confirm-password").value;
        const msgEl = document.getElementById("password-message");
        if (newPassword !== confirmPassword) {
            msgEl.textContent = "❌ Mật khẩu mới không khớp nhau!";
            msgEl.style.color = "red";
            return;
        }
        if (oldPassword === newPassword) {
            msgEl.textContent = "❌ Mật khẩu mới phải khác mật khẩu cũ!";
            msgEl.style.color = "red";
            return;
        }

        msgEl.textContent = "⏳ Đang xử lý...";
        msgEl.style.color = "blue";

        try {
            const token = localStorage.getItem("token") || localStorage.getItem("pharmaPredictAuthToken");
            
            const response = await fetch("http://127.0.0.1:5000/api/users/change-password", {
                method: "PUT",
                headers: {
                    "Content-Type": "application/json",
                    "Authorization": `Bearer ${token}`
                },
                body: JSON.stringify({
                    old_password: oldPassword,
                    new_password: newPassword
                })
            });

            const data = await response.json();
            
            if (response.ok) {
                msgEl.textContent = "✅ Đổi mật khẩu thành công!";
                msgEl.style.color = "green";
                passwordForm.reset(); 
            } else {
                msgEl.textContent = "❌ " + (data.error || "Lỗi khi đổi mật khẩu.");
                msgEl.style.color = "red";
            }
        } catch (err) {
            msgEl.textContent = "❌ Không thể kết nối tới máy chủ.";
            msgEl.style.color = "red";
        }
    });
}
initTheme();
updateCharCount();
updateSelectedCount();
initializeAuth();

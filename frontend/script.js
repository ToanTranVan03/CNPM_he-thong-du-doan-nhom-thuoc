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
const historyFilterToggle = document.getElementById("history-filter-toggle");
const historyFilterPanel = document.getElementById("history-filter-panel");
const historyDateFilter = document.getElementById("history-date-filter");
const historyMessage = document.getElementById("history-message");
const historyClearButton = document.getElementById("history-clear");
const historyExportExcel = document.getElementById("history-export-excel");
const historyExportPdf = document.getElementById("history-export-pdf");
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
    } else {
      savedResults = savedResults
        .filter((entry) => entry && typeof entry === "object")
        .slice(-20)
        .map((entry) => ({ ...entry, id: entry.id || makeHistoryId() }));
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
  const initials = initialsForName(displayName, displayEmail);
  userName.textContent = displayName;
  userEmail.textContent = displayEmail;
  userAvatar.textContent = initials;
  // Trang Hồ sơ
  const setText = (id, val) => { const el = document.getElementById(id); if (el) el.textContent = val; };
  const setVal = (id, val) => { const el = document.getElementById(id); if (el) el.value = val; };
  setText("profile-avatar", initials);
  setText("profile-name-display", displayName);
  setText("profile-email-display", displayEmail);
  setVal("profile-name-input", displayName);
  setVal("profile-email-input", displayEmail);
  const isAdmin = currentUser?.role === "admin";
  setText("profile-role", isAdmin ? "Quản trị viên" : "Người dùng");
  const roleChip = document.getElementById("profile-role-chip");
  if (roleChip) roleChip.classList.toggle("is-admin", isAdmin);
  setText("profile-stat-saved", String((typeof savedResults !== "undefined" && savedResults) ? savedResults.length : 0));
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

const ADMIN_PAGES = new Set(["dashboard", "admin-history", "dictionary", "drug-admin", "feedback-admin"]);

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
  } else if (pageName === "admin-history") {
    loadAdminHistory(1);
  } else if (pageName === "dictionary") {
    loadDictionary(1);
  } else if (pageName === "drug-admin") {
    loadDrugAdmin();
  } else if (pageName === "feedback-admin") {
    loadFeedbackAdmin(1);
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

function makeHistoryId() {
  if (globalThis.crypto?.randomUUID) return globalThis.crypto.randomUUID();
  return `history-${Date.now()}-${Math.random().toString(16).slice(2)}`;
}

function saveHistory() {
  savedResults = savedResults.slice(-20);
  try {
    localStorage.setItem(historyStorageKey(), JSON.stringify(savedResults));
    return true;
  } catch {
    return false;
  }
}

function addPredictionToHistory(result, notes) {
  const entry = {
    id: makeHistoryId(),
    disease: result.display_title || result.disease_vi || result.disease || "Chưa đủ dữ liệu để gợi ý",
    symptoms: result.matched_symptoms_vi || result.matched_symptom_labels || [],
    notes: String(notes || "").trim(),
    savedAt: new Date().toLocaleDateString("vi-VN"),
    savedAtIso: new Date().toISOString(),
  };
  savedResults.push(entry);
  const saved = saveHistory();
  renderSavedHistory();
  renderRecentActivity();
  if (!saved) setAuthMessage(historyMessage, "Trình duyệt không cho phép lưu lịch sử.", true);
  return saved;
}

function deleteHistoryEntry(entry) {
  if (!confirm(`Xóa kết quả “${entry.disease || "dự đoán"}”?`)) return;
  savedResults = savedResults.filter((item) => item.id !== entry.id);
  saveHistory();
  renderSavedHistory();
  renderRecentActivity();
  setAuthMessage(historyMessage, "Đã xóa kết quả khỏi lịch sử.");
}

function historyEntryDate(entry) {
  if (entry.savedAtIso) {
    const parsed = new Date(entry.savedAtIso);
    if (!Number.isNaN(parsed.getTime())) return parsed;
  }
  const match = String(entry.savedAt || "").match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})$/);
  return match ? new Date(Number(match[3]), Number(match[2]) - 1, Number(match[1])) : null;
}

function historyEntryMatches(entry) {
  const query = (historySearch?.value || "").trim().toLowerCase();
  const symptoms = Array.isArray(entry.symptoms) ? entry.symptoms : [];
  const haystack = `${entry.disease || ""} ${entry.notes || ""} ${symptoms.join(" ")} ${entry.savedAt || ""}`.toLowerCase();
  if (query && !haystack.includes(query)) return false;

  const period = historyDateFilter?.value || "all";
  if (period === "all") return true;
  const date = historyEntryDate(entry);
  if (!date) return false;
  const now = new Date();
  const start = new Date(now.getFullYear(), now.getMonth(), now.getDate());
  if (period === "today") return date >= start;
  start.setDate(start.getDate() - Number(period) + 1);
  return date >= start;
}

function filteredHistoryEntries() {
  return savedResults.filter(historyEntryMatches);
}

function openHistoryDetail(entry) {
  const modal = document.getElementById("history-detail-modal");
  const body = document.getElementById("history-detail-body");
  if (!modal || !body) return;
  const symptoms = Array.isArray(entry.symptoms) ? entry.symptoms.join(", ") : "";
  const fields = [
    ["Ngày lưu", entry.savedAt || "—"],
    ["Kết quả dự đoán", entry.disease || "—"],
    ["Triệu chứng", symptoms || "Chưa rõ triệu chứng"],
    ["Mô tả đã nhập", entry.notes || "Không có mô tả"],
  ];
  body.innerHTML = fields.map(([key, value]) => `<dt>${ahEscape(key)}</dt><dd>${ahEscape(value)}</dd>`).join("");
  modal.classList.remove("is-hidden");
  document.getElementById("history-detail-close")?.focus();
}

function createHistoryCard(entry) {
  const card = document.createElement("article");
  card.className = "history-card user-history-card";
  const symptoms = Array.isArray(entry.symptoms) ? entry.symptoms : [];
  card.dataset.search = `${entry.disease || ""} ${entry.notes || ""} ${symptoms.join(" ")} ${entry.savedAt || ""}`.toLowerCase();

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
  summary.textContent = `${symptoms.join(", ") || "Chưa rõ triệu chứng"} - ${entry.notes || "Không có mô tả."}`;

  const actions = document.createElement("div");
  actions.className = "history-card-actions";

  const deleteButton = document.createElement("button");
  deleteButton.className = "icon-button history-delete-button";
  deleteButton.type = "button";
  deleteButton.setAttribute("aria-label", `Xóa ${entry.disease || "dự đoán"}`);
  deleteButton.title = "Xóa lịch sử";
  const deleteIcon = document.createElement("span");
  deleteIcon.className = "material-symbols-outlined";
  deleteIcon.setAttribute("aria-hidden", "true");
  deleteIcon.textContent = "delete";
  deleteButton.appendChild(deleteIcon);
  deleteButton.addEventListener("click", (event) => {
    event.stopPropagation();
    deleteHistoryEntry(entry);
  });

  const button = document.createElement("button");
  button.className = "icon-button";
  button.type = "button";
  button.setAttribute("aria-label", `Xem chi tiết ${entry.disease || "dự đoán"}`);

  const icon = document.createElement("span");
  icon.className = "material-symbols-outlined";
  icon.setAttribute("aria-hidden", "true");
  icon.textContent = "chevron_right";

  topLine.append(status, time);
  button.appendChild(icon);
  button.addEventListener("click", (event) => {
    event.stopPropagation();
    openHistoryDetail(entry);
  });
  actions.append(deleteButton, button);
  card.append(topLine, title, summary, actions);
  card.addEventListener("click", () => openHistoryDetail(entry));
  return card;
}

function renderSavedHistory() {
  document.querySelectorAll(".user-history-card").forEach((card) => card.remove());
  savedResults
    .slice()
    .reverse()
    .forEach((entry) => {
      historyList.appendChild(createHistoryCard(entry));
    });
  applyHistoryFilters();
}

function applyHistoryFilters() {
  const entries = savedResults.slice().reverse();
  document.querySelectorAll(".user-history-card").forEach((card, index) => {
    card.classList.toggle("is-hidden", !entries[index] || !historyEntryMatches(entries[index]));
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
      desc.textContent = "Không có mục nào khớp với từ khóa hoặc bộ lọc hiện tại.";
    }
  }
}

async function exportPersonalHistory(format) {
  const entries = filteredHistoryEntries();
  if (entries.length === 0) {
    setAuthMessage(historyMessage, "Không có dữ liệu phù hợp để xuất.", true);
    return;
  }
  const button = format === "xlsx" ? historyExportExcel : historyExportPdf;
  if (button) button.disabled = true;
  setAuthMessage(historyMessage, `Đang tạo file ${format === "xlsx" ? "Excel" : "PDF"}...`);
  try {
    const response = await fetch(`/api/history/export.${format}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
      },
      body: JSON.stringify({ entries }),
    });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Không tạo được báo cáo.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `lich_su_du_doan.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    setAuthMessage(historyMessage, `Đã xuất ${entries.length} kết quả.`);
  } catch (error) {
    setAuthMessage(historyMessage, formatError(error), true);
  } finally {
    if (button) button.disabled = false;
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
  // Vòng donut độ tin cậy (đồng bộ với mức màu qua data-level)
  const donutArc = document.getElementById("confidence-donut-arc");
  const donutVal = document.getElementById("confidence-donut-value");
  if (donutArc) {
    const C = 2 * Math.PI * 52;
    const shown = isRuleBased ? 0 : Math.max(0, Math.min(100, confidencePct || 0));
    donutArc.style.strokeDasharray = C.toFixed(1);
    donutArc.style.strokeDashoffset = (C * (1 - shown / 100)).toFixed(1);
  }
  if (donutVal) donutVal.textContent = isRuleBased ? "Quy tắc" : `${confidence}%`;
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

  // Vẫn giữ result để "Lưu kết quả" hoạt động (lịch sử ghi cả ca chưa đủ tin cậy).
  // Feedback đã bị ẩn ở ca này nên không gửi nhầm.
  currentResult = result;
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
  const notes = textarea.value.trim();

  const response = await fetch("/api/predict", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...(authToken ? { Authorization: `Bearer ${authToken}` } : {}),
    },
    body: JSON.stringify({
      symptoms: [...selectedSymptoms],
      notes,
    }),
  });

  const result = await response.json();
  if (!response.ok) {
    if (result.needs_more_input) {
      renderInsufficientInput(result);
      addPredictionToHistory(result, notes);
    }
    throw new Error(result.error || "Không gợi ý được nhóm thuốc.");
  }

  setMessage("Dự đoán xong.");
  renderPrediction(result);
  addPredictionToHistory(result, notes);
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
    const td3 = document.createElement("td");
    td3.className = "admin-row-actions";
    const eBtn = document.createElement("button");
    eBtn.className = "text-button";
    eBtn.type = "button";
    eBtn.textContent = "Sửa";
    eBtn.addEventListener("click", (ev) => {
      ev.stopPropagation();
      document.getElementById("tc-edit-ma").value = it.ma;
      document.getElementById("tc-ten").value = it.ten;
      document.getElementById("tc-tu-khoa").value = it.tu_khoa || "";
      document.getElementById("tc-submit").textContent = "Lưu sửa";
      document.getElementById("tc-cancel").hidden = false;
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
    const dBtn = document.createElement("button");
    dBtn.className = "text-button danger";
    dBtn.type = "button";
    dBtn.textContent = "Xóa";
    dBtn.addEventListener("click", async (ev) => {
      ev.stopPropagation();
      if (!confirm(`Xóa triệu chứng "${it.ten}"?`)) return;
      const r = await fetch(`/api/admin/db/trieu-chung/${it.ma}`, { method: "DELETE", headers: { Authorization: `Bearer ${authToken}` } });
      if (r.ok) loadDictionary(dictPage);
    });
    td3.append(eBtn, dBtn);
    tr.append(td0, td1, td2, td3);
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

// PORT: thêm/sửa triệu chứng trong từ điển
const tcForm = document.getElementById("tc-form");
const tcMessage = document.getElementById("tc-message");
const tcEditMa = document.getElementById("tc-edit-ma");
const tcSubmit = document.getElementById("tc-submit");
const tcCancel = document.getElementById("tc-cancel");
function resetTcForm() {
  if (tcForm) tcForm.reset();
  if (tcEditMa) tcEditMa.value = "";
  if (tcSubmit) tcSubmit.textContent = "Thêm triệu chứng";
  if (tcCancel) tcCancel.hidden = true;
}
if (tcForm) {
  tcForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const ma = tcEditMa.value;
    const body = JSON.stringify({ ten: document.getElementById("tc-ten").value, tu_khoa: document.getElementById("tc-tu-khoa").value });
    const url = ma ? `/api/admin/db/trieu-chung/${ma}` : "/api/admin/db/trieu-chung";
    tcMessage.classList.remove("is-error");
    try {
      const r = await fetch(url, { method: ma ? "PUT" : "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` }, body });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Không lưu được.");
      resetTcForm();
      tcMessage.textContent = ma ? "Đã cập nhật triệu chứng." : "Đã thêm triệu chứng.";
      loadDictionary(ma ? dictPage : 1);
    } catch (error) {
      tcMessage.textContent = formatError(error);
      tcMessage.classList.add("is-error");
    }
  });
}
if (tcCancel) tcCancel.addEventListener("click", resetTcForm);

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

// ── Hồ sơ: cập nhật họ tên (gọi /api/auth/profile) ──────────────────────────
const profileInfoForm = document.getElementById("profile-info-form");
if (profileInfoForm) {
  profileInfoForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const msg = document.getElementById("profile-info-message");
    const name = document.getElementById("profile-name-input").value.trim();
    if (msg) { msg.textContent = ""; msg.classList.remove("is-error"); }
    try {
      const res = await fetch("/api/auth/profile", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ name }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Không cập nhật được hồ sơ.");
      currentUser = data.user;
      localStorage.setItem(AUTH_USER_KEY, JSON.stringify(currentUser));
      updateUserUi();
      if (msg) { msg.textContent = "Đã lưu thay đổi."; }
    } catch (error) {
      if (msg) { msg.textContent = formatError(error); msg.classList.add("is-error"); }
    }
  });
}

// ── Hồ sơ: đổi mật khẩu (gọi /api/auth/change-password) ─────────────────────
const profilePwForm = document.getElementById("profile-password-form");
if (profilePwForm) {
  profilePwForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const msg = document.getElementById("profile-pw-message");
    const cur = document.getElementById("profile-current-pw").value;
    const np = document.getElementById("profile-new-pw").value;
    const cp = document.getElementById("profile-confirm-pw").value;
    if (msg) { msg.textContent = ""; msg.classList.remove("is-error"); }
    if (np !== cp) {
      if (msg) { msg.textContent = "Mật khẩu nhập lại không khớp."; msg.classList.add("is-error"); }
      return;
    }
    try {
      const res = await fetch("/api/auth/change-password", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
        body: JSON.stringify({ current_password: cur, new_password: np }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Không đổi được mật khẩu.");
      if (data.token) { authToken = data.token; localStorage.setItem(AUTH_TOKEN_KEY, authToken); }
      if (data.user) { currentUser = data.user; localStorage.setItem(AUTH_USER_KEY, JSON.stringify(currentUser)); }
      profilePwForm.reset();
      if (msg) { msg.textContent = "Đổi mật khẩu thành công."; }
    } catch (error) {
      if (msg) { msg.textContent = formatError(error); msg.classList.add("is-error"); }
    }
  });
}

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

// ── PORT: Quản lý thuốc (CRUD nhóm thuốc + thuốc) ────────────────────────────
const dgForm = document.getElementById("dg-form");
const dgList = document.getElementById("dg-list");
const dgCount = document.getElementById("dg-count");
const dgMessage = document.getElementById("dg-message");
const dgEditMa = document.getElementById("dg-edit-ma");
const dgSubmit = document.getElementById("dg-submit");
const dgCancel = document.getElementById("dg-cancel");
const thForm = document.getElementById("th-form");
const thList = document.getElementById("th-list");
const thCount = document.getElementById("th-count");
const thMessage = document.getElementById("th-message");
const thNhom = document.getElementById("th-nhom");
const thSearch = document.getElementById("th-search");
const thPageInfo = document.getElementById("th-page-info");
const thPrev = document.getElementById("th-prev");
const thNext = document.getElementById("th-next");
const TH_PER_PAGE = 10;
let thPage = 1, thTotalPages = 0, thDebounce = null;

function adminHeaders(json) {
  return { ...(json ? { "Content-Type": "application/json" } : {}), Authorization: `Bearer ${authToken}` };
}

function adminRow(text, sub, onEdit, onDelete) {
  const li = document.createElement("li");
  li.className = "admin-list-item";
  const info = document.createElement("div");
  const t = document.createElement("strong");
  t.textContent = text;
  info.appendChild(t);
  if (sub) {
    const s = document.createElement("span");
    s.className = "muted-text";
    s.textContent = sub;
    info.appendChild(s);
  }
  const actions = document.createElement("div");
  actions.className = "admin-row-actions";
  if (onEdit) {
    const e = document.createElement("button");
    e.className = "text-button";
    e.type = "button";
    e.textContent = "Sửa";
    e.addEventListener("click", onEdit);
    actions.appendChild(e);
  }
  const d = document.createElement("button");
  d.className = "text-button danger";
  d.type = "button";
  d.textContent = "Xóa";
  d.addEventListener("click", onDelete);
  actions.appendChild(d);
  li.append(info, actions);
  return li;
}

async function loadDrugGroups() {
  const r = await fetch("/api/admin/db/nhom-thuoc", { headers: adminHeaders() });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Không tải được nhóm thuốc.");
  const groups = data.nhom_thuoc || [];
  if (dgCount) dgCount.textContent = String(groups.length);
  dgList.innerHTML = "";
  // select gắn nhóm cho thuốc
  if (thNhom) {
    thNhom.innerHTML = '<option value="">— Gắn vào nhóm (tùy chọn) —</option>';
    groups.forEach((g) => {
      const o = document.createElement("option");
      o.value = String(g.ma); o.textContent = g.ten;
      thNhom.appendChild(o);
    });
  }
  groups.forEach((g) => {
    dgList.appendChild(adminRow(
      g.ten, `${g.so_thuoc} thuốc${g.mo_ta ? " · " + g.mo_ta : ""}`,
      () => { dgEditMa.value = g.ma; document.getElementById("dg-ten").value = g.ten; document.getElementById("dg-mo-ta").value = g.mo_ta || ""; dgSubmit.textContent = "Lưu sửa"; dgCancel.hidden = false; },
      async () => {
        if (!confirm(`Xóa nhóm "${g.ten}"? Các liên kết thuốc cũng bị gỡ.`)) return;
        const dr = await fetch(`/api/admin/db/nhom-thuoc/${g.ma}`, { method: "DELETE", headers: adminHeaders() });
        if (dr.ok) loadDrugAdmin(); else dgMessage.textContent = (await dr.json()).error || "Không xóa được.";
      }));
  });
}

async function loadDrugs(page) {
  thPage = page || 1;
  const q = thSearch ? thSearch.value.trim() : "";
  const params = new URLSearchParams({ page: String(thPage), per_page: String(TH_PER_PAGE) });
  if (q) params.set("q", q);
  const r = await fetch(`/api/admin/db/thuoc?${params}`, { headers: adminHeaders() });
  const data = await r.json();
  if (!r.ok) throw new Error(data.error || "Không tải được thuốc.");
  thTotalPages = data.total_pages || 0;
  if (thCount) thCount.textContent = (data.total || 0).toLocaleString("vi-VN");
  thList.innerHTML = "";
  (data.thuoc || []).forEach((t) => {
    const sub = [t.hoat_chat, (t.nhom || []).join(", ")].filter(Boolean).join(" · ");
    thList.appendChild(adminRow(t.ten, sub, null, async () => {
      if (!confirm(`Xóa thuốc "${t.ten}"?`)) return;
      const dr = await fetch(`/api/admin/db/thuoc/${t.ma}`, { method: "DELETE", headers: adminHeaders() });
      if (dr.ok) loadDrugs(thPage); else thMessage.textContent = (await dr.json()).error || "Không xóa được.";
    }));
  });
  if (thPageInfo) thPageInfo.textContent = thTotalPages ? `Trang ${thPage} / ${thTotalPages}` : "Trang 0";
  if (thPrev) thPrev.disabled = thPage <= 1;
  if (thNext) thNext.disabled = thPage >= thTotalPages;
}

async function loadDrugAdmin() {
  if (!isAdminUser()) return;
  try {
    await loadDrugGroups();
    await loadDrugs(1);
  } catch (error) {
    if (dgMessage) dgMessage.textContent = formatError(error);
  }
}

if (dgForm) {
  dgForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const ma = dgEditMa.value;
    const body = JSON.stringify({ ten: document.getElementById("dg-ten").value, mo_ta: document.getElementById("dg-mo-ta").value });
    const url = ma ? `/api/admin/db/nhom-thuoc/${ma}` : "/api/admin/db/nhom-thuoc";
    try {
      const r = await fetch(url, { method: ma ? "PUT" : "POST", headers: adminHeaders(true), body });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Không lưu được.");
      dgForm.reset(); dgEditMa.value = ""; dgSubmit.textContent = "Thêm nhóm"; dgCancel.hidden = true;
      dgMessage.textContent = ma ? "Đã cập nhật nhóm." : "Đã thêm nhóm.";
      loadDrugAdmin();
    } catch (error) { dgMessage.textContent = formatError(error); }
  });
}
if (dgCancel) dgCancel.addEventListener("click", () => { dgForm.reset(); dgEditMa.value = ""; dgSubmit.textContent = "Thêm nhóm"; dgCancel.hidden = true; });

if (thForm) {
  thForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    const body = JSON.stringify({
      ten: document.getElementById("th-ten").value,
      hoat_chat: document.getElementById("th-hoat-chat").value,
      ma_nhom_thuoc: thNhom.value || null,
    });
    try {
      const r = await fetch("/api/admin/db/thuoc", { method: "POST", headers: adminHeaders(true), body });
      const data = await r.json();
      if (!r.ok) throw new Error(data.error || "Không thêm được.");
      thForm.reset();
      thMessage.textContent = "Đã thêm thuốc.";
      loadDrugGroups();
      loadDrugs(1);
    } catch (error) { thMessage.textContent = formatError(error); }
  });
}
if (thSearch) thSearch.addEventListener("input", () => { clearTimeout(thDebounce); thDebounce = setTimeout(() => loadDrugs(1), 250); });
if (thPrev) thPrev.addEventListener("click", () => { if (thPage > 1) loadDrugs(thPage - 1); });
if (thNext) thNext.addEventListener("click", () => { if (thPage < thTotalPages) loadDrugs(thPage + 1); });

// PORT: bulk import CSV
async function bulkUpload(fileInputId, url, msgEl, onDone) {
  const f = document.getElementById(fileInputId).files[0];
  if (!f) { msgEl.textContent = "Chưa chọn file."; msgEl.classList.add("is-error"); return; }
  msgEl.classList.remove("is-error");
  msgEl.textContent = "Đang tải lên...";
  const fd = new FormData();
  fd.append("file", f);
  try {
    const r = await fetch(url, { method: "POST", headers: { Authorization: `Bearer ${authToken}` }, body: fd });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Import lỗi.");
    let txt = `Đã thêm ${data.inserted}`;
    if (typeof data.skipped === "number") txt += `, bỏ qua ${data.skipped} (trùng)`;
    if (data.errors && data.errors.length) txt += `. ${data.errors.length} cảnh báo: ${data.errors[0]}`;
    msgEl.textContent = txt;
    if (onDone) onDone();
  } catch (error) {
    msgEl.textContent = formatError(error);
    msgEl.classList.add("is-error");
  }
}

async function downloadTemplate(url, filename) {
  try {
    const r = await fetch(url, { headers: { Authorization: `Bearer ${authToken}` } });
    if (!r.ok) throw new Error("Không tải được template.");
    const blob = await r.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = filename;
    a.click();
    URL.revokeObjectURL(a.href);
  } catch (e) { /* bỏ qua */ }
}

const importDgBtn = document.getElementById("import-dg-btn");
const importThBtn = document.getElementById("import-th-btn");
if (importDgBtn) importDgBtn.addEventListener("click", () =>
  bulkUpload("import-dg-file", "/api/admin/bulk-import/nhom-thuoc", document.getElementById("import-dg-msg"), loadDrugAdmin));
if (importThBtn) importThBtn.addEventListener("click", () =>
  bulkUpload("import-th-file", "/api/admin/bulk-import/thuoc", document.getElementById("import-th-msg"), loadDrugAdmin));
const tplDg = document.getElementById("tpl-dg");
const tplTh = document.getElementById("tpl-th");
if (tplDg) tplDg.addEventListener("click", (e) => { e.preventDefault(); downloadTemplate("/api/admin/bulk-import/template/nhom-thuoc", "nhom_thuoc_template.csv"); });
if (tplTh) tplTh.addEventListener("click", (e) => { e.preventDefault(); downloadTemplate("/api/admin/bulk-import/template/thuoc", "thuoc_template.csv"); });

// ── PORT: duyệt phản hồi không đồng ý ────────────────────────────────────────
const fbList = document.getElementById("fb-list");
const fbEmpty = document.getElementById("fb-empty");
const fbPendingPill = document.getElementById("fb-pending-pill");
const fbMessage = document.getElementById("fb-message");
const fbPageInfo = document.getElementById("fb-page-info");
const fbPrev = document.getElementById("fb-prev");
const fbNext = document.getElementById("fb-next");
const fbTabs = document.querySelectorAll("[data-fb-filter]");
let fbFilter = "0", fbPage = 1, fbTotalPages = 0;

function fmtDate(iso) {
  if (!iso) return "";
  try { return new Date(iso).toLocaleString("vi-VN"); } catch { return iso; }
}

async function loadFeedbackAdmin(page) {
  if (!isAdminUser()) return;
  fbPage = page || 1;
  const params = new URLSearchParams({ page: String(fbPage), per_page: "10" });
  if (fbFilter === "0" || fbFilter === "1") params.set("reviewed", fbFilter);
  try {
    const r = await fetch(`/api/admin/rejected-feedbacks?${params}`, { headers: { Authorization: `Bearer ${authToken}` } });
    const data = await r.json();
    if (!r.ok) throw new Error(data.error || "Không tải được phản hồi.");
    fbTotalPages = data.total_pages || 0;
    if (fbPendingPill) fbPendingPill.textContent = `${data.chua_xu_ly || 0} chưa xử lý`;
    const items = data.feedbacks || [];
    fbEmpty.classList.toggle("is-hidden", items.length > 0);
    fbList.innerHTML = "";
    items.forEach((f) => {
      const li = document.createElement("li");
      li.className = "admin-list-item";
      const info = document.createElement("div");
      const t = document.createElement("strong");
      t.textContent = f.noi_dung || "(không ghi lý do)";
      const s = document.createElement("span");
      s.className = "muted-text";
      s.textContent = [f.nhom_thuoc, fmtDate(f.thoi_gian), f.da_xu_ly ? "✓ đã xử lý" : "• chưa xử lý"].filter(Boolean).join(" · ");
      info.append(t, s);
      const actions = document.createElement("div");
      actions.className = "admin-row-actions";
      const btn = document.createElement("button");
      btn.className = f.da_xu_ly ? "text-button" : "primary-button compact";
      btn.type = "button";
      btn.textContent = f.da_xu_ly ? "Mở lại" : "Đánh dấu đã xử lý";
      btn.addEventListener("click", async () => {
        const rr = await fetch(`/api/admin/rejected-feedbacks/${f.ma}/reviewed`, {
          method: "POST", headers: { "Content-Type": "application/json", Authorization: `Bearer ${authToken}` },
          body: JSON.stringify({ da_xu_ly: !f.da_xu_ly }),
        });
        if (rr.ok) loadFeedbackAdmin(fbPage);
      });
      actions.appendChild(btn);
      li.append(info, actions);
      fbList.appendChild(li);
    });
    if (fbPageInfo) fbPageInfo.textContent = fbTotalPages ? `Trang ${fbPage} / ${fbTotalPages}` : "Trang 0";
    if (fbPrev) fbPrev.disabled = fbPage <= 1;
    if (fbNext) fbNext.disabled = fbPage >= fbTotalPages;
  } catch (error) {
    if (fbMessage) { fbMessage.textContent = formatError(error); fbMessage.classList.add("is-error"); }
  }
}

fbTabs.forEach((tab) => {
  tab.addEventListener("click", () => {
    fbFilter = tab.dataset.fbFilter;
    fbTabs.forEach((t) => t.classList.toggle("is-active", t === tab));
    loadFeedbackAdmin(1);
  });
});
if (fbPrev) fbPrev.addEventListener("click", () => { if (fbPage > 1) loadFeedbackAdmin(fbPage - 1); });
if (fbNext) fbNext.addEventListener("click", () => { if (fbPage < fbTotalPages) loadFeedbackAdmin(fbPage + 1); });

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

historySearch.addEventListener("input", applyHistoryFilters);

if (historyFilterToggle && historyFilterPanel) {
  historyFilterToggle.addEventListener("click", () => {
    const willOpen = historyFilterPanel.classList.contains("is-hidden");
    historyFilterPanel.classList.toggle("is-hidden", !willOpen);
    historyFilterToggle.setAttribute("aria-expanded", String(willOpen));
    if (willOpen) historyDateFilter?.focus();
  });
}
if (historyDateFilter) historyDateFilter.addEventListener("change", applyHistoryFilters);
if (historyClearButton) {
  historyClearButton.addEventListener("click", () => {
    if (savedResults.length === 0) {
      setAuthMessage(historyMessage, "Lịch sử hiện đang trống.");
      return;
    }
    if (!confirm(`Xóa toàn bộ ${savedResults.length} kết quả đã lưu?`)) return;
    savedResults = [];
    saveHistory();
    renderSavedHistory();
    renderRecentActivity();
    setAuthMessage(historyMessage, "Đã xóa toàn bộ lịch sử.");
  });
}
if (historyExportExcel) historyExportExcel.addEventListener("click", () => exportPersonalHistory("xlsx"));
if (historyExportPdf) historyExportPdf.addEventListener("click", () => exportPersonalHistory("pdf"));

const historyDetailModal = document.getElementById("history-detail-modal");
const historyDetailClose = document.getElementById("history-detail-close");
function closeHistoryDetail() {
  if (historyDetailModal) historyDetailModal.classList.add("is-hidden");
}
if (historyDetailClose) historyDetailClose.addEventListener("click", closeHistoryDetail);
if (historyDetailModal) {
  historyDetailModal.addEventListener("click", (event) => {
    if (event.target === historyDetailModal) closeHistoryDetail();
  });
}

saveResultButton.addEventListener("click", () => {
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

// ── Admin: lịch sử dự đoán toàn hệ thống (đọc từ Postgres) ───────────────────
let ahPage = 1, ahPages = 1, ahStatus = "", ahEmail = "", ahDebounce = null;
const AH_STATUS_LABELS = { suggest: "Gợi ý OTC", safety_block: "Né an toàn", emergency: "Cấp cứu" };

function ahEscape(value) {
  const div = document.createElement("div");
  div.textContent = value == null ? "" : String(value);
  return div.innerHTML;
}

async function loadAdminHistory(page = 1) {
  ahPage = page;
  const rows = document.getElementById("ah-rows");
  const table = document.getElementById("ah-table");
  const empty = document.getElementById("ah-empty");
  const msg = document.getElementById("ah-message");
  const pill = document.getElementById("ah-total-pill");
  const info = document.getElementById("ah-page-info");
  if (!rows) return;
  if (msg) { msg.textContent = ""; msg.classList.remove("is-error"); }
  try {
    const params = new URLSearchParams({ page: String(page), page_size: "20" });
    if (ahStatus) params.set("status", ahStatus);
    if (ahEmail) params.set("email", ahEmail);
    const response = await fetch(`/api/admin/history?${params.toString()}`, { headers: adminHeaders() });
    const data = await response.json();
    if (!response.ok) throw new Error(data.error || "Không tải được lịch sử hệ thống.");
    ahPages = data.pages || 1;
    if (pill) pill.textContent = `${data.total} lượt`;
    if (info) info.textContent = `Trang ${data.page} / ${data.pages}`;
    rows.innerHTML = "";
    (data.items || []).forEach((it) => {
      const tr = document.createElement("tr");
      const time = it.time ? new Date(it.time).toLocaleString("vi-VN") : "—";
      const label = AH_STATUS_LABELS[it.status] || it.status || "—";
      tr.className = "ah-row";
      tr.innerHTML =
        `<td>${ahEscape(time)}</td>` +
        `<td>${ahEscape(it.email || "guest")}</td>` +
        `<td><span class="ah-status ah-${ahEscape(it.status || "")}">${ahEscape(label)}</span></td>` +
        `<td>${ahEscape(it.group || "—")}</td>` +
        `<td class="ah-chevron"><span class="material-symbols-outlined" aria-hidden="true">chevron_right</span></td>`;
      tr.addEventListener("click", () => openAhDetail(it));
      rows.appendChild(tr);
    });
    const isEmpty = (data.items || []).length === 0;
    if (empty) empty.classList.toggle("is-hidden", !isEmpty);
    if (table) table.classList.toggle("is-hidden", isEmpty);
  } catch (error) {
    if (msg) { msg.textContent = error.message; msg.classList.add("is-error"); }
  }
}

document.querySelectorAll("[data-ah-status]").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll("[data-ah-status]").forEach((b) => b.classList.toggle("is-active", b === btn));
    ahStatus = btn.dataset.ahStatus || "";
    loadAdminHistory(1);
  });
});
const ahEmailInput = document.getElementById("ah-email");
if (ahEmailInput) {
  ahEmailInput.addEventListener("input", () => {
    clearTimeout(ahDebounce);
    ahDebounce = setTimeout(() => { ahEmail = ahEmailInput.value.trim(); loadAdminHistory(1); }, 300);
  });
}
const ahPrevBtn = document.getElementById("ah-prev");
const ahNextBtn = document.getElementById("ah-next");
if (ahPrevBtn) ahPrevBtn.addEventListener("click", () => { if (ahPage > 1) loadAdminHistory(ahPage - 1); });
if (ahNextBtn) ahNextBtn.addEventListener("click", () => { if (ahPage < ahPages) loadAdminHistory(ahPage + 1); });

async function exportAdminHistory(format, button) {
  const msg = document.getElementById("ah-message");
  if (button) button.disabled = true;
  if (msg) { msg.textContent = `Đang tạo file ${format === "xlsx" ? "Excel" : "PDF"}...`; msg.classList.remove("is-error"); }
  try {
    const params = new URLSearchParams();
    if (ahStatus) params.set("status", ahStatus);
    if (ahEmail) params.set("email", ahEmail);
    const qs = params.toString();
    const response = await fetch(`/api/admin/history.${format}${qs ? `?${qs}` : ""}`, { headers: adminHeaders() });
    if (!response.ok) {
      const data = await response.json().catch(() => ({}));
      throw new Error(data.error || "Không xuất được báo cáo.");
    }
    const blob = await response.blob();
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `lich_su_he_thong.${format}`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    URL.revokeObjectURL(url);
    if (msg) msg.textContent = "Đã tạo báo cáo theo bộ lọc hiện tại.";
  } catch (error) {
    if (msg) { msg.textContent = error.message; msg.classList.add("is-error"); }
  } finally {
    if (button) button.disabled = false;
  }
}

const ahExportExcelBtn = document.getElementById("ah-export-excel");
const ahExportPdfBtn = document.getElementById("ah-export-pdf");
if (ahExportExcelBtn) ahExportExcelBtn.addEventListener("click", () => exportAdminHistory("xlsx", ahExportExcelBtn));
if (ahExportPdfBtn) ahExportPdfBtn.addEventListener("click", () => exportAdminHistory("pdf", ahExportPdfBtn));

// Master–detail: bấm 1 dòng để xem chi tiết đầy đủ.
const ahDetailModal = document.getElementById("ah-detail-modal");
const ahDetailBody = document.getElementById("ah-detail-body");
const ahDetailClose = document.getElementById("ah-detail-close");

function closeAhDetail() {
  if (ahDetailModal) ahDetailModal.classList.add("is-hidden");
}

function openAhDetail(it) {
  if (!ahDetailModal || !ahDetailBody) return;
  const time = it.time ? new Date(it.time).toLocaleString("vi-VN") : "—";
  const label = AH_STATUS_LABELS[it.status] || it.status || "—";
  const conf = (typeof it.confidence === "number") ? `${Math.round(it.confidence * 100)}%` : "—";
  const fields = [
    ["Thời gian", time],
    ["Người dùng", it.email || "guest"],
    ["Hướng xử trí", label],
    ["Nhóm thuốc", it.group || "—"],
    ["Độ tin cậy", conf],
    ["Câu người dùng nhập", it.notes || "(không lưu cho ca này)"],
  ];
  ahDetailBody.innerHTML = fields
    .map(([k, v]) => `<dt>${ahEscape(k)}</dt><dd>${ahEscape(v)}</dd>`)
    .join("");
  ahDetailModal.classList.remove("is-hidden");
}

if (ahDetailClose) ahDetailClose.addEventListener("click", closeAhDetail);
if (ahDetailModal) {
  ahDetailModal.addEventListener("click", (e) => {
    if (e.target === ahDetailModal) closeAhDetail();
  });
}
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && historyDetailModal && !historyDetailModal.classList.contains("is-hidden")) {
    closeHistoryDetail();
  }
  if (e.key === "Escape" && ahDetailModal && !ahDetailModal.classList.contains("is-hidden")) {
    closeAhDetail();
  }
});

initTheme();
updateCharCount();
updateSelectedCount();
initializeAuth();

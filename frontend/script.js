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
  renderTop3DrugGroups(
    data.top3_predictions || data.predictions || data.results || [],
    data.symptoms_vi || data.matched_symptoms || []
);
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

// ════════════════════════════════════════════════════════════════════════════════
// SYMPTOM SUGGESTER - Constants and States
// ════════════════════════════════════════════════════════════════════════════════
const MAX_SELECTED_SYMPTOMS = 15;
const SYMPTOM_STATES = {
  LOADING: 'loading',
  EMPTY: 'empty',
  ERROR: 'error',
  LOADED: 'loaded'
};

// ════════════════════════════════════════════════════════════════════════════════
// SYMPTOM SUGGESTER - Helper Functions
// ════════════════════════════════════════════════════════════════════════════════

function showSymptomState(state, errorMessage = "") {
  const states = {
    loading: document.getElementById("symptom-loading-state"),
    empty: document.getElementById("symptom-empty-state"),
    error: document.getElementById("symptom-error-state"),
    list: document.getElementById("symptom-list")
  };

  // Hide all states
  Object.values(states).forEach(el => {
    if (el) el.style.display = "none";
  });

  // Show requested state
  if (state === SYMPTOM_STATES.LOADING) {
    if (states.loading) states.loading.style.display = "flex";
  } else if (state === SYMPTOM_STATES.EMPTY) {
    if (states.empty) states.empty.style.display = "flex";
  } else if (state === SYMPTOM_STATES.ERROR) {
    if (states.error) {
      states.error.style.display = "flex";
      const errorMsg = document.getElementById("symptom-error-message");
      if (errorMsg) errorMsg.textContent = errorMessage || "Lỗi tải dữ liệu, vui lòng thử lại";
    }
  } else if (state === SYMPTOM_STATES.LOADED) {
    if (states.list) states.list.style.display = "flex";
  }
}

function updateSelectedCount() {
  const badgeEl = document.getElementById("selected-count");
  if (badgeEl) {
    const count = selectedSymptoms.size;
    badgeEl.textContent = count === 0 ? "0 đã chọn" : `${count} đã chọn`;
    badgeEl.setAttribute("data-count", count);
  }
}

function canSelectMore() {
  return selectedSymptoms.size < MAX_SELECTED_SYMPTOMS;
}

function getSelectedSymptomLabels() {
  // Trả về mảng tên của các triệu chứng đã chọn để cập nhật textarea
  const selectedLabels = [];
  selectedSymptoms.forEach(symptomId => {
    const symptom = symptoms.find(s => s.id === symptomId);
    if (symptom) {
      selectedLabels.push(symptom.label_vi || symptom.label);
    }
  });
  return selectedLabels;
}

// ════════════════════════════════════════════════════════════════════════════════
// SYMPTOM SUGGESTER - Main Functions
// ════════════════════════════════════════════════════════════════════════════════

async function loadSymptoms() {
  try {
    showSymptomState(SYMPTOM_STATES.LOADING);
    const response = await fetch("/api/symptoms/common?limit=30");
    if (!response.ok) {
      throw new Error("Không tải được danh sách triệu chứng.");
    }
    const data = await response.json();
    symptoms = data.data || data.symptoms || [];
    symptomsLoaded = true;
    renderSymptoms("");
  } catch (error) {
    showSymptomState(SYMPTOM_STATES.ERROR, error.message);
    console.error("Error loading symptoms:", error);
  }
}

async function renderSymptoms(filter = "") {
  try {
    const query = filter.trim();

    if (!query) {
      // Nếu không có filter, hiển thị danh sách common symptoms từ cache
      if (symptoms.length === 0) {
        showSymptomState(SYMPTOM_STATES.EMPTY);
        return;
      }
      renderSymptomChips(symptoms);
    } else {
      // Nếu có filter, gọi API search
      showSymptomState(SYMPTOM_STATES.LOADING);
      const response = await fetch(`/api/symptoms/search?q=${encodeURIComponent(query)}&limit=30`);
      if (!response.ok) {
        throw new Error("Lỗi tìm kiếm triệu chứng");
      }
      const data = await response.json();
      const results = data.data || [];
      
      if (results.length === 0) {
        showSymptomState(SYMPTOM_STATES.EMPTY);
      } else {
        renderSymptomChips(results);
      }
    }
  } catch (error) {
    showSymptomState(SYMPTOM_STATES.ERROR, error.message);
    console.error("Error rendering symptoms:", error);
  }
}

function renderSymptomChips(symptomsData) {
  const chipsContainer = document.getElementById("symptom-list");
  if (!chipsContainer) return;

  chipsContainer.innerHTML = "";
  showSymptomState(SYMPTOM_STATES.LOADED);

  symptomsData.forEach((symptom) => {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "symptom-chip";
    
    const isSelected = selectedSymptoms.has(symptom.id);
    if (isSelected) {
      button.classList.add("selected");
    }

    // Disable button nếu đạt giới hạn và chưa được chọn
    const isDisabled = !isSelected && !canSelectMore();
    if (isDisabled) {
      button.classList.add("disabled");
      button.disabled = true;
      button.title = `Đã chọn tối đa ${MAX_SELECTED_SYMPTOMS} triệu chứng`;
    }

    button.dataset.symptom = symptom.id;
    button.textContent = symptom.label_vi || symptom.label || symptom.label_en;
    
    button.addEventListener("click", () => {
      if (selectedSymptoms.has(symptom.id)) {
        // Bỏ chọn
        selectedSymptoms.delete(symptom.id);
      } else {
        // Chọn (nếu chưa đạt giới hạn)
        if (canSelectMore()) {
          selectedSymptoms.add(symptom.id);
        }
      }
      updateSelectedCount();
      renderSymptoms(symptomSearch.value);
    });

    chipsContainer.appendChild(button);
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
  button.addEventListener("click", () => {
    showHistoryDetail(entry);
  });
  topLine.append(status, time);
  button.appendChild(icon);
  card.append(topLine, title, summary, button);
  return card;
}
function showHistoryDetail(entry) {
  alert(
    `CHI TIẾT LỊCH SỬ DỰ ĐOÁN\n\n` +
    `Ngày: ${entry.savedAt || "Không rõ"}\n` +
    `Nhóm thuốc: ${entry.disease || "Không rõ"}\n` +
    `Triệu chứng: ${(entry.symptoms || []).join(", ") || "Không rõ"}\n` +
    `Ghi chú: ${entry.notes || "Không có"}\n` +
    `Người dùng: ${entry.user || "Không rõ"}\n` +
    `Độ tin cậy: ${entry.score != null ? entry.score : "Không có"}\n` +
    `Loại điểm: ${entry.score_type || "Không có"}`
  );
}
function renderSavedHistory() {
  document.querySelectorAll(".user-history-card").forEach((card) => card.remove());
  savedResults
    .slice()
    .reverse()
    .forEach((entry) => {
      historyList.prepend(createHistoryCard(entry));
    });
  renderHistoryTable();
  updateHistoryEmptyState();
}

function renderHistoryTable() {
  const tbody = document.getElementById('history-table-tbody');
  if (!tbody) return;
  tbody.innerHTML = '';

  // Use current filter from search box
  const allFiltered = getFilteredHistoryEntries();
  const total = allFiltered.length;
  historyPageSize = parseInt(document.getElementById('history-page-size')?.value || historyPageSize, 10) || historyPageSize;
  const totalPages = Math.max(1, Math.ceil(total / historyPageSize));
  if (historyCurrentPage > totalPages) historyCurrentPage = totalPages;
  if (historyCurrentPage < 1) historyCurrentPage = 1;

  const start = (historyCurrentPage - 1) * historyPageSize;
  const pageRows = allFiltered.slice(start, start + historyPageSize);

  pageRows.forEach((entry, localIdx) => {
    const idx = start + localIdx; // index in reversed array
    const tr = document.createElement('tr');
    tr.dataset.search = `${entry.disease || ''} ${entry.notes || ''} ${(entry.symptoms || []).join(' ')} ${entry.savedAt || ''}`.toLowerCase();

    const tdDate = document.createElement('td');
    tdDate.style.padding = '12px';
    tdDate.textContent = entry.savedAt || '';

    const tdTitle = document.createElement('td');
    tdTitle.style.padding = '12px';
    tdTitle.textContent = entry.disease || '';

    const tdSymptoms = document.createElement('td');
    tdSymptoms.style.padding = '12px';
    tdSymptoms.textContent = (entry.symptoms || []).join(', ');

    const tdNotes = document.createElement('td');
    tdNotes.style.padding = '12px';
    tdNotes.textContent = entry.notes || '';

    const tdActions = document.createElement('td');
    tdActions.style.padding = '12px';
    tdActions.style.textAlign = 'center';
    const viewBtn = document.createElement('button');
    viewBtn.className = 'text-button';
    viewBtn.type = 'button';
    viewBtn.textContent = 'Xem';
    viewBtn.addEventListener('click', () => {
      showHistoryDetail(entry);
    });
    const delBtn = document.createElement('button');
    delBtn.className = 'text-button';
    delBtn.type = 'button';
    delBtn.textContent = 'Xóa';
    delBtn.addEventListener('click', () => {
      if (confirm('Xác nhận xóa mục lịch sử này?')) {
        // compute global index in savedResults (reversed earlier)
        const globalIdx = savedResults.length - 1 - idx;
        savedResults.splice(globalIdx, 1);
        saveHistory();
        renderSavedHistory();
        renderRecentActivity();
      }
    });
    tdActions.style.display = "flex";
    tdActions.style.justifyContent = "center";
    tdActions.style.gap = "10px";
    tdActions.append(viewBtn, delBtn);

    tr.append(tdDate, tdTitle, tdSymptoms, tdNotes, tdActions);
    tbody.appendChild(tr);
  });

  // update pager UI
  const pagerInfo = document.getElementById('history-pager-info');
  const pagerPrev = document.getElementById('history-pager-prev');
  const pagerNext = document.getElementById('history-pager-next');
  if (pagerInfo) {
    const from = total === 0 ? 0 : start + 1;
    const to = Math.min(total, start + pageRows.length);
    pagerInfo.textContent = `Hiển thị ${from}–${to} / ${total}`;
  }
  if (pagerPrev) pagerPrev.disabled = historyCurrentPage <= 1;
  if (pagerNext) pagerNext.disabled = historyCurrentPage >= totalPages;

  // set jump input value
  const jumpInput = document.getElementById('history-jump-input');
  if (jumpInput) jumpInput.value = historyCurrentPage;

  // ensure pager controls wired once
  attachHistoryPagerHandlers();
}

function attachHistoryPagerHandlers() {
  const pagerPrev = document.getElementById('history-pager-prev');
  const pagerNext = document.getElementById('history-pager-next');
  const pageSizeSelect = document.getElementById('history-page-size');
  if (pagerPrev && !pagerPrev._hasHandler) {
    pagerPrev.addEventListener('click', () => { historyCurrentPage = Math.max(1, historyCurrentPage - 1); renderHistoryTable(); updateHistoryEmptyState(); });
    pagerPrev._hasHandler = true;
  }
  if (pagerNext && !pagerNext._hasHandler) {
    pagerNext.addEventListener('click', () => { historyCurrentPage = historyCurrentPage + 1; renderHistoryTable(); updateHistoryEmptyState(); });
    pagerNext._hasHandler = true;
  }
  if (pageSizeSelect && !pageSizeSelect._hasHandler) {
    pageSizeSelect.addEventListener('change', () => { historyPageSize = parseInt(pageSizeSelect.value, 10) || 10; historyCurrentPage = 1; renderHistoryTable(); updateHistoryEmptyState(); });
    pageSizeSelect._hasHandler = true;
  }
  // Jump-to-page handlers
  const jumpInputEl = document.getElementById('history-jump-input');
  const jumpGo = document.getElementById('history-jump-go');
  if (jumpGo && !jumpGo._hasHandler) {
    jumpGo.addEventListener('click', () => {
      const val = parseInt(jumpInputEl?.value, 10);
      const total = getFilteredHistoryEntries().length;
      const totalPages = Math.max(1, Math.ceil(total / historyPageSize));
      const errorEl = document.getElementById('history-jump-error');
      if (!Number.isFinite(val) || val < 1 || val > totalPages) {
        if (errorEl) {
          errorEl.textContent = `Nhập số trang hợp lệ: 1 - ${totalPages}`;
          errorEl.style.display = 'inline';
        } else {
          alert(`Nhập số trang hợp lệ: 1 - ${totalPages}`);
        }
        if (jumpInputEl) jumpInputEl.focus();
        return;
      }
      if (errorEl) { errorEl.textContent = ''; errorEl.style.display = 'none'; }
      historyCurrentPage = val;
      renderHistoryTable();
      updateHistoryEmptyState();
    });
    jumpGo._hasHandler = true;
  }
  if (jumpInputEl && !jumpInputEl._hasHandler) {
    jumpInputEl.addEventListener('keydown', (e) => { if (e.key === 'Enter') { e.preventDefault(); document.getElementById('history-jump-go')?.click(); }});
    jumpInputEl._hasHandler = true;
  }
}

function updateHistoryEmptyState() {
  const empty = document.getElementById("history-empty");
  if (!empty) {
    return;
  }
  const cards = historyList.querySelectorAll(".history-card");
  const visibleCard = Array.from(cards).some((card) => !card.classList.contains("is-hidden"));
  const visibleTableRows = document.querySelectorAll("#history-table-tbody tr:not(.is-hidden)");
  const anyVisible = visibleCard || visibleTableRows.length > 0;
  empty.classList.toggle("is-hidden", anyVisible);
  const title = empty.querySelector("h2");
  const desc = empty.querySelector("p");
  if (title && desc) {
    if (cards.length === 0 && document.querySelectorAll('#history-table-tbody tr').length === 0) {
      title.textContent = "Chưa có lịch sử dự đoán";
      desc.textContent = "Các kết quả bạn lưu sẽ xuất hiện ở đây. Hãy thử tạo một dự đoán mới.";
    } else if (!anyVisible) {
      title.textContent = "Không tìm thấy kết quả";
      desc.textContent = "Không có mục nào khớp với từ khóa tìm kiếm.";
    } else {
      // Có ít nhất một mục, giữ mặc định thông điệp
      title.textContent = "Kết quả";
      desc.textContent = "Hiển thị các mục lịch sử phù hợp.";
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
function renderDangerWarning(dangerWarning) {
  if (!dangerWarning || !dangerWarning.has_danger) {
    return;
  }

  const warningContainer = document.getElementById("warning-text");

  if (!warningContainer) {
    return;
  }

  const keywords = dangerWarning.danger_keywords || [];

  warningContainer.innerHTML = `
    <div class="danger-banner">
      <h3>🚨 CẢNH BÁO Y KHOA KHẨN CẤP</h3>
      <p>${dangerWarning.warning_message}</p>
      <div class="danger-keywords">
        ${keywords.map(x => `<span>${x}</span>`).join("")}
      </div>
    </div>
  `;
}
function renderPrediction(result) {
  const isRuleBased = result.score_type === "rule";
  const confidence = result.confidence === null || result.confidence === undefined ? "0.0" : (result.confidence * 100).toFixed(1);
  const isUncertain = Boolean(result.needs_more_input);
  const matchedCount = (result.matched_symptoms_vi || result.matched_symptoms || []).length;
  const unsupportedLabels = (result.unsupported_symptoms || []).map((symptom) => symptom.label_vi);
  const scoreText = result.score_label || "Độ tin cậy";

  currentResult = result;
  renderDangerWarning(result.danger_warning);
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
    
    const authData = {
        token: data.token,
        user: { name: "Bác sĩ", email: inputEmail } 
    };
    
    handleAuthSuccess(authData);
    
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
            if (button.dataset.page === "admin-feedback") {
          loadRejectedFeedbacks();
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

// ════════════════════════════════════════════════════════════════════════════════
// SYMPTOM SEARCH - Debounced Input Handler
// ════════════════════════════════════════════════════════════════════════════════

let symptomSearchTimeout;
const SYMPTOM_SEARCH_DELAY = 300; // ms

symptomSearch.addEventListener("input", (event) => {
  // Clear previous timeout
  if (symptomSearchTimeout) {
    clearTimeout(symptomSearchTimeout);
  }
  
  // Set new timeout to debounce search
  symptomSearchTimeout = setTimeout(() => {
    renderSymptoms(event.target.value);
  }, SYMPTOM_SEARCH_DELAY);
});

let historyCurrentPage = 1;
let historyPageSize = 10;

historySearch.addEventListener("input", (event) => {
  const query = event.target.value.trim().toLowerCase();

  document.querySelectorAll(".history-card").forEach((card) => {
    const haystack = (card.dataset.search || '').toLowerCase();
    card.classList.toggle("is-hidden", query !== "" && !haystack.includes(query));
  });

  // Reset to first page when searching
  historyCurrentPage = 1;
  renderHistoryTable();
  updateHistoryEmptyState();
});

// Thiết lập chuyển chế độ Thẻ / Bảng
(function initHistoryViewToggle(){
  const historyViewButtons = document.querySelectorAll('.view-toggle-btn');
  const historyTableWrap = document.getElementById('history-table-wrap');
  const historyGrid = document.getElementById('history-list');
  if (!historyViewButtons || historyViewButtons.length === 0) return;
  historyViewButtons.forEach((btn) => {
    btn.addEventListener('click', () => {
      historyViewButtons.forEach((b) => {
        b.classList.toggle('is-active', b === btn);
        b.setAttribute('aria-selected', String(b === btn));
      });
      const view = btn.dataset.historyView;
      if (view === 'table') {
        if (historyGrid) historyGrid.classList.add('is-hidden');
        if (historyTableWrap) historyTableWrap.classList.remove('is-hidden');
      } else {
        if (historyGrid) historyGrid.classList.remove('is-hidden');
        if (historyTableWrap) historyTableWrap.classList.add('is-hidden');
      }
    });
  });
})();

// --- CSV EXPORT FOR HISTORY ---
function getFilteredHistoryEntries() {
  const query = (historySearch && historySearch.value ? historySearch.value.trim().toLowerCase() : '');
  return savedResults.slice().reverse().filter((entry) => {
    const hay = `${entry.disease || ''} ${entry.notes || ''} ${(entry.symptoms || []).join(' ') } ${entry.savedAt || ''}`.toLowerCase();
    return query === '' || hay.includes(query);
  });
}

function toCsvRow(fields, sep = ',') {
  return fields
    .map((f) => {
      if (f === null || f === undefined) return '';
      const s = String(f);
      const needsQuote = s.includes('"') || s.includes('\n') || (sep && s.includes(sep));
      if (needsQuote) {
        return '"' + s.replace(/"/g, '""') + '"';
      }
      return s;
    })
    .join(sep);
}

function exportHistoryCsv(selectedCols = ['date','disease','symptoms','notes','user','score','score_type'], exportAll = false, sep = ',') {
  const rows = exportAll ? savedResults.slice().reverse() : getFilteredHistoryEntries();
  if (!rows || rows.length === 0) {
    alert('Không có mục lịch sử để xuất.');
    return;
  }

  const colMap = {
    date: 'Ngày',
    disease: 'Bệnh/Nhóm thuốc',
    symptoms: 'Triệu chứng',
    notes: 'Ghi chú',
    user: 'Người dùng',
    score: 'Score',
    score_type: 'Score type',
  };

  const header = selectedCols.map((c) => colMap[c] || c);
  const lines = [toCsvRow(header, sep)];

  rows.forEach((r) => {
    const values = selectedCols.map((c) => {
      switch (c) {
        case 'date':
          return r.savedAt || '';
        case 'disease':
          return r.disease || '';
        case 'symptoms':
          return (r.symptoms || []).join('; ');
        case 'notes':
          return r.notes || '';
        case 'user':
          return r.user || (currentUser ? (currentUser.email || currentUser.name) : 'guest') || '';
        case 'score':
          return r.score != null ? String(r.score) : (r._raw_confidence != null ? String(r._raw_confidence) : '');
        case 'score_type':
          return r.score_type || r._raw_score_type || '';
        default:
          return '';
      }
    });
    lines.push(toCsvRow(values, sep));
  });

  const csv = '\uFEFF' + lines.join('\r\n'); // BOM for Excel
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pharma_history_${new Date().toISOString().slice(0,10)}.csv`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

function exportHistoryJson(selectedCols = ['date','disease','symptoms','notes','user','score','score_type'], exportAll = false) {
  const rows = exportAll ? savedResults.slice().reverse() : getFilteredHistoryEntries();
  if (!rows || rows.length === 0) {
    alert('Không có mục lịch sử để xuất.');
    return;
  }
  const items = rows.map((r) => {
    const obj = {};
    selectedCols.forEach((c) => {
      switch (c) {
        case 'date': obj['date'] = r.savedAt || ''; break;
        case 'disease': obj['disease'] = r.disease || ''; break;
        case 'symptoms': obj['symptoms'] = r.symptoms || []; break;
        case 'notes': obj['notes'] = r.notes || ''; break;
        case 'user': obj['user'] = r.user || (currentUser ? (currentUser.email || currentUser.name) : 'guest') || ''; break;
        case 'score': obj['score'] = r.score != null ? r.score : (r._raw_confidence != null ? r._raw_confidence : null); break;
        case 'score_type': obj['score_type'] = r.score_type || r._raw_score_type || null; break;
        default: obj[c] = ''; break;
      }
    });
    return obj;
  });
  const json = JSON.stringify(items, null, 2);
  const blob = new Blob([json], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `pharma_history_${new Date().toISOString().slice(0,10)}.json`;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 5000);
}

const historyExportBtn = document.getElementById('history-export-button');
if (historyExportBtn) {
  const exportOptions = document.getElementById('history-export-options');
  historyExportBtn.addEventListener('click', (e) => {
    if (!exportOptions) return;
    exportOptions.classList.toggle('is-hidden');
    // position near button
    try {
      const rect = historyExportBtn.getBoundingClientRect();
      exportOptions.style.left = rect.right - 12 + 'px';
      exportOptions.style.top = rect.bottom + window.scrollY + 8 + 'px';
    } catch (err) {}
  });

  const exportConfirm = document.getElementById('history-export-confirm');
  const exportCancel = document.getElementById('history-export-cancel');
  if (exportCancel) exportCancel.addEventListener('click', () => exportOptions && exportOptions.classList.add('is-hidden'));
  if (exportConfirm) exportConfirm.addEventListener('click', () => {
    const selected = [];
    if (document.getElementById('col-date')?.checked) selected.push('date');
    if (document.getElementById('col-disease')?.checked) selected.push('disease');
    if (document.getElementById('col-symptoms')?.checked) selected.push('symptoms');
    if (document.getElementById('col-notes')?.checked) selected.push('notes');
    if (document.getElementById('col-user')?.checked) selected.push('user');
    if (document.getElementById('col-score')?.checked) selected.push('score');
    if (document.getElementById('col-score-type')?.checked) selected.push('score_type');
    const exportAll = !!document.getElementById('export-all')?.checked;
    const format = (document.getElementById('export-format')?.value || 'csv').toLowerCase();
    const sep = (document.getElementById('export-sep')?.value) || ',';
    if (format === 'json') {
      exportHistoryJson(selected, exportAll);
    } else {
      exportHistoryCsv(selected, exportAll, sep);
    }
    exportOptions && exportOptions.classList.add('is-hidden');
  });
}

saveResultButton.addEventListener("click", () => {
  if (currentResult) {
    savedResults.push({
      disease: currentResult.display_title || currentResult.disease_vi || currentResult.disease,
      symptoms: currentResult.matched_symptoms_vi || [],
      notes: textarea.value.trim(),
      savedAt: new Date().toLocaleDateString("vi-VN"),
      user: currentUser ? (currentUser.email || currentUser.name) : 'guest',
      score: (typeof currentResult.confidence === 'number') ? currentResult.confidence : (currentResult.confidence ?? null),
      score_type: currentResult.score_type || null,
      // keep raw fields if downstream code needs them
      _raw_confidence: currentResult.confidence ?? null,
      _raw_score_type: currentResult.score_type ?? null,
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
const drugGroupForm = document.getElementById("drug-group-form");
const drugGroupList = document.getElementById("drug-group-list");
const dgNameInput = document.getElementById("dg-name");
const dgDescInput = document.getElementById("dg-desc");
const dgSubmitButton = drugGroupForm?.querySelector('button[type="submit"]');
let editingDrugGroupId = null;

function escapeHtml(value = "") {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}
// ============================================================
// SCRUM-78 / Task 47
// UI Admin xem danh sách phản hồi "Không đồng ý"
// ============================================================

let rejectedFeedbacks = [];

async function loadRejectedFeedbacks() {
  const tbody = document.getElementById("feedback-tbody");
  const empty = document.getElementById("feedback-empty");

  if (!tbody) return;

  tbody.innerHTML = `
    <tr>
      <td colspan="5" style="padding:20px; text-align:center; color:var(--text-muted);">
        Đang tải danh sách phản hồi...
      </td>
    </tr>
  `;

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/rejected-feedbacks`);
    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || "Không tải được phản hồi.");
    }

    rejectedFeedbacks = data.feedbacks || [];
    renderRejectedFeedbacks();

    if (empty) {
      empty.classList.toggle("is-hidden", rejectedFeedbacks.length > 0);
    }
  } catch (error) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="padding:20px; text-align:center; color:#ef4444;">
          ${escapeHtml(error.message || "Lỗi tải phản hồi.")}
        </td>
      </tr>
    `;
  }
}

function renderRejectedFeedbacks() {
  const tbody = document.getElementById("feedback-tbody");
  const searchInput = document.getElementById("feedback-search");

  if (!tbody) return;

  const keyword = (searchInput?.value || "").trim().toLowerCase();

  const filtered = rejectedFeedbacks.filter((item) => {
    const text = `${item.trieu_chung_nhap || ""} ${item.ghi_chu || ""}`.toLowerCase();
    return !keyword || text.includes(keyword);
  });

  if (filtered.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="5" style="padding:20px; text-align:center; color:var(--text-muted);">
          Không có phản hồi phù hợp.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = "";

  filtered.forEach((item) => {
    const row = document.createElement("tr");

    row.innerHTML = `
        <td style="padding:12px; border-bottom:1px solid var(--border); color:var(--text-muted);">
        ${item.created_at ? new Date(item.created_at).toLocaleString("vi-VN") : "Không rõ"}
      </td>
      <td style="padding:12px; border-bottom:1px solid var(--border);">
        <span class="status-pill ${item.xu_ly === "DA_XU_LY" ? "status-secure" : ""}">
          ${item.xu_ly === "DA_XU_LY" ? "Đã xử lý" : "Chưa xử lý"}
        </span>
      </td>
      <td style="padding:12px; border-bottom:1px solid var(--border); text-align:center;">
        ${
          item.xu_ly === "DA_XU_LY"
            ? `<span style="color:var(--text-muted); font-weight:700;">Hoàn tất</span>`
            : `<button class="text-button" type="button" onclick="markFeedbackReviewed(${item.id})" style="color:#22c55e; font-weight:700;">
                <span class="material-symbols-outlined" style="font-size:18px;">done</span>
                Đánh dấu đã xử lý
              </button>`
        }
      </td>
    `;

    tbody.appendChild(row);
  });
}

async function markFeedbackReviewed(id) {
  if (!confirm("Đánh dấu phản hồi này là đã xem xét?")) return;

  try {
    const res = await fetch(`${API_BASE_URL}/api/admin/rejected-feedbacks/${id}/reviewed`, {
      method: "POST"
    });

    const data = await res.json();

    if (!res.ok) {
      throw new Error(data.message || "Không cập nhật được phản hồi.");
    }

    await loadRejectedFeedbacks();
  } catch (error) {
    alert(error.message || "Lỗi cập nhật phản hồi.");
  }
}

window.markFeedbackReviewed = markFeedbackReviewed;

function setDrugGroupFormMode(mode = "add", group = null) {
  editingDrugGroupId = mode === "edit" && group ? group.id : null;
  if (dgNameInput) dgNameInput.value = group?.ten_nhom || "";
  if (dgDescInput) dgDescInput.value = group?.mo_ta || "";

  if (dgSubmitButton) {
    dgSubmitButton.innerHTML = editingDrugGroupId
      ? `<span class="material-symbols-outlined">save</span> Cập nhật`
      : `<span class="material-symbols-outlined">add</span> Thêm nhóm`;
  }

  let cancelBtn = document.getElementById("dg-cancel-edit");
  if (editingDrugGroupId && !cancelBtn && drugGroupForm) {
    cancelBtn = document.createElement("button");
    cancelBtn.id = "dg-cancel-edit";
    cancelBtn.type = "button";
    cancelBtn.className = "secondary-button";
    cancelBtn.style.height = "46px";
    cancelBtn.style.marginBottom = "4px";
    cancelBtn.innerHTML = `<span class="material-symbols-outlined">close</span> Hủy`;
    cancelBtn.addEventListener("click", () => {
      drugGroupForm.reset();
      setDrugGroupFormMode("add");
    });
    drugGroupForm.appendChild(cancelBtn);
  }
  if (!editingDrugGroupId && cancelBtn) cancelBtn.remove();
}

async function loadDrugGroups() {
  if (!drugGroupList) return;
  try {
    const res = await fetch(`${API_BASE_URL}/api/drug-groups`);
    if (!res.ok) throw new Error("Không tải được danh sách nhóm thuốc.");
    const data = await res.json();

    drugGroupList.innerHTML = "";

    if (!Array.isArray(data) || data.length === 0) {
      drugGroupList.innerHTML = `<tr><td colspan="4" style="text-align: center; padding: 20px; color: var(--text-muted);">Chưa có dữ liệu nhóm thuốc nào.</td></tr>`;
      return;
    }

    data.forEach((g) => {
      const row = document.createElement("tr");
      row.innerHTML = `
        <td style="padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-muted);">${g.id}</td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border); font-weight: 600;">${escapeHtml(g.ten_nhom)}</td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border); color: var(--text-muted);">${escapeHtml(g.mo_ta || "Không có mô tả.")}</td>
        <td style="padding: 12px; border-bottom: 1px solid var(--border); text-align: center; white-space: nowrap;">
          <button type="button" class="text-button" data-action="edit" data-id="${g.id}" data-name="${escapeHtml(g.ten_nhom)}" data-desc="${escapeHtml(g.mo_ta || "")}" style="color: #2563eb; padding: 4px 8px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
            <span class="material-symbols-outlined" style="font-size: 18px;">edit</span> Sửa
          </button>
          <button type="button" class="text-button" data-action="delete" data-id="${g.id}" style="color: #ef4444; padding: 4px 8px; font-weight: 600; display: inline-flex; align-items: center; gap: 4px;">
            <span class="material-symbols-outlined" style="font-size: 18px;">delete</span> Xóa
          </button>
        </td>
      `;
      drugGroupList.appendChild(row);
    });
  } catch (e) {
    console.error("Lỗi kết nối API lấy danh mục nhóm thuốc:", e);
  }
}

if (drugGroupList) {
  drugGroupList.addEventListener("click", async (e) => {
    const button = e.target.closest("button[data-action]");
    if (!button) return;

    const action = button.dataset.action;
    const id = Number(button.dataset.id);

    if (action === "edit") {
      setDrugGroupFormMode("edit", {
        id,
        ten_nhom: button.dataset.name || "",
        mo_ta: button.dataset.desc || "",
      });
      dgNameInput?.focus();
      return;
    }

    if (action === "delete") {
      await deleteDrugGroup(id);
    }
  });
}

async function deleteDrugGroup(id) {
  if (!confirm("⚠️ Bạn có chắc chắn muốn xóa nhóm thuốc này khỏi hệ thống không?")) return;
  try {
    const res = await fetch(`${API_BASE_URL}/api/drug-groups/${id}`, {
      method: "DELETE",
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.error || "Không thể xóa nhóm thuốc.");
    if (editingDrugGroupId === id) setDrugGroupFormMode("add");
    loadDrugGroups();
  } catch (e) {
    alert(e.message || "Lỗi xóa nhóm thuốc.");
    console.error("Lỗi xóa nhóm thuốc:", e);
  }
}

if (drugGroupForm) {
  drugGroupForm.addEventListener("submit", async (e) => {
    e.preventDefault();
    const ten_nhom = dgNameInput?.value.trim() || "";
    const mo_ta = dgDescInput?.value.trim() || "";

    if (!ten_nhom) {
      alert("Vui lòng nhập tên nhóm thuốc.");
      dgNameInput?.focus();
      return;
    }

    try {
      const endpoint = editingDrugGroupId
        ? `${API_BASE_URL}/api/drug-groups/${editingDrugGroupId}`
        : `${API_BASE_URL}/api/drug-groups`;
      const method = editingDrugGroupId ? "PUT" : "POST";

      const res = await fetch(endpoint, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ten_nhom, mo_ta }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) throw new Error(data.error || "Không thể lưu nhóm thuốc.");

      drugGroupForm.reset();
      setDrugGroupFormMode("add");
      loadDrugGroups();
    } catch (e) {
      alert(e.message || "Lỗi lưu nhóm thuốc.");
      console.error("Lỗi lưu nhóm thuốc:", e);
    }
  });
}
document.getElementById("btn-reload-feedback")
  ?.addEventListener("click", loadRejectedFeedbacks);

document.getElementById("feedback-search")
  ?.addEventListener("input", renderRejectedFeedbacks);
// ============================================================
// SCRUM-75 / SCRUM-76
// Bác sĩ đánh giá kết quả dự đoán: Đồng ý / Không đồng ý
// ============================================================

const btnEvalApprove = document.getElementById("btn-eval-approve");
const btnEvalReject = document.getElementById("btn-eval-reject");
const btnEvalCancel = document.getElementById("btn-eval-cancel");
const btnEvalSubmit = document.getElementById("btn-eval-submit");
const evaluationNoteBox = document.getElementById("evaluation-note-box");
const evaluationNote = document.getElementById("evaluation-note");
const evaluationMessage = document.getElementById("evaluation-message");

function setEvaluationMessage(message, isError = false) {
  if (!evaluationMessage) return;
  evaluationMessage.textContent = message;
  evaluationMessage.classList.toggle("is-error", isError);
}

async function sendEvaluation(status, note = "") {
  if (!currentResult) {
    setEvaluationMessage("Chưa có kết quả dự đoán để đánh giá.", true);
    return;
  }

  const symptomsText =
    textarea?.value?.trim() ||
    (currentResult.matched_symptoms_vi || []).join(", ") ||
    "Không rõ";

  try {
    const response = await fetch(`${API_BASE_URL}/api/evaluation`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json"
      },
      body: JSON.stringify({
        trieu_chung_nhap: symptomsText,
        trang_thai: status,
        ghi_chu: note
      })
    });

    const data = await response.json();

    if (!response.ok || !data.success) {
      throw new Error(data.message || "Không gửi được đánh giá.");
    }

    setEvaluationMessage("Đã gửi đánh giá thành công.", false);

    if (evaluationNoteBox) {
      evaluationNoteBox.classList.add("is-hidden");
    }

    if (evaluationNote) {
      evaluationNote.value = "";
    }
  } catch (error) {
    setEvaluationMessage(error.message || "Lỗi gửi đánh giá.", true);
  }
}

btnEvalApprove?.addEventListener("click", () => {
  sendEvaluation("APPROVE", "Bác sĩ đồng ý với kết quả dự đoán.");
});

btnEvalReject?.addEventListener("click", () => {
  setEvaluationMessage("");
  evaluationNoteBox?.classList.remove("is-hidden");
  evaluationNote?.focus();
});

btnEvalCancel?.addEventListener("click", () => {
  evaluationNoteBox?.classList.add("is-hidden");
  if (evaluationNote) evaluationNote.value = "";
  setEvaluationMessage("");
});

btnEvalSubmit?.addEventListener("click", () => {
  const note = evaluationNote?.value?.trim() || "";

  if (!note) {
    setEvaluationMessage("Vui lòng nhập lý do không đồng ý.", true);
    return;
  }

  sendEvaluation("REJECT", note);
});
initTheme();
updateCharCount();
updateSelectedCount();
initializeAuth();
loadDrugGroups(); 


// ============================================================
// MODULE: QUẢN LÝ THUỐC (Admin)  — SCRUM-48
// ============================================================

const API = "http://127.0.0.1:5000/api";


// ============================================================
// MODULE: QUẢN LÝ TỪ ĐIỂN TRIỆU CHỨNG (Admin)
// - CRUD đơn giản, tìm kiếm, import CSV, export CSV
// - Endpoints dự kiến: GET/POST/PUT/DELETE /api/symptoms
// ============================================================

(async function () {
  // State
  let _dictList = [];
  let _editDictId = null;

  // DOM refs
  const dictTbody = document.getElementById("dict-tbody");
  const dictEmpty = document.getElementById("dict-empty");
  const dictSearch = document.getElementById("dict-search");
  const btnAddDict = document.getElementById("btn-add-dict");
  const btnImportDict = document.getElementById("btn-import-dict");
  const dictFileInput = document.getElementById("dict-file-input");
  const btnExportDict = document.getElementById("btn-export-dict");

  // Create modal elements (lightweight, reuse modal style)
  const modalId = 'modal-dict';
  if (!document.getElementById(modalId)) {
    const modalHtml = `
    <div class="modal-overlay is-hidden" id="${modalId}" role="dialog" aria-modal="true" aria-labelledby="modal-dict-title">
      <div class="modal-card">
        <div class="modal-header">
          <h2 id="modal-dict-title">Thêm mục từ điển</h2>
          <button class="icon-button" type="button" id="modal-dict-close" aria-label="Đóng"><span class="material-symbols-outlined" aria-hidden="true">close</span></button>
        </div>
        <form id="modal-dict-form" class="modal-body" novalidate>
          <input type="hidden" id="modal-dict-id" />
          <div class="form-row">
            <div class="form-field"><label for="dict-vi">Triệu chứng (Tiếng Việt) *</label><input id="dict-vi" type="text" required placeholder="ví dụ: sốt"/></div>
            <div class="form-field"><label for="dict-en">Label (Tiếng Anh) *</label><input id="dict-en" type="text" required placeholder="ví dụ: fever"/></div>
          </div>
          <div class="form-field"><label for="dict-note">Ghi chú</label><input id="dict-note" type="text" placeholder="Ghi chú/alias"/></div>
          <p class="form-message" id="modal-dict-msg" role="status"></p>
          <div class="form-actions">
            <button class="primary-button" type="submit" id="modal-dict-submit"><span class="material-symbols-outlined">save</span> Lưu</button>
            <button class="secondary-button" type="button" id="modal-dict-cancel"><span class="material-symbols-outlined">close</span> Hủy</button>
          </div>
        </form>
      </div>
    </div>`;
    document.body.insertAdjacentHTML('beforeend', modalHtml);
  }

  const modalOverlay = document.getElementById(modalId);
  const modalForm = document.getElementById('modal-dict-form');
  const modalMsg = document.getElementById('modal-dict-msg');
  const modalSubmit = document.getElementById('modal-dict-submit');
  const inpId = document.getElementById('modal-dict-id');
  const inpVi = document.getElementById('dict-vi');
  const inpEn = document.getElementById('dict-en');
  const inpNote = document.getElementById('dict-note');
  const btnClose = document.getElementById('modal-dict-close');
  const btnCancel = document.getElementById('modal-dict-cancel');

  function setModalDictMsg(m, err = false) { modalMsg.textContent = m; modalMsg.className = 'form-message' + (err ? ' is-error' : ''); }

  // Fetch list
  async function loadDict() {
    try {
      const res = await fetch(`${API}/symptoms`);
      if (!res.ok) throw new Error('Không tải được từ điển.');
      const data = await res.json();
      _dictList = Array.isArray(data) ? data : (data.symptoms || []);
    } catch (e) {
      _dictList = [];
      console.error(e);
    }
    renderDictTable(dictSearch?.value || '');
  }

  function renderDictTable(keyword = '') {
    const kw = (keyword || '').trim().toLowerCase();
    dictTbody.innerHTML = '';
    const filtered = _dictList.filter(item => {
      if (!kw) return true;
      return (item.label_vi || '').toLowerCase().includes(kw) || (item.label_en || '').toLowerCase().includes(kw) || (item.note || '').toLowerCase().includes(kw);
    });
    if (filtered.length === 0) {
      dictEmpty.classList.remove('is-hidden');
      dictTbody.innerHTML = '';
      return;
    }
    dictEmpty.classList.add('is-hidden');
    filtered.forEach(item => {
      const tr = document.createElement('tr');
      tr.innerHTML = `
        <td style="padding:10px;">${item.id ?? ''}</td>
        <td style="padding:10px;">${escapeHtml(item.label_vi || item.label || '')}</td>
        <td style="padding:10px;">${escapeHtml(item.label_en || '')}</td>
        <td style="padding:10px;">${escapeHtml(item.note || '')}</td>
        <td style="text-align:center; padding:10px; white-space:nowrap;">
          <button class="text-button" data-action="edit" data-id="${item.id}" style="margin-right:8px;"><span class="material-symbols-outlined">edit</span> Sửa</button>
          <button class="text-button" data-action="delete" data-id="${item.id}"><span class="material-symbols-outlined">delete</span> Xóa</button>
        </td>`;
      dictTbody.appendChild(tr);
    });
  }

  function openAddDict() {
    _editDictId = null;
    inpId.value = '';
    inpVi.value = '';
    inpEn.value = '';
    inpNote.value = '';
    setModalDictMsg('');
    document.getElementById('modal-dict-title').textContent = 'Thêm mục từ điển';
    modalSubmit.innerHTML = '<span class="material-symbols-outlined">add</span> Thêm';
    modalOverlay.classList.remove('is-hidden');
    inpVi.focus();
  }

  function openEditDict(id) {
    const item = _dictList.find(x => String(x.id) === String(id));
    if (!item) return alert('Không tìm thấy mục.');
    _editDictId = item.id;
    inpId.value = item.id;
    inpVi.value = item.label_vi || item.label || '';
    inpEn.value = item.label_en || '';
    inpNote.value = item.note || '';
    setModalDictMsg('');
    document.getElementById('modal-dict-title').textContent = 'Sửa mục từ điển';
    modalSubmit.innerHTML = '<span class="material-symbols-outlined">save</span> Lưu';
    modalOverlay.classList.remove('is-hidden');
    inpVi.focus();
  }

  function closeModalDict() { modalOverlay.classList.add('is-hidden'); setModalDictMsg(''); _editDictId = null; }

  modalForm?.addEventListener('submit', async (e) => {
    e.preventDefault();
    setModalDictMsg('');
    const vi = inpVi.value.trim();
    const en = inpEn.value.trim();
    if (!vi || !en) { setModalDictMsg('Vui lòng nhập cả Tiếng Việt và Label Tiếng Anh.', true); return; }
    const payload = { label_vi: vi, label_en: en, note: inpNote.value.trim() || null };
    try {
      const method = _editDictId ? 'PUT' : 'POST';
      const url = _editDictId ? `${API}/symptoms/${_editDictId}` : `${API}/symptoms`;
      const res = await fetch(url, { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(payload) });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) { setModalDictMsg(data.error || 'Lỗi lưu mục', true); return; }
      closeModalDict();
      await loadDict();
    } catch (err) {
      setModalDictMsg('Không kết nối được máy chủ.', true);
    }
  });

  btnClose?.addEventListener('click', closeModalDict);
  btnCancel?.addEventListener('click', closeModalDict);
  modalOverlay?.addEventListener('click', (e) => { if (e.target === modalOverlay) closeModalDict(); });

  // actions in table
  dictTbody?.addEventListener('click', (e) => {
    const btn = e.target.closest('button[data-action]');
    if (!btn) return;
    const act = btn.dataset.action;
    const id = btn.dataset.id;
    if (act === 'edit') openEditDict(id);
    if (act === 'delete') confirmDeleteDict(id);
  });


// =========================================================
// TASK 65 & 66: XỬ LÝ XÓA LỊCH SỬ DỰ ĐOÁN VỚI MODAL HIỆN ĐẠI
// =========================================================
let currentDeleteId = null;

// 1. Hàm này gắn vào nút "Xóa" ngoài giao diện lịch sử để mở Modal
function confirmDelete(id) {
    currentDeleteId = id; 
    const modal = document.getElementById('delete-confirm-modal');
    if (modal) {
        modal.classList.remove('is-hidden'); 
    }
}

// 2. Hàm này dùng để đóng Modal khi bấm Hủy
function closeDeleteModal() {
    currentDeleteId = null;
    const modal = document.getElementById('delete-confirm-modal');
    if (modal) {
        modal.classList.add('is-hidden'); 
    }
}

// 3. Hàm thực thi xóa khi bấm nút "Xác nhận xóa" bên trong Modal (Viết theo đúng phong cách của nhóm bạn)
async function executeDeleteHistory() {
    if (!currentDeleteId) return;
    try {
        // Gọi tới API của Flask Backend (Cổng 5000)
        const res = await fetch(`http://127.0.0.1:5000/api/evaluation/${currentDeleteId}`, { method: 'DELETE' });
        
        if (!res.ok) { 
            const d = await res.json().catch(() => ({})); 
            alert(d.message || 'Xóa thất bại'); 
            closeDeleteModal();
            return; 
        }
        
        alert('Xóa bản ghi lịch sử thành công!');
        
        // Xóa dòng đó trên giao diện mà không cần reload
        const element = document.getElementById(`record-${currentDeleteId}`);
        if (element) {
            element.remove();
        } else {
            window.location.reload(); // Dự phòng nếu không tìm thấy ID dòng
        }
    } catch (e) { 
        alert('Không kết nối máy chủ Backend.'); 
    } finally {
        closeDeleteModal(); // Luôn luôn đóng modal sau khi chạy xong
    }
}


  async function confirmDeleteDict(id) {
    if (!confirm('Xóa mục này khỏi từ điển?')) return;
    try {
      const res = await fetch(`${API}/symptoms/${id}`, { method: 'DELETE' });
      if (!res.ok) { const d = await res.json().catch(()=>({})); alert(d.error || 'Xóa thất bại'); return; }
      await loadDict();
    } catch (e) { alert('Không kết nối máy chủ.'); }
  }

  // search
  dictSearch?.addEventListener('input', (e) => renderDictTable(e.target.value));

  // add
  btnAddDict?.addEventListener('click', openAddDict);

  // import CSV
  btnImportDict?.addEventListener('click', () => dictFileInput.click());
  dictFileInput?.addEventListener('change', async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    try {
      const text = await f.text();
      const parsed = parseCSV(text);
      // expect columns like label_vi,label_en,note
      const header = parsed.header.map(h => h.toLowerCase());
      const viIdx = header.findIndex(h => h.includes('vi') || h.includes('label_vi') || h.includes('tieng_viet') || h.includes('vietnam'));
      const enIdx = header.findIndex(h => h.includes('en') || h.includes('label_en') || h.includes('label') || h.includes('english'));
      if (viIdx === -1 || enIdx === -1) {
        alert('CSV phải có cột chứa Tiếng Việt và Label Tiếng Anh (ví dụ header: label_vi,label_en).');
        return;
      }
      let added = 0, failed = 0;
      for (let i=0;i<parsed.data.length;i++){
        const row = parsed.data[i];
        const vi = row[header[viIdx]]?.trim() || '';
        const en = row[header[enIdx]]?.trim() || '';
        const note = (header.includes('note') ? (row['note'] || '') : (row[header.find(h=>h.includes('note'))]||''));
        if (!vi||!en){ failed++; continue; }
        try {
          const res = await fetch(`${API}/symptoms`, { method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({ label_vi:vi, label_en:en, note: note || null }) });
          if (res.ok) added++; else failed++;
        } catch { failed++; }
      }
      alert(`Nhập xong. Thêm: ${added}, Lỗi: ${failed}`);
      await loadDict();
    } catch (err) { alert('Lỗi đọc file CSV'); }
  });

  // export CSV
  btnExportDict?.addEventListener('click', () => {
    const rows = [ ['id','label_vi','label_en','note'] ];
    _dictList.forEach(r => rows.push([r.id, r.label_vi||r.label||'', r.label_en||'', r.note||'']));
    const csv = rows.map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n');
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a'); a.href = url; a.download = 'dictionary_export.csv'; a.click(); URL.revokeObjectURL(url);
  });

  // initial load when page is shown
  const origShow = window.showPage;
  window.showPage = function(pageName){ origShow(pageName); if (pageName === 'admin-dictionary') loadDict(); };

  // expose for debugging
  window._dictReload = loadDict;
})();

// ── State ──────────────────────────────────────────────────
let _thuocList    = [];   // cache danh sách thuốc
let _nhomList     = [];   // cache danh sách nhóm thuốc
let _thuocEditId  = null; // null = đang thêm mới

// ── DOM refs ───────────────────────────────────────────────
const pageThuoc      = document.getElementById("page-admin-thuoc");
const thuocTbody     = document.getElementById("admin-thuoc-tbody");
const thuocEmpty     = document.getElementById("admin-thuoc-empty");
const searchInput    = document.getElementById("thuoc-search-input");
const filterNhomSel  = document.getElementById("thuoc-filter-nhom");

const modalThuoc     = document.getElementById("modal-thuoc");
const modalTitle     = document.getElementById("modal-thuoc-title");
const modalForm      = document.getElementById("modal-thuoc-form");
const modalMsg       = document.getElementById("modal-thuoc-msg");
const modalSubmitBtn = document.getElementById("modal-thuoc-submit");

// form fields
const mtId       = document.getElementById("modal-thuoc-id");
const mtTen      = document.getElementById("mt-ten");
const mtNhom     = document.getElementById("mt-nhom");
const mtHoatChat = document.getElementById("mt-hoat-chat");
const mtHamLuong = document.getElementById("mt-ham-luong");
const mtDangBC   = document.getElementById("mt-dang-bao-che");
const mtDonVi    = document.getElementById("mt-don-vi");
const mtHangSX   = document.getElementById("mt-hang-sx");
const mtNuocSX   = document.getElementById("mt-nuoc-sx");
const mtSoDK     = document.getElementById("mt-so-dk");
const mtGia      = document.getElementById("mt-gia");
const mtMoTa     = document.getElementById("mt-mo-ta");

// ── Helpers ────────────────────────────────────────────────
function formatGia(val) {
  if (val == null || val === "") return "—";
  return new Intl.NumberFormat("vi-VN").format(val) + " ₫";
}
function esc(s) {
  if (!s) return "";
  return String(s)
    .replace(/&/g,"&amp;").replace(/</g,"&lt;")
    .replace(/>/g,"&gt;").replace(/"/g,"&quot;");
}
function setModalMsg(msg, isErr = false) {
  modalMsg.textContent = msg;
  modalMsg.className   = "form-message" + (isErr ? " is-error" : "");
}

// ── Nhóm thuốc: load cho dropdown ─────────────────────────
async function loadNhomThuocOptions() {
  try {
    const res = await fetch(`${API}/drug-groups`);
    _nhomList = await res.json();
  } catch (_) {
    _nhomList = [];
  }

  // Đổ vào select lọc (trang chính)
  if (filterNhomSel) {
    filterNhomSel.innerHTML = '<option value="">Tất cả nhóm thuốc</option>';
    _nhomList.forEach(n => {
      const o = document.createElement("option");
      o.value = n.id; o.textContent = n.ten_nhom;
      filterNhomSel.appendChild(o);
    });
  }

  // Đổ vào select trong modal
  if (mtNhom) {
    mtNhom.innerHTML = '<option value="">— Chọn nhóm thuốc —</option>';
    _nhomList.forEach(n => {
      const o = document.createElement("option");
      o.value = n.id; o.textContent = n.ten_nhom;
      mtNhom.appendChild(o);
    });
  }
}

// ── Thuốc: fetch từ API ────────────────────────────────────
async function fetchThuocList(nhomId = "") {
  const url = nhomId
    ? `${API}/thuoc?nhom_thuoc_id=${nhomId}`
    : `${API}/thuoc`;
  const res  = await fetch(url);
  _thuocList = await res.json();
}

// ── Thuốc: render bảng ────────────────────────────────────
function renderThuocTable(keyword = "") {
  const kw = keyword.trim().toLowerCase();
  const filtered = _thuocList.filter(t =>
    !kw ||
    t.ten_thuoc.toLowerCase().includes(kw) ||
    (t.hoat_chat || "").toLowerCase().includes(kw)
  );

  thuocTbody.innerHTML = "";

  if (filtered.length === 0) {
    thuocTbody.innerHTML = `
      <tr><td colspan="8" class="admin-table-empty">
        <span class="material-symbols-outlined">search_off</span>
        ${kw ? "Không tìm thấy thuốc phù hợp." : "Chưa có thuốc nào trong nhóm này."}
      </td></tr>`;
    thuocEmpty.classList.toggle("is-hidden", kw !== "");
    return;
  }

  thuocEmpty.classList.add("is-hidden");

  filtered.forEach(t => {
    const tr = document.createElement("tr");
    tr.innerHTML = `
      <td style="color:var(--text-muted);font-size:.85rem">${t.id}</td>
      <td>
        <div class="thuoc-name">${esc(t.ten_thuoc)}</div>
        ${t.so_dang_ky ? `<div class="thuoc-sub">SĐK: ${esc(t.so_dang_ky)}</div>` : ""}
      </td>
      <td>${esc(t.hoat_chat) || "<span style='color:var(--text-muted)'>—</span>"}</td>
      <td>${esc(t.ham_luong) || "<span style='color:var(--text-muted)'>—</span>"}</td>
      <td>${esc(t.dang_bao_che) || "<span style='color:var(--text-muted)'>—</span>"}</td>
      <td>
        ${t.nhom_thuoc
          ? `<span class="nhom-badge">${esc(t.nhom_thuoc.ten_nhom)}</span>`
          : "<span style='color:var(--text-muted)'>—</span>"}
      </td>
      <td class="gia-cell">${formatGia(t.gia_tham_khao)}</td>
      <td class="action-cell">
        <button class="icon-button" title="Sửa thuốc"
                onclick="openEditThuoc(${t.id})" aria-label="Sửa ${esc(t.ten_thuoc)}">
          <span class="material-symbols-outlined">edit</span>
        </button>
        <button class="icon-button btn-delete-thuoc" title="Xóa thuốc"
                onclick="confirmDeleteThuoc(${t.id}, '${esc(t.ten_thuoc)}')"
                aria-label="Xóa ${esc(t.ten_thuoc)}">
          <span class="material-symbols-outlined">delete</span>
        </button>
      </td>`;
    thuocTbody.appendChild(tr);
  });
}

// ── Load + render tổng hợp ─────────────────────────────────
async function reloadThuoc() {
  thuocTbody.innerHTML = `
    <tr><td colspan="8" class="admin-table-empty">
      <span class="material-symbols-outlined">hourglass_empty</span>
      Đang tải...
    </td></tr>`;
  thuocEmpty.classList.add("is-hidden");

  const nhomId = filterNhomSel?.value || "";
  await fetchThuocList(nhomId);
  renderThuocTable(searchInput?.value || "");
}

// ── Modal: mở thêm mới ────────────────────────────────────
function openAddThuoc() {
  _thuocEditId = null;
  modalTitle.textContent = "Thêm thuốc mới";
  modalSubmitBtn.innerHTML = `<span class="material-symbols-outlined">add</span> Thêm thuốc`;
  modalForm.reset();
  mtId.value = "";
  setModalMsg("");
  modalThuoc.classList.remove("is-hidden");
  mtTen.focus();
}

// ── Modal: mở sửa ─────────────────────────────────────────
async function openEditThuoc(id) {
  _thuocEditId = id;
  modalTitle.textContent = "Sửa thông tin thuốc";
  modalSubmitBtn.innerHTML = `<span class="material-symbols-outlined">save</span> Lưu thay đổi`;
  setModalMsg("");

  // Lấy dữ liệu hiện tại
  try {
    const res = await fetch(`${API}/thuoc/${id}`);
    if (!res.ok) throw new Error();
    const t = await res.json();

    mtId.value          = t.id;
    mtTen.value         = t.ten_thuoc       || "";
    mtNhom.value        = t.nhom_thuoc_id   || "";
    mtHoatChat.value    = t.hoat_chat       || "";
    mtHamLuong.value    = t.ham_luong       || "";
    mtDangBC.value      = t.dang_bao_che    || "";
    mtDonVi.value       = t.don_vi_tinh     || "";
    mtHangSX.value      = t.hang_san_xuat   || "";
    mtNuocSX.value      = t.nuoc_san_xuat   || "";
    mtSoDK.value        = t.so_dang_ky      || "";
    mtGia.value         = t.gia_tham_khao   || "";
    mtMoTa.value        = t.mo_ta           || "";

    modalThuoc.classList.remove("is-hidden");
    mtTen.focus();
  } catch {
    alert("Không thể tải thông tin thuốc. Vui lòng thử lại.");
  }
}

// ── Modal: đóng ───────────────────────────────────────────
function closeThuocModal() {
  modalThuoc.classList.add("is-hidden");
  modalForm.reset();
  setModalMsg("");
  _thuocEditId = null;
}

// ── Modal: submit (thêm hoặc sửa) ─────────────────────────
modalForm?.addEventListener("submit", async (e) => {
  e.preventDefault();
  setModalMsg("");

  const ten   = mtTen.value.trim();
  const nhomId = parseInt(mtNhom.value);

  if (!ten)    { setModalMsg("Vui lòng nhập tên thuốc.", true); mtTen.focus();  return; }
  if (!nhomId) { setModalMsg("Vui lòng chọn nhóm thuốc.", true); mtNhom.focus(); return; }

  const payload = {
    ten_thuoc:    ten,
    nhom_thuoc_id: nhomId,
    hoat_chat:    mtHoatChat.value.trim() || null,
    ham_luong:    mtHamLuong.value.trim() || null,
    dang_bao_che: mtDangBC.value.trim()   || null,
    don_vi_tinh:  mtDonVi.value.trim()    || null,
    hang_san_xuat:mtHangSX.value.trim()   || null,
    nuoc_san_xuat:mtNuocSX.value.trim()   || null,
    so_dang_ky:   mtSoDK.value.trim()     || null,
    gia_tham_khao:mtGia.value !== "" ? parseFloat(mtGia.value) : null,
    mo_ta:        mtMoTa.value.trim()     || null,
  };

  const isEdit  = Boolean(_thuocEditId);
  const url     = isEdit ? `${API}/thuoc/${_thuocEditId}` : `${API}/thuoc`;
  const method  = isEdit ? "PUT" : "POST";

  // Disable button
  modalSubmitBtn.disabled = true;
  const origHtml = modalSubmitBtn.innerHTML;
  modalSubmitBtn.innerHTML = `<span class="material-symbols-outlined">hourglass_empty</span> Đang lưu...`;

  try {
    const res  = await fetch(url, {
      method,
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });
    const data = await res.json();

    if (!res.ok) {
      setModalMsg(data.error || "Có lỗi xảy ra.", true);
      return;
    }

    closeThuocModal();
    await reloadThuoc();

  } catch {
    setModalMsg("Không kết nối được máy chủ.", true);
  } finally {
    modalSubmitBtn.disabled = false;
    modalSubmitBtn.innerHTML = origHtml;
  }
});

// ── Xóa thuốc ─────────────────────────────────────────────
window.confirmDeleteThuoc = async function (id, ten) {
  if (!confirm(`Xóa thuốc "${ten}"?\nThao tác này không thể hoàn tác.`)) return;
  try {
    const res = await fetch(`${API}/thuoc/${id}`, { method: "DELETE" });
    if (res.ok) {
      await reloadThuoc();
    } else {
      const d = await res.json();
      alert(d.error || "Xóa thất bại.");
    }
  } catch {
    alert("Không kết nối được máy chủ.");
  }
};

// ── Expose để HTML onclick dùng được ──────────────────────
window.openEditThuoc = openEditThuoc;

// ── Sự kiện tìm kiếm & lọc ────────────────────────────────
searchInput?.addEventListener("input", () =>
  renderThuocTable(searchInput.value));

filterNhomSel?.addEventListener("change", reloadThuoc);

// ── Nút mở modal thêm mới ─────────────────────────────────
document.getElementById("btn-mo-them-thuoc")
  ?.addEventListener("click", openAddThuoc);
document.getElementById("btn-mo-them-thuoc-2")
  ?.addEventListener("click", openAddThuoc);
document.getElementById("btn-add-thuoc")
  ?.addEventListener("click", openAddThuoc);

// ── Đóng modal ────────────────────────────────────────────
document.getElementById("modal-thuoc-close")
  ?.addEventListener("click", closeThuocModal);
document.getElementById("modal-thuoc-cancel")
  ?.addEventListener("click", closeThuocModal);

// Click ra ngoài modal cũng đóng
modalThuoc?.addEventListener("click", (e) => {
  if (e.target === modalThuoc) closeThuocModal();
});

// ESC đóng modal
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape" && !modalThuoc.classList.contains("is-hidden"))
    closeThuocModal();
});

// ── Hook vào showPage để load dữ liệu khi vào trang ───────
const _origShowPage = showPage;
window.showPage = function(pageName) {
  _origShowPage(pageName);
  if (pageName === "admin-thuoc") {
    loadNhomThuocOptions().then(reloadThuoc);
  }
};

// ════════════════════════════════════════════════════════════
// ── DRAG & DROP FILE UPLOAD COMPONENT ──────────────────────
// ════════════════════════════════════════════════════════════

const uploadZone = document.getElementById("file-upload-zone");
const fileInput = document.getElementById("file-upload-input");
const fileUploadBrowse = document.getElementById("file-upload-browse");
const btnToggleUpload = document.getElementById("btn-toggle-upload");

if (uploadZone && fileInput && btnToggleUpload) {
  // Toggle upload zone visibility
  btnToggleUpload.addEventListener("click", () => {
    const isVisible = uploadZone.style.display !== "none";
    uploadZone.style.display = isVisible ? "none" : "block";
    if (!isVisible) {
      fileInput.value = "";
      uploadZone.querySelector(".upload-progress").style.display = "none";
      uploadZone.querySelector(".upload-result").style.display = "none";
    }
  });

  // Browse button click
  fileUploadBrowse?.addEventListener("click", (e) => {
    e.preventDefault();
    fileInput.click();
  });

  // File input change
  fileInput.addEventListener("change", (e) => {
    const files = e.target.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  });

  // Drag and drop events
  uploadZone.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.style.borderColor = "var(--primary)";
    uploadZone.style.background = "rgba(var(--primary-rgb), 0.05)";
  });

  uploadZone.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.style.borderColor = "var(--outline)";
    uploadZone.style.background = "var(--surface-low)";
  });

  uploadZone.addEventListener("drop", (e) => {
    e.preventDefault();
    e.stopPropagation();
    uploadZone.style.borderColor = "var(--outline)";
    uploadZone.style.background = "var(--surface-low)";
    
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileUpload(files[0]);
    }
  });

  // Click on zone to select file
  uploadZone.addEventListener("click", (e) => {
    if (e.target.id !== "file-upload-browse") {
      fileInput.click();
    }
  });
}

// Parse CSV data
function parseCSV(text) {
  const lines = text.split("\n").map(l => l.trim()).filter(l => l);
  const header = lines[0].split(",").map(h => h.trim().toLowerCase());
  
  const data = [];
  for (let i = 1; i < lines.length; i++) {
    const values = parseCSVLine(lines[i]);
    if (values.length < 2) continue; // Skip empty lines
    
    const row = {};
    header.forEach((col, idx) => {
      row[col] = values[idx] ? values[idx].trim() : "";
    });
    data.push(row);
  }
  return { header, data };
}

// Parse CSV line handling quoted values
function parseCSVLine(line) {
  const result = [];
  let current = "";
  let inQuotes = false;
  
  for (let i = 0; i < line.length; i++) {
    const char = line[i];
    const nextChar = line[i + 1];
    
    if (char === '"') {
      if (inQuotes && nextChar === '"') {
        current += '"';
        i++;
      } else {
        inQuotes = !inQuotes;
      }
    } else if (char === "," && !inQuotes) {
      result.push(current);
      current = "";
    } else {
      current += char;
    }
  }
  result.push(current);
  return result;
}

// Parse XLSX (simplified - requires reading file)
async function parseXLSX(file) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const data = new Uint8Array(e.target.result);
        const sheet = XLSX.read(data, { type: "array" });
        const firstSheet = sheet.Sheets[sheet.SheetNames[0]];
        const rows = XLSX.utils.sheet_to_json(firstSheet, { defval: "" });
        
        if (rows.length === 0) {
          resolve({ header: [], data: [] });
          return;
        }
        
        const header = Object.keys(rows[0]).map(k => k.toLowerCase());
        resolve({ header, data: rows });
      } catch (err) {
        console.error("XLSX parsing error:", err);
        resolve({ header: [], data: [] });
      }
    };
    reader.readAsArrayBuffer(file);
  });
}

// Map column names flexibly
function mapColumnName(columnName, possibleNames) {
  const normalized = columnName.toLowerCase().trim();
  for (const name of possibleNames) {
    if (normalized.includes(name.toLowerCase()) || name.toLowerCase().includes(normalized)) {
      return true;
    }
  }
  return normalized.length > 0 && possibleNames.some(n => n.length > 0);
}

// Main file upload handler
async function handleFileUpload(file) {
  const uploadProgress = uploadZone.querySelector(".upload-progress");
  const uploadResult = uploadZone.querySelector(".upload-result");
  const uploadStatus = document.getElementById("upload-status");
  const uploadCount = document.getElementById("upload-count");
  const uploadResultText = document.getElementById("upload-result-text");
  const progressBar = document.getElementById("upload-progress-bar");

  uploadProgress.style.display = "block";
  uploadResult.style.display = "none";
  progressBar.style.width = "0%";

  const fileName = file.name.toLowerCase();
  let parsedData;

  try {
    if (fileName.endsWith(".csv")) {
      uploadStatus.textContent = "Đang đọc file CSV...";
      const text = await file.text();
      parsedData = parseCSV(text);
    } else if (fileName.endsWith(".xlsx") || fileName.endsWith(".xls")) {
      uploadStatus.textContent = "Đang đọc file Excel...";
      
      // Load XLSX library if not available
      if (typeof XLSX === "undefined") {
        const script = document.createElement("script");
        script.src = "https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.min.js";
        document.head.appendChild(script);
        
        await new Promise(resolve => {
          script.onload = resolve;
        });
      }
      
      parsedData = await parseXLSX(file);
    } else {
      throw new Error("Định dạng file không hỗ trợ. Vui lòng sử dụng CSV hoặc XLSX.");
    }

    if (!parsedData || parsedData.data.length === 0) {
      throw new Error("File không chứa dữ liệu hoặc định dạng không đúng.");
    }

    uploadStatus.textContent = `Đang nhập ${parsedData.data.length} hàng...`;
    const totalItems = parsedData.data.length;

    // Map columns
    const header = parsedData.header || Object.keys(parsedData.data[0] || {});
    const colMap = {
      ten: header.find(h => h.includes("ten") || h.includes("name") || h === "tên"),
      hoatChat: header.find(h => h.includes("hoat") || h.includes("active") || h.includes("substance")),
      hamLuong: header.find(h => h.includes("ham") || h.includes("strength") || h.includes("dose")),
      dangBaoChe: header.find(h => h.includes("dang") || h.includes("form")),
      nhom: header.find(h => h.includes("nhom") || h.includes("group")),
      gia: header.find(h => h.includes("gia") || h.includes("price")),
      donVi: header.find(h => h.includes("don") || h.includes("unit")),
      hangSx: header.find(h => h.includes("hang") || h.includes("manufacturer")),
      nuocSx: header.find(h => h.includes("nuoc") || h.includes("country")),
      soDk: header.find(h => h.includes("so") || h.includes("registration")),
      moTa: header.find(h => h.includes("mo") || h.includes("description"))
    };

    // Check required columns
    if (!colMap.ten || !colMap.nhom) {
      throw new Error("File phải chứa cột 'Tên thuốc' (name) và 'Nhóm thuốc' (group). Kiểm tra tiêu đề cột.");
    }

    let successCount = 0;
    let errorCount = 0;
    const errors = [];

    // Fetch nhom mapping
    const nhomsResp = await fetch(`${API_BASE_URL}/api/nhom-thuoc`);
    const nhomsList = (await nhomsResp.json()) || [];
    const nhomMap = {};
    nhomsList.forEach(n => {
      nhomMap[n.ten.toLowerCase()] = n.id;
    });

    // Process each row
    for (let i = 0; i < totalItems; i++) {
      try {
        const row = parsedData.data[i];
        const ten = row[colMap.ten]?.trim();
        const nhomName = row[colMap.nhom]?.trim();

        if (!ten || !nhomName) {
          errorCount++;
          errors.push(`Hàng ${i + 2}: Thiếu tên thuốc hoặc nhóm thuốc`);
          continue;
        }

        const nhomId = nhomMap[nhomName.toLowerCase()];
        if (!nhomId) {
          errorCount++;
          errors.push(`Hàng ${i + 2}: Nhóm thuốc "${nhomName}" không tồn tại`);
          continue;
        }

        const thuocData = {
          ten: ten,
          nhom_id: nhomId,
          hoat_chat: row[colMap.hoatChat]?.trim() || "",
          ham_luong: row[colMap.hamLuong]?.trim() || "",
          dang_bao_che: row[colMap.dangBaoChe]?.trim() || "",
          don_vi: row[colMap.donVi]?.trim() || "",
          hang_sx: row[colMap.hangSx]?.trim() || "",
          nuoc_sx: row[colMap.nuocSx]?.trim() || "",
          so_dk: row[colMap.soDk]?.trim() || "",
          gia: parseInt(row[colMap.gia]) || 0,
          mo_ta: row[colMap.moTa]?.trim() || ""
        };

        // Send to API
        const response = await fetch(`${API_BASE_URL}/api/thuoc`, {
          method: "POST",
          headers: {
            "Authorization": `Bearer ${authToken}`,
            "Content-Type": "application/json"
          },
          body: JSON.stringify(thuocData)
        });

        if (response.ok) {
          successCount++;
        } else {
          errorCount++;
          const errText = await response.text();
          errors.push(`Hàng ${i + 2}: ${errText || "Lỗi thêm thuốc"}`);
        }
      } catch (err) {
        errorCount++;
        errors.push(`Hàng ${i + 2}: ${err.message}`);
      }

      // Update progress
      const progress = ((i + 1) / totalItems) * 100;
      progressBar.style.width = progress + "%";
      uploadCount.textContent = `${successCount} thành công / ${i + 1} hàng`;
    }

    // Show result
    uploadProgress.style.display = "none";
    uploadResult.style.display = "block";
    
    let resultHTML = `<strong>✅ Nhập file thành công!</strong><br>Thêm ${successCount} thuốc`;
    if (errorCount > 0) {
      resultHTML += `<br>❌ Lỗi: ${errorCount} hàng`;
      if (errors.length > 0 && errors.length <= 5) {
        resultHTML += "<br><small>" + errors.join("<br>") + "</small>";
      }
    }
    uploadResultText.innerHTML = resultHTML;

    // Reload table
    setTimeout(() => {
      reloadThuoc();
    }, 1000);

  } catch (error) {
    uploadProgress.style.display = "none";
    uploadResult.style.display = "block";
    uploadResult.style.background = "rgba(var(--error-rgb, 220, 38, 38), 0.1)";
    uploadResultText.innerHTML = `<strong>❌ Lỗi:</strong> ${error.message}`;
  }
}
function renderTop3DrugGroups(predictions = [], matchedSymptoms = []) {
    const resultArea = document.getElementById("prediction-result");

    if (!resultArea) {
        console.warn("Không tìm thấy #prediction-result");
        return;
    }

    const top3 = predictions.slice(0, 3);

    const top3Html = top3.map((item, index) => {
        const groupName =
            item.group ||
            item.group_name ||
            item.ten_nhom ||
            item.label ||
            "Nhóm thuốc không xác định";

        const score =
            item.score ??
            item.confidence ??
            item.probability ??
            0;

        const percent = Number(score).toFixed(1);

        return `
            <div class="top-drug-item">
                <div class="top-drug-header">
                    <span class="top-drug-rank">Top ${index + 1}</span>
                    <strong>${groupName}</strong>
                    <span>${percent}%</span>
                </div>

                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${percent}%"></div>
                </div>
            </div>
        `;
    }).join("");

    const symptomsHtml = matchedSymptoms.length > 0
        ? matchedSymptoms.map(symptom => `<span class="symptom-chip">${symptom}</span>`).join("")
        : `<span class="text-muted">Chưa có triệu chứng khớp.</span>`;

    resultArea.innerHTML += `
        <div class="result-card mt-3">
            <h3>Top 3 nhóm thuốc gợi ý</h3>
            ${top3Html || "<p>Chưa có kết quả dự đoán.</p>"}
        </div>

        <div class="result-card mt-3">
            <h3>Triệu chứng đã khớp</h3>
            <div class="symptom-chip-list">
                ${symptomsHtml}
            </div>
        </div>
    `;
}



// Hàm xử lý khi bấm "Đồng ý"
function handleApprove() {
    alert("Cảm ơn bác sĩ đã xác nhận kết quả chính xác!");
    const btn = document.getElementById('btnApprove');
    if (btn) {
        btn.className = "btn btn-success px-4 py-2 fw-semibold";
        btn.disabled = true;
    }
}

/// ==========================================
// ĐOẠN MÃ MỚI SỬ DỤNG FETCH() ĐỂ GỌI API (TASK 45)
// ==========================================

// 1. Hàm xử lý khi bấm nút "Đồng ý" -> Gửi trạng thái APPROVE về Backend
function handleApprove() {
    // Lấy tên triệu chứng hiện tại từ giao diện (ví dụ lấy từ thẻ h1 hiển thị kết quả)
    const symptomName = document.getElementById('result-title')?.innerText || "Triệu chứng ẩn danh";

    fetch('http://127.0.0.1:5000/api/evaluation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            trieu_chung_nhap: symptomName,
            trang_thai: 'APPROVE',
            ghi_chu: ''
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Cảm ơn bác sĩ đã xác nhận kết quả chính xác!");
            const btn = document.getElementById('btnApprove');
            if (btn) {
                btn.style.background = "#059669";
                btn.style.color = "#ffffff";
                btn.disabled = true;
                btn.innerText = "Đã đồng ý";
            }
        }
    })
    .catch(err => console.error("Lỗi gửi đánh giá:", err));
}

// 2. Hàm xử lý khi viết ghi chú và bấm "Gửi đánh giá" -> Gửi trạng thái REJECT kèm lời nhắn
function submitRejectFeedback() {
    const notes = document.getElementById('feedbackNotes').value.trim();
    const symptomName = document.getElementById('result-title')?.innerText || "Triệu chứng ẩn danh";

    if (!notes) {
        alert("Vui lòng nhập lý do hoặc ghi chú trước khi gửi!");
        return;
    }

    fetch('http://127.0.0.1:5000/api/evaluation', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            trieu_chung_nhap: symptomName,
            trang_thai: 'REJECT',
            ghi_chu: notes
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            alert("Hệ thống đã ghi nhận phản hồi đóng góp của bạn!");
            
            // Xóa nội dung trong ô nhập và đóng Modal ẩn đi
            document.getElementById('feedbackNotes').value = '';
            const modalEl = document.getElementById('feedbackModal');
            const modal = bootstrap.Modal.getInstance(modalEl);
            if (modal) {
                modal.hide();
            }
        }
    })
    .catch(err => console.error("Lỗi gửi phản hồi:", err));
}

// ────────────────────────────────────────────────────────────────────────────
// FEEDBACK STATISTICS (DASHBOARD)
// ────────────────────────────────────────────────────────────────────────────

let feedbackChartInstance = null;

// Register custom plugin for center label in doughnut chart
const centerLabelPlugin = {
    id: 'centerLabel',
    afterDraw(chart) {
        const {width, height} = chart;
        const ctx = chart.ctx;
        
        // Calculate font size responsively
        const fontSize = Math.min(width, height) / 8;
        const smallFontSize = fontSize / 1.5;
        
        // Get chart data
        const data = chart.data.datasets[0].data;
        const total = data.reduce((a, b) => a + b, 0);
        
        // Draw text
        ctx.save();
        ctx.font = `bold ${fontSize}px Inter, system-ui`;
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#000000';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Main text
        ctx.fillText(total, width / 2, height / 2 - fontSize / 4);
        
        // Label text - "Tổng đánh giá"
        ctx.font = `500 ${smallFontSize}px Inter, system-ui`;
        ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#666666';
        ctx.fillText('Tổng đánh giá', width / 2, height / 2 + smallFontSize * 0.8);
        
        ctx.restore();
    }
};

// Register the plugin
if (window.Chart && window.Chart.register) {
    Chart.register(centerLabelPlugin);
}

async function loadFeedbackStatistics() {
    const loading = document.getElementById('feedback-stats-loading');
    const content = document.getElementById('feedback-stats-content');
    const empty = document.getElementById('feedback-stats-empty');
    const errorDiv = document.getElementById('feedback-stats-error');
    
    // Show loading state
    if (loading) loading.style.display = 'block';
    if (content) content.classList.add('is-hidden');
    if (empty) empty.classList.add('is-hidden');
    
    try {
        const response = await fetch('/api/feedback/statistics');
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.message || 'API returned error');
        }
        
        // Hide loading
        if (loading) loading.style.display = 'none';
        
        // Check for empty state
        if (data.total === 0) {
            if (content) content.classList.add('is-hidden');
            if (empty) empty.classList.remove('is-hidden');
            return;
        }
        
        // Update stat cards
        const agreeCount = document.getElementById('stat-agree-count');
        const agreePercent = document.getElementById('stat-agree-percent');
        const disagreeCount = document.getElementById('stat-disagree-count');
        const disagreePercent = document.getElementById('stat-disagree-percent');
        const totalCount = document.getElementById('stat-total-count');
        const consensusRate = document.getElementById('stat-consensus-rate');
        
        // Calculate consensus rate
        const consensus = data.agree_percentage;
        
        // Update values with animation
        if (agreeCount) {
            agreeCount.textContent = data.agree_count;
            agreeCount.parentElement.parentElement.style.animation = 'none';
            setTimeout(() => {
                agreeCount.parentElement.parentElement.style.animation = '';
            }, 10);
        }
        if (agreePercent) agreePercent.textContent = data.agree_percentage.toFixed(1) + '%';
        if (disagreeCount) disagreeCount.textContent = data.disagree_count;
        if (disagreePercent) disagreePercent.textContent = data.disagree_percentage.toFixed(1) + '%';
        if (totalCount) totalCount.textContent = data.total;
        if (consensusRate) consensusRate.textContent = data.agree_percentage.toFixed(1) + '%';
        
        // Update legend labels
        const legendAgreeCount = document.getElementById('legend-agree-count');
        const legendAgreePercent = document.getElementById('legend-agree-percent');
        const legendDisagreeCount = document.getElementById('legend-disagree-count');
        const legendDisagreePercent = document.getElementById('legend-disagree-percent');
        
        if (legendAgreeCount) legendAgreeCount.textContent = data.agree_count;
        if (legendAgreePercent) legendAgreePercent.textContent = data.agree_percentage.toFixed(0);
        if (legendDisagreeCount) legendDisagreeCount.textContent = data.disagree_count;
        if (legendDisagreePercent) legendDisagreePercent.textContent = data.disagree_percentage.toFixed(0);
        
        // Render chart
        renderFeedbackChart(data);
        
        // Show content, hide loading/error
        if (content) {
            content.classList.remove('is-hidden');
            if (errorDiv) errorDiv.classList.add('is-hidden');
        }
        
    } catch (error) {
        console.error('Error loading feedback statistics:', error);
        
        // Show error state
        if (loading) loading.style.display = 'none';
        if (content) content.classList.add('is-hidden');
        if (empty) empty.classList.add('is-hidden');
        if (errorDiv) errorDiv.classList.remove('is-hidden');
    }
}

function renderFeedbackChart(data) {
    const canvas = document.getElementById('feedbackChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy previous chart instance if it exists
    if (feedbackChartInstance) {
        feedbackChartInstance.destroy();
    }
    
    // Prepare chart options
    const textColor = getComputedStyle(document.documentElement).getPropertyValue('--text').trim() || '#0e1b2b';
    const mutedColor = getComputedStyle(document.documentElement).getPropertyValue('--text-muted').trim() || '#5a6675';
    
    // Create new chart with enhanced styling
    feedbackChartInstance = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Đồng ý', 'Không đồng ý'],
            datasets: [{
                data: [data.agree_count, data.disagree_count],
                backgroundColor: ['#22c55e', '#ef4444'],
                borderColor: [
                    getComputedStyle(document.documentElement).getPropertyValue('--surface').trim() || '#f5f7fb',
                    getComputedStyle(document.documentElement).getPropertyValue('--surface').trim() || '#f5f7fb'
                ],
                borderWidth: 3,
                hoverBorderWidth: 5,
                hoverOffset: 8,
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            animation: {
                duration: 800,
                easing: 'easeInOutQuart',
                delay: (context) => {
                    let delay = 0;
                    if (context.type === 'data' && context.mode === 'default' && !context.dropped) {
                        delay = context.dataIndex * 100 + context.datasetIndex * 50;
                    }
                    return delay;
                },
            },
            plugins: {
                centerLabel: {},
                legend: {
                    position: 'right',
                    align: 'center',
                    labels: {
                        color: textColor,
                        padding: 16,
                        font: {
                            size: 14,
                            weight: '500',
                            family: 'Inter, system-ui, -apple-system'
                        },
                        boxWidth: 12,
                        boxHeight: 12,
                        borderRadius: 3,
                        generateLabels(chart) {
                            const data = chart.data;
                            const datasets = data.datasets;
                            const total = datasets[0].data.reduce((a, b) => a + b, 0);
                            
                            return data.labels.map((label, i) => {
                                const value = datasets[0].data[i];
                                const percentage = total > 0 ? ((value / total) * 100).toFixed(0) : 0;
                                const emoji = i === 0 ? '🟢' : '🔴';
                                
                                return {
                                    text: `${emoji} ${label}\n${value} (${percentage}%)`,
                                    fillStyle: datasets[0].backgroundColor[i],
                                    hidden: false,
                                    index: i,
                                };
                            });
                        }
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: '#ffffff',
                    bodyColor: '#ffffff',
                    borderColor: 'rgba(255, 255, 255, 0.2)',
                    borderWidth: 1,
                    padding: 12,
                    displayColors: true,
                    boxWidth: 10,
                    boxHeight: 10,
                    cornerRadius: 6,
                    titleFont: {
                        size: 13,
                        weight: '600',
                        family: 'Inter, system-ui'
                    },
                    bodyFont: {
                        size: 12,
                        family: 'Inter, system-ui'
                    },
                    callbacks: {
                        title: function(context) {
                            const index = context[0].dataIndex;
                            const labels = ['Đồng ý', 'Không đồng ý'];
                            return labels[index] || '';
                        },
                        label: function(context) {
                            const value = context.parsed || 0;
                            const total = context.dataset.data.reduce((a, b) => a + b, 0);
                            const percentage = total > 0 ? ((value / total) * 100).toFixed(1) : 0;
                            return [`${value} đánh giá`, `${percentage}%`];
                        },
                        afterLabel: function(context) {
                            const index = context.dataIndex;
                            return index === 0 ? '✓ Chính xác' : '✗ Không chính xác';
                        }
                    }
                }
            }
        }
    });
}

// Hook into page switching
const originalPageSwitch = document.querySelector('[data-page="dashboard"]');
if (originalPageSwitch) {
    document.addEventListener('click', function(e) {
        if (e.target.closest('[data-page="dashboard"]')) {
            setTimeout(loadFeedbackStatistics, 100);
        }
    });
}

// Retry button handler
const retryBtn = document.getElementById('btn-retry-stats');
if (retryBtn) {
    retryBtn.addEventListener('click', loadFeedbackStatistics);
}

// Refresh empty state button handler
const refreshEmptyBtn = document.getElementById('btn-refresh-empty');
if (refreshEmptyBtn) {
    refreshEmptyBtn.addEventListener('click', loadFeedbackStatistics);
}

// Legend item hover effects
document.addEventListener('DOMContentLoaded', function() {
    const legendItems = document.querySelectorAll('.legend-item');
    if (legendItems.length > 0 && feedbackChartInstance) {
        legendItems.forEach((item, index) => {
            item.addEventListener('click', function() {
                if (feedbackChartInstance) {
                    feedbackChartInstance.toggleDataVisibility(index, true);
                }
            });
        });
    }
});
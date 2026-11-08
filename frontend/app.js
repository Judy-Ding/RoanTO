const CATEGORY_ICONS = { Navigate: "↗", Settle: "⌂", Explore: "✦", Connect: "♡" };
const CATEGORY_DESCRIPTIONS = {
  Navigate: "Build confidence getting around Toronto and using local transit.",
  Settle: "Figure out essential services and everyday systems in your new home.",
  Explore: "Discover places and experiences around the city at your own pace.",
  Connect: "Find activities and opportunities to meet people in your community.",
};

function showError(element, error) {
  element.textContent = error.message || "Something went wrong. Please try again.";
  element.hidden = false;
}

function showAuthNavigation(user) {
  const loginLink = document.querySelector("#auth-link");
  const userLabel = document.querySelector("#auth-user");
  const logoutButton = document.querySelector("#logout-button");
  if (loginLink) loginLink.hidden = Boolean(user);
  if (userLabel) {
    userLabel.textContent = user?.email || "Signed in";
    userLabel.hidden = !user;
  }
  if (logoutButton) logoutButton.hidden = !user;
}

let firebaseAuthError = null;

async function initializeFirebase() {
  try {
    const response = await fetch("/api/auth/config");
    const config = await response.json().catch(() => ({}));
    if (!response.ok) {
      throw new Error(config.detail || "Firebase is not configured yet.");
    }
    if (!window.firebase) {
      throw new Error("Firebase could not load. Check your internet connection and reload.");
    }
    const { authEmulatorUrl, ...firebaseConfig } = config;
    if (!firebase.apps.length) firebase.initializeApp(firebaseConfig);
    const auth = firebase.auth();
    if (authEmulatorUrl) auth.useEmulator(authEmulatorUrl, { disableWarnings: true });
    auth.onAuthStateChanged(showAuthNavigation);
    await new Promise((resolve, reject) => {
      const unsubscribe = auth.onAuthStateChanged(
        () => {
          unsubscribe();
          resolve();
        },
        (error) => {
          unsubscribe();
          reject(error);
        },
      );
    });
    document.querySelector("#logout-button")?.addEventListener("click", async () => {
      try {
        await auth.signOut();
        location.href = "/";
      } catch (error) {
        console.error("Could not sign out:", error);
      }
    });
    return auth;
  } catch (error) {
    firebaseAuthError = error;
    showAuthNavigation(null);
    return null;
  }
}

const firebaseAuthPromise = initializeFirebase();

async function api(path, options = {}) {
  const auth = await firebaseAuthPromise;
  const headers = { "Content-Type": "application/json", ...(options.headers || {}) };
  if (auth?.currentUser) {
    headers.Authorization = `Bearer ${await auth.currentUser.getIdToken()}`;
  }
  const response = await fetch(path, { ...options, headers });
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    const detail = typeof body.detail === "string" ? body.detail : "Something went wrong. Please try again.";
    throw new Error(detail);
  }
  return body;
}

async function requireSignedIn(errorElement) {
  const auth = await firebaseAuthPromise;
  if (!auth) {
    showError(errorElement, firebaseAuthError || new Error("Firebase authentication is not configured."));
    return false;
  }
  if (!auth.currentUser) {
    const next = `${location.pathname}${location.search}`;
    location.href = `/login.html?next=${encodeURIComponent(next)}`;
    return false;
  }
  return true;
}

function safeNextPath() {
  const requested = new URLSearchParams(location.search).get("next");
  return requested?.startsWith("/") && !requested.startsWith("//") ? requested : "/";
}

function firebaseErrorMessage(error) {
  const messages = {
    "auth/configuration-not-found": "Firebase Authentication is not set up for this project. In the Firebase Console open Authentication, click Get started, then enable Email/Password under Sign-in method.",
    "auth/operation-not-allowed": "Email/password sign-in is not enabled. In the Firebase Console go to Authentication → Sign-in method and enable Email/Password.",
    "auth/email-already-in-use": "That email already has an account. Try logging in instead.",
    "auth/invalid-email": "Enter a valid email address.",
    "auth/invalid-credential": "Email or password is incorrect.",
    "auth/user-disabled": "This account has been disabled.",
    "auth/too-many-requests": "Too many attempts. Wait a little and try again.",
    "auth/weak-password": "Choose a stronger password, at least 6 characters long.",
    "auth/invalid-api-key": "The Firebase API key in .env is invalid. Copy it again from Project settings → General.",
    "auth/api-key-not-valid.-please-pass-a-valid-api-key.": "The Firebase API key in .env is invalid. Copy it again from Project settings → General.",
    "auth/unauthorized-domain": "This domain is not authorized. Add it under Authentication → Settings → Authorized domains.",
    "auth/user-not-found": "Email or password is incorrect.",
    "auth/wrong-password": "Email or password is incorrect.",
    "auth/network-request-failed": "Could not reach Firebase. Check your internet connection.",
  };
  return messages[error.code] || error.message || "Authentication failed. Please try again.";
}

async function initializeAuthPage() {
  const form = document.querySelector("#auth-form");
  const error = document.querySelector("#auth-error");
  const success = document.querySelector("#auth-success");
  const heading = document.querySelector("#auth-heading");
  const description = document.querySelector("#auth-description");
  const submit = document.querySelector("#auth-submit");
  const password = document.querySelector("#auth-password");
  const loginTab = document.querySelector("#login-tab");
  const registerTab = document.querySelector("#register-tab");
  let mode = "login";

  function setMode(nextMode) {
    mode = nextMode;
    const registering = mode === "register";
    heading.textContent = registering ? "Create your account" : "Welcome back";
    description.textContent = registering
      ? "Register to save your plans and keep your progress."
      : "Log in to create and continue your personal plans.";
    submit.textContent = registering ? "Create account" : "Log in";
    password.autocomplete = registering ? "new-password" : "current-password";
    loginTab.classList.toggle("active", !registering);
    registerTab.classList.toggle("active", registering);
    loginTab.setAttribute("aria-selected", String(!registering));
    registerTab.setAttribute("aria-selected", String(registering));
    error.hidden = true;
    success.hidden = true;
  }

  loginTab.addEventListener("click", () => setMode("login"));
  registerTab.addEventListener("click", () => setMode("register"));

  const auth = await firebaseAuthPromise;
  if (!auth) {
    showError(error, firebaseAuthError || new Error("Firebase authentication is not configured."));
    submit.disabled = true;
    return;
  }
  if (auth.currentUser) {
    location.replace(safeNextPath());
    return;
  }

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    success.hidden = true;
    submit.disabled = true;
    submit.textContent = mode === "register" ? "Creating account…" : "Logging in…";
    const email = document.querySelector("#auth-email").value.trim();
    try {
      if (mode === "register") {
        await auth.createUserWithEmailAndPassword(email, password.value);
        success.textContent = "Your account is ready.";
        success.hidden = false;
      } else {
        await auth.signInWithEmailAndPassword(email, password.value);
      }
      location.replace(safeNextPath());
    } catch (caught) {
      showError(error, new Error(firebaseErrorMessage(caught)));
    } finally {
      submit.disabled = false;
      submit.textContent = mode === "register" ? "Create account" : "Log in";
    }
  });
}

function escapeHTML(value) {
  return String(value).replace(/[&<>"']/g, (char) => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

async function initializeHome() {
  const groups = document.querySelector("#mission-groups");
  const error = document.querySelector("#home-error");
  const params = new URLSearchParams(location.search);
  const requestedPillar = params.get("pillar");
  const categories = ["Navigate", "Settle", "Explore", "Connect"];
  const selectedPillar = categories.includes(requestedPillar) ? requestedPillar : null;
  try {
    const missions = await api("/api/missions");
    const heading = document.querySelector("#pillar-heading");
    const eyebrow = document.querySelector("#pillar-eyebrow");
    const description = document.querySelector("#pillar-description");
    const back = document.querySelector("#pillar-back");
    const customGoal = document.querySelector("#custom-goal-card");

    if (selectedPillar) {
      eyebrow.textContent = "Your focus";
      heading.textContent = selectedPillar;
      description.textContent = CATEGORY_DESCRIPTIONS[selectedPillar];
      back.hidden = false;
      customGoal.href = `/ai_plan.html?mission=custom&pillar=${encodeURIComponent(selectedPillar)}`;
      groups.innerHTML = `<section class="mission-group pillar-missions">
        <h3 class="category-title"><span class="category-icon">${CATEGORY_ICONS[selectedPillar]}</span>${selectedPillar} goals</h3>
        ${missions.filter((mission) => mission.category === selectedPillar).map((mission) => `
          <a class="mission-card" href="/ai_plan.html?mission=${encodeURIComponent(mission.id)}&pillar=${encodeURIComponent(selectedPillar)}">
            <div><strong>${escapeHTML(mission.title)}</strong><span>${escapeHTML(mission.description)}</span></div>
            <span class="mission-arrow" aria-hidden="true">→</span>
          </a>`).join("")}
      </section>`;
    } else {
      eyebrow.textContent = "Start with a pillar";
      heading.textContent = "What would you like to focus on?";
      description.textContent = "Choose an area of everyday life to see goals that fit.";
      back.hidden = true;
      customGoal.href = "/ai_plan.html?mission=custom";
      groups.innerHTML = categories.map((category) => {
        const count = missions.filter((mission) => mission.category === category).length;
        return `<a class="pillar-card" href="/?pillar=${encodeURIComponent(category)}">
          <span class="category-icon">${CATEGORY_ICONS[category]}</span>
          <span class="pillar-card-copy"><strong>${category}</strong><small>${escapeHTML(CATEGORY_DESCRIPTIONS[category])}</small></span>
          <span class="pillar-card-meta">${count} goals <span class="mission-arrow" aria-hidden="true">→</span></span>
        </a>`;
      }).join("");
    }
  } catch (caught) {
    showError(error, caught);
  }
}

function renderPlanContent(container, plan) {
  const content = plan.content;
  const steps = content.steps.map((step, index) => `
    <article class="action-step"><div class="step-topline"><span class="step-number">${index + 1}</span><div><h3>${escapeHTML(step.title)}</h3><p>${escapeHTML(step.details)}</p></div></div></article>
  `).join("");
  const tips = content.practical_tips.map((tip) => `<li>${escapeHTML(tip)}</li>`).join("");
  const verification = content.verify_before_you_go.map((item) => `<li>${escapeHTML(item)}</li>`).join("");
  const resources = content.resources.map((resource) =>
    `<a class="resource-link" href="${escapeHTML(resource.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(resource.title)} ↗</a>`
  ).join("");
  container.innerHTML = `
    <article class="plan-card">
      <p class="eyebrow">Your goal</p><h2>${escapeHTML(content.goal)}</h2>
      <p class="plan-overview">${escapeHTML(content.overview)}</p>
      <h3>Step by step</h3><div class="steps-list">${steps}</div>
      <div class="guidance-card">
        <h3>Practical tips</h3><ul>${tips}</ul>
        ${resources ? `<h3>Official resources</h3><div class="resources">${resources}</div>` : ""}
        <h3>Remember to verify</h3><ul>${verification}</ul>
      </div>
      <p class="muted" style="margin:14px 0 0">Schedules, hours, prices, eligibility, and service availability can change. Confirm details with the official source before you go.</p>
    </article>`;
}

async function initializeCreate() {
  const params = new URLSearchParams(location.search);
  const select = document.querySelector("#mission-select");
  const planBackLink = document.querySelector("#plan-back-link");
  const customGoalField = document.querySelector("#custom-goal-field");
  const customGoalInput = document.querySelector("#custom-goal");
  const specificFields = document.querySelector("#mission-specific-fields");
  const form = document.querySelector("#plan-form");
  const error = document.querySelector("#plan-error");
  const generated = document.querySelector("#generated-plan");
  const planContent = document.querySelector("#plan-content");
  const generateButton = document.querySelector("#generate-button");
  const modifyButton = document.querySelector("#modify-button");
  const saveButton = document.querySelector("#save-button");
  let draft = null;
  let missions = [];
  let visibleMissions = [];

  try {
    missions = await api("/api/missions");
    const selected = params.get("mission");
    const requestedPillar = params.get("pillar");
    const selectedMission = missions.find((mission) => mission.id === selected);
    const pillar = ["Navigate", "Settle", "Explore", "Connect"].includes(requestedPillar)
      ? requestedPillar
      : selectedMission?.category;
    visibleMissions = pillar ? missions.filter((mission) => mission.category === pillar) : missions;
    planBackLink.href = pillar ? `/?pillar=${encodeURIComponent(pillar)}` : "/";
    planBackLink.textContent = pillar ? `← Back to ${pillar}` : "← Back to goals";
    select.innerHTML = `<option value="">Choose a preset goal</option>${visibleMissions.map((mission) =>
      `<option value="${escapeHTML(mission.id)}">${escapeHTML(mission.title)}</option>`
    ).join("")}<option value="custom">Write my own goal…</option>`;
    if (selected === "custom" || visibleMissions.some((mission) => mission.id === selected)) {
      select.value = selected;
    }
    renderMissionFields();
  } catch (caught) {
    showError(error, caught);
    generateButton.disabled = true;
    return;
  }

  function renderMissionFields() {
    const isCustom = select.value === "custom";
    customGoalField.hidden = !isCustom;
    customGoalInput.required = isCustom;
    const mission = missions.find((item) => item.id === select.value);
    specificFields.innerHTML = (mission?.preference_fields || []).map((field) => `
      <label class="field">
        <span>${escapeHTML(field.label)} <small>Optional</small></span>
        <input name="${escapeHTML(field.id)}" placeholder="${escapeHTML(field.placeholder)}" maxlength="300">
      </label>
    `).join("");
  }

  select.addEventListener("change", () => {
    renderMissionFields();
  });

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    error.hidden = true;
    if (!await requireSignedIn(error)) return;
    generateButton.disabled = true;
    generateButton.textContent = "Creating your plan…";
    const formData = new FormData(form);
    const preferences = Object.fromEntries(
      [...formData.entries()]
        .filter(([key]) => key !== "custom_goal")
        .map(([key, value]) => [key, String(value).trim()])
    );
    try {
      draft = await api("/api/plans/generate", {
        method: "POST",
        body: JSON.stringify({
          mission_id: select.value,
          custom_goal: select.value === "custom" ? customGoalInput.value.trim() : null,
          preferences,
        }),
      });
      renderPlanContent(planContent, draft);
      generated.hidden = false;
      generated.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (caught) {
      showError(error, caught);
    } finally {
      generateButton.disabled = false;
      generateButton.innerHTML = 'Generate My Plan <span aria-hidden="true">→</span>';
    }
  });

  modifyButton.addEventListener("click", async () => {
    const request = document.querySelector("#modify-request").value.trim();
    if (!draft || !request) {
      showError(error, new Error("Enter how you would like to change the plan."));
      error.hidden = false;
      return;
    }
    error.hidden = true;
    if (!await requireSignedIn(error)) return;
    modifyButton.disabled = true;
    modifyButton.textContent = "Updating your plan…";
    try {
      draft = await api("/api/plans/modify", {
        method: "POST",
        body: JSON.stringify({ plan: draft, request }),
      });
      renderPlanContent(planContent, draft);
      document.querySelector("#modify-request").value = "";
    } catch (caught) {
      showError(error, caught);
    } finally {
      modifyButton.disabled = false;
      modifyButton.textContent = "Update my plan";
    }
  });

  saveButton.addEventListener("click", async () => {
    if (!draft) return;
    error.hidden = true;
    if (!await requireSignedIn(error)) return;
    saveButton.disabled = true;
    saveButton.textContent = "Saving…";
    try {
      const saved = await api("/api/plans", { method: "POST", body: JSON.stringify(draft) });
      location.href = `/my_plan.html?plan_id=${encodeURIComponent(saved.id)}`;
    } catch (caught) {
      showError(error, caught);
      saveButton.disabled = false;
      saveButton.innerHTML = 'Save &amp; continue <span aria-hidden="true">→</span>';
    }
  });
}

function renderSavedPlan(plan) {
  document.querySelector("#saved-title").textContent = plan.mission_title;
  document.querySelector("#saved-overview").textContent = plan.content.overview;
  const stepsContainer = document.querySelector("#saved-steps");
  stepsContainer.innerHTML = plan.content.steps.map((step, index) => `
    <article class="action-step saved-step ${step.completed ? "is-complete" : ""}">
      <input type="checkbox" aria-label="Mark ${escapeHTML(step.title)} complete" data-step="${index}" ${step.completed ? "checked" : ""}>
      <div><h3>${escapeHTML(step.title)}</h3><p>${escapeHTML(step.details)}</p></div>
    </article>`).join("");

  const tips = plan.content.practical_tips.map((tip) => `<li>${escapeHTML(tip)}</li>`).join("");
  const verification = plan.content.verify_before_you_go.map((item) => `<li>${escapeHTML(item)}</li>`).join("");
  const resources = plan.content.resources.map((resource) =>
    `<a class="resource-link" href="${escapeHTML(resource.url)}" target="_blank" rel="noopener noreferrer">${escapeHTML(resource.title)} ↗</a>`
  ).join("");
  document.querySelector("#saved-guidance").innerHTML = `
    <div class="guidance-card"><h3>Practical tips</h3><ul>${tips}</ul>
    ${resources ? `<h3>Official resources</h3><div class="resources">${resources}</div>` : ""}
    <h3>Remember to verify</h3><ul>${verification}</ul>
    <p class="muted" style="margin:14px 0 0">Schedules, hours, prices, eligibility, and service availability can change. Confirm details with the official source before you go.</p></div>`;

  const completed = plan.content.steps.filter((step) => step.completed).length;
  const percent = plan.content.steps.length ? Math.round((completed / plan.content.steps.length) * 100) : 0;
  document.querySelector("#progress-label").textContent = `${completed} of ${plan.content.steps.length} steps complete`;
  document.querySelector("#progress-percent").textContent = `${percent}%`;
  document.querySelector("#progress-bar").style.width = `${percent}%`;
  const completePanel = document.querySelector(".complete-panel");
  completePanel.classList.toggle("is-complete", plan.mission_completed);
  const completeButton = document.querySelector("#complete-button");
  completeButton.textContent = plan.mission_completed ? "Mission complete ✓" : "Mark mission complete";
  document.querySelector("#saved-plan").hidden = false;
  document.querySelector("#saved-loading").hidden = true;
}

function renderSavedPlanList(plans) {
  const container = document.querySelector("#saved-plan-list");
  if (!plans.length) {
    container.innerHTML = `<div class="empty-plans panel">
      <span class="empty-plans-icon" aria-hidden="true">✦</span>
      <h2>Your plans will show up here</h2>
      <p class="muted">Generate a plan for a goal you have, then save it to keep it with your account.</p>
      <a class="button button-secondary" href="/">Explore goals</a>
    </div>`;
  } else {
    container.innerHTML = plans.map((plan) => {
      const stepCount = plan.content.steps.length;
      const completedSteps = plan.content.steps.filter((step) => step.completed).length;
      const progress = stepCount ? Math.round((completedSteps / stepCount) * 100) : 0;
      const status = plan.mission_completed ? "Mission complete" : `${completedSteps} of ${stepCount} steps complete`;
      return `<a class="saved-plan-card" href="/my_plan.html?plan_id=${encodeURIComponent(plan.id)}">
        <span class="saved-plan-icon" aria-hidden="true">${CATEGORY_ICONS[plan.category] || "✦"}</span>
        <span class="saved-plan-copy">
          <strong>${escapeHTML(plan.mission_title)}</strong>
          <small>${escapeHTML(status)}</small>
          <span class="progress-track"><span style="width:${progress}%"></span></span>
        </span>
        <span class="mission-arrow" aria-hidden="true">→</span>
      </a>`;
    }).join("");
  }
  document.querySelector("#plan-list-view").hidden = false;
  document.querySelector("#saved-loading").hidden = true;
}

async function initializeSavedPlan() {
  const params = new URLSearchParams(location.search);
  const planId = params.get("plan_id");
  const loading = document.querySelector("#saved-loading");
  const error = document.querySelector("#saved-error");
  const backLink = document.querySelector("#my-plan-back");
  if (!await requireSignedIn(error)) {
    loading.hidden = true;
    return;
  }
  if (!planId) {
    backLink.href = "/";
    try {
      const plans = await api("/api/plans");
      renderSavedPlanList(plans);
    } catch (caught) {
      loading.hidden = true;
      showError(error, caught);
    }
    return;
  }
  backLink.href = "/my_plan.html";
  backLink.textContent = "← All my plans";
  let plan;
  try {
    plan = await api(`/api/plans/${encodeURIComponent(planId)}`);
    renderSavedPlan(plan);
  } catch (caught) {
    loading.hidden = true;
    showError(error, caught);
    return;
  }

  document.querySelector("#saved-steps").addEventListener("change", async (event) => {
    const checkbox = event.target.closest("input[data-step]");
    if (!checkbox) return;
    checkbox.disabled = true;
    error.hidden = true;
    try {
      plan = await api(`/api/plans/${encodeURIComponent(plan.id)}/steps/${checkbox.dataset.step}`, {
        method: "PATCH",
        body: JSON.stringify({ completed: checkbox.checked }),
      });
      renderSavedPlan(plan);
    } catch (caught) {
      checkbox.checked = !checkbox.checked;
      checkbox.disabled = false;
      showError(error, caught);
    }
  });

  document.querySelector("#complete-button").addEventListener("click", async (event) => {
    const button = event.currentTarget;
    button.disabled = true;
    error.hidden = true;
    try {
      plan = await api(`/api/plans/${encodeURIComponent(plan.id)}/complete`, {
        method: "PATCH",
        body: JSON.stringify({ completed: !plan.mission_completed }),
      });
      renderSavedPlan(plan);
    } catch (caught) {
      showError(error, caught);
    } finally {
      button.disabled = false;
    }
  });
}

const page = document.body.dataset.page;
if (page === "auth") initializeAuthPage();
if (page === "home") initializeHome();
if (page === "create") initializeCreate();
if (page === "saved") initializeSavedPlan();

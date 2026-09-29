(() => {
  const csrf = () => document.cookie.split(";").map((part) => part.trim()).find((part) => part.startsWith("csrftoken="))?.split("=").slice(1).join("=") || "";
  const escapeHtml = (value) => String(value ?? "").replace(/[&<>"']/g, (char) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[char]);
  const toast = (message, isError = false) => {
    const node = document.querySelector(".toast");
    if (!node) return;
    node.textContent = message;
    node.classList.toggle("is-error", isError);
    node.classList.add("is-visible");
    window.clearTimeout(toast.timer);
    toast.timer = window.setTimeout(() => node.classList.remove("is-visible"), 3600);
  };
  const api = async (url, options = {}) => {
    const headers = { ...(options.body ? { "Content-Type": "application/json" } : {}), ...(options.method && options.method !== "GET" ? { "X-CSRFToken": csrf() } : {}), ...options.headers };
    const response = await fetch(url, { credentials: "same-origin", ...options, headers });
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || data.detail || "Something went wrong. Please try again.");
    return data;
  };
  const setLoading = (button, loading, label) => {
    if (!button) return;
    if (loading) {
      button.dataset.originalText = button.textContent;
      button.disabled = true;
      button.textContent = label;
    } else {
      button.disabled = false;
      if (button.dataset.originalText) button.textContent = button.dataset.originalText;
    }
  };
  const macrosMarkup = (nutrition) => {
    if (!nutrition) return "";
    const items = [["Protein", nutrition.protein_g, "g"], ["Carbs", nutrition.carbs_g, "g"], ["Fats", nutrition.fats_g, "g"]];
    const total = items.reduce((sum, item) => sum + (Number(item[1]) || 0), 0) || 1;
    return items.map(([label, value, unit]) => `<div class="macro-line"><span>${label}</span><span class="macro-track"><i style="width:${Math.max(5, Math.min(100, (Number(value) || 0) / total * 100))}%"></i></span><b>${escapeHtml(value ?? "—")}${unit}</b></div>`).join("");
  };
  const dayMarkup = (day, index) => {
    const dayName = escapeHtml(day.day || `Day ${index + 1}`);
    const focus = escapeHtml(day.focus || "Workout");
    const exercises = Array.isArray(day.exercises) ? day.exercises : [];
    const recovery = day.recovery ? `<p class="recovery-copy">${escapeHtml(day.recovery)}</p>` : "";
    const rows = exercises.map((exercise) => `<tr><td>${escapeHtml(exercise.name || "Movement")}${exercise.beginner_alternative ? `<br><span class="exercise-alt">Easier option: ${escapeHtml(exercise.beginner_alternative)}</span>` : ""}</td><td>${escapeHtml(exercise.sets ?? "—")}</td><td>${escapeHtml(exercise.repetitions ?? exercise.duration_minutes ?? "—")}</td><td>${escapeHtml(exercise.rest_seconds ?? "—")}${exercise.rest_seconds ? " sec" : ""}</td></tr>`).join("");
    return `<article class="workout-card"><header class="workout-card-head"><span class="workout-day-number">${String(index + 1).padStart(2, "0")}</span><div><h2>${dayName}</h2><p>${focus}</p></div><span class="workout-duration">${escapeHtml(day.duration_minutes || "—")} min</span></header>${rows ? `<div class="exercise-table-wrap"><table class="exercise-table"><thead><tr><th>Exercise</th><th>Sets</th><th>Reps / time</th><th>Rest</th></tr></thead><tbody>${rows}</tbody></table></div>` : ""}${recovery}</article>`;
  };
  const showPlanError = (error) => {
    const target = document.querySelector("[data-plan-content]") || document.querySelector(".content-section");
    if (!target) return;
    target.innerHTML = `<div class="panel empty-state"><h2>Your plan is waiting</h2><p>${escapeHtml(error.message)}</p><a class="button button-dark" href="/profile/">Create my plan ↗</a></div>`;
  };
  const renderPlan = (plan) => {
    const summary = plan.summary || {};
    const nutrition = plan.nutrition_guidance || {};
    const days = Array.isArray(plan.weekly_workout_plan) ? plan.weekly_workout_plan : [];
    document.querySelectorAll("[data-summary-goal]").forEach((node) => { node.textContent = summary.goal || "Personalized for you"; });
    document.querySelectorAll("[data-summary-days]").forEach((node) => { node.textContent = summary.weekly_workouts ?? days.length ?? "—"; });
    document.querySelectorAll("[data-summary-minutes]").forEach((node) => { node.textContent = summary.session_minutes ?? "—"; });
    document.querySelectorAll("[data-calories]").forEach((node) => { node.textContent = Number(nutrition.daily_calories).toLocaleString() || "—"; });
    document.querySelectorAll("[data-macros]").forEach((node) => { node.innerHTML = macrosMarkup(nutrition); });
    document.querySelectorAll("[data-motivation]").forEach((node) => { node.textContent = plan.motivation || "Consistency grows one comfortable step at a time."; });
    const headline = document.querySelector("[data-plan-headline]");
    if (headline) headline.textContent = summary.headline || "Your plan is ready when you are.";
    const preview = document.querySelector("[data-workout-preview]");
    if (preview) preview.innerHTML = days.length ? days.slice(0, 5).map((day, index) => `<div class="preview-day"><strong>${escapeHtml(day.day || `Day ${index + 1}`)}</strong><span>${escapeHtml(day.focus || "Workout")}</span><em>${escapeHtml(day.duration_minutes || summary.session_minutes || "—")} min</em></div>`).join("") : `<p class="empty-state">No sessions yet. Update your profile to create your weekly plan.</p>`;
    const workoutDays = document.querySelector("[data-workout-days]");
    if (workoutDays) workoutDays.innerHTML = days.map(dayMarkup).join("") || `<div class="panel empty-state">Your weekly schedule will appear here.</div>`;
    const scheduleMeta = document.querySelector("[data-schedule-meta]");
    if (scheduleMeta) scheduleMeta.textContent = `${days.length} sessions · ${summary.fitness_level || "Personalized"} level`;
    const safety = document.querySelector("[data-safety]");
    if (safety) safety.innerHTML = (plan.safety_notes || []).map((note) => `<li>${escapeHtml(note)}</li>`).join("");
    const mealList = document.querySelector("[data-meals]");
    if (mealList) mealList.innerHTML = (plan.daily_meal_ideas || []).map((meal) => `<article class="meal-card"><span class="meal-type">${escapeHtml(meal.meal_type || "Meal")}</span><h3>${escapeHtml(meal.name || "Flexible meal idea")}</h3><ul>${(meal.foods || []).map((food) => `<li>${escapeHtml(food)}</li>`).join("")}</ul><p>${escapeHtml(meal.notes || "")}</p></article>`).join("") || `<div class="panel empty-state">Meal ideas will appear with your plan.</div>`;
    const nutritionNote = document.querySelector("[data-nutrition-note]");
    if (nutritionNote) nutritionNote.textContent = nutrition.notes || "Approximate guidance only. Your needs vary day to day.";
    const hydration = document.querySelector("[data-hydration]");
    if (hydration) hydration.textContent = `Your profile lists ${nutrition.hydration_liters || "—"} L/day. Keep water nearby and sip through the day; individual needs vary.`;
    const waterMeter = document.querySelector("[data-water-meter]");
    if (waterMeter) waterMeter.style.width = `${Math.max(12, Math.min(100, Number(nutrition.hydration_liters || 2) / 4 * 100))}%`;
    const sleep = document.querySelector("[data-sleep-tips]");
    if (sleep) sleep.innerHTML = (plan.hydration_and_sleep_tips || []).map((tip) => `<li>${escapeHtml(tip)}</li>`).join("");
    const miniWeek = document.querySelector("[data-mini-week]");
    if (miniWeek) miniWeek.innerHTML = days.slice(0, 5).map((day, index) => `<div class="mini-day"><span>${escapeHtml((day.day || `Day ${index + 1}`).slice(0, 3))}</span><i></i></div>`).join("") || `<div class="empty-state">Your week will appear here.</div>`;
    const dashboardGoal = document.querySelector("[data-dashboard-goal]");
    if (dashboardGoal) dashboardGoal.textContent = summary.goal || "Make a plan to begin";
    const dashboardSummary = document.querySelector("[data-dashboard-summary]");
    if (dashboardSummary) dashboardSummary.textContent = summary.headline || "Your personalized weekly rhythm is ready.";
    const dashboardDays = document.querySelector("[data-dashboard-days]");
    if (dashboardDays) dashboardDays.textContent = summary.weekly_workouts ?? days.length ?? "—";
    const dashboardCalories = document.querySelector("[data-dashboard-calories]");
    if (dashboardCalories) dashboardCalories.textContent = Number(nutrition.daily_calories).toLocaleString() || "—";
    const dashboardMacros = document.querySelector("[data-dashboard-macros]");
    if (dashboardMacros) dashboardMacros.innerHTML = macrosMarkup(nutrition);
  };
  const loadPlan = async () => {
    try { const plan = await api("/api/plan/"); renderPlan(plan); return plan; }
    catch (error) { showPlanError(error); return null; }
  };
  const loadTips = async () => {
    const target = document.querySelector("[data-tips]");
    if (!target) return;
    target.innerHTML = `<p class="loading-state">Gathering your daily tips…</p>`;
    try {
      const data = await api("/api/tips/");
      target.innerHTML = (data.tips || []).map((tip, index) => `<article class="tip-card" style="animation-delay:${index * 60}ms"><span class="tip-number">0${index + 1}</span><span class="eyebrow">${escapeHtml(tip.category || "WELLNESS")}</span><p>${escapeHtml(tip.content)}</p></article>`).join("");
      const motivation = data.tips?.find((tip) => tip.category === "motivation");
      if (motivation) document.querySelector("[data-tip-motivation]").textContent = motivation.content;
    } catch (error) { target.innerHTML = `<div class="panel empty-state">${escapeHtml(error.message)} <a class="text-link" href="/profile/">Set up your profile ↗</a></div>`; }
  };
  const loadDashboard = async () => {
    const plan = await loadPlan();
    try {
      const progress = await api("/api/progress/");
      const checkins = document.querySelector("[data-dashboard-checkins]");
      if (checkins) checkins.textContent = progress.entries.length;
      const history = document.querySelector("[data-progress-history]");
      if (history) history.innerHTML = progress.entries.slice(0, 4).map((entry) => `<div class="history-line"><span>${escapeHtml(entry.recorded_at.slice(0, 10))}${entry.note ? ` · ${escapeHtml(entry.note)}` : ""}</span><span>${entry.weight_kg ? `${escapeHtml(entry.weight_kg)} kg` : `${escapeHtml(entry.activity_minutes || 0)} min`}</span></div>`).join("") || "No progress logged yet.";
      const recent = document.querySelector("[data-recent-feedback]");
      if (recent && progress.feedback.length) recent.innerHTML = progress.feedback.slice(0, 2).map((item) => `<div class="feedback-preview"><strong>${"★".repeat(item.rating)} · ${escapeHtml(item.difficulty)} week</strong><p>${escapeHtml(item.comments || `${item.adherence}% of planned sessions completed.`)}</p></div>`).join("");
    } catch { /* Dashboard plan state remains useful without progress history. */ }
    if (!plan) return;
  };
  const submitForm = async (form) => {
    const kind = form.dataset.form;
    const button = form.querySelector("button[type='submit']");
    const errorTarget = form.querySelector("[data-form-error]");
    if (errorTarget) errorTarget.textContent = "";
    setLoading(button, true, kind === "profile" || kind === "feedback" ? "Building your plan…" : "Working…");
    try {
      const formData = new FormData(form);
      const data = Object.fromEntries(formData.entries());
      let endpoint = "";
      if (kind === "profile") endpoint = "/api/profile/";
      if (kind === "feedback") endpoint = "/api/feedback/";
      if (kind === "progress") endpoint = "/api/progress/";
      if (kind === "login") endpoint = "/api/auth/login/";
      if (kind === "register") endpoint = "/api/auth/register/";
      const result = await api(endpoint, { method: "POST", body: JSON.stringify(data) });
      if (kind === "profile" || kind === "feedback") {
        toast(kind === "profile" ? "Your plan is ready." : "Your updated plan is ready.");
        window.location.href = "/result/";
      } else if (kind === "progress") {
        form.reset(); toast("Progress saved."); window.location.reload();
      } else if (kind === "login" || kind === "register") {
        const next = new URLSearchParams(window.location.search).get("next");
        window.location.href = next?.startsWith("/") ? next : (kind === "register" ? "/profile/" : "/dashboard/");
      }
      return result;
    } catch (error) {
      if (errorTarget) errorTarget.textContent = error.message;
      else toast(error.message, true);
    } finally { setLoading(button, false); }
  };
  const init = async () => {
    const navToggle = document.querySelector(".nav-toggle");
    navToggle?.addEventListener("click", () => {
      const nav = document.querySelector(".main-nav");
      const open = nav.classList.toggle("is-open");
      navToggle.setAttribute("aria-expanded", String(open));
    });
    document.querySelectorAll("[data-form]").forEach((form) => form.addEventListener("submit", (event) => { event.preventDefault(); submitForm(form); }));
    document.querySelectorAll("input[type='range']").forEach((input) => input.addEventListener("input", () => {
      const output = document.querySelector(`[data-range-output="${input.name}"]`);
      if (output) output.textContent = input.name === "rating" ? `${input.value} / 5` : `${input.value}%`;
    }));
    const stamp = document.querySelector("[data-date-stamp]");
    if (stamp) stamp.textContent = new Intl.DateTimeFormat(undefined, { weekday: "long", month: "short", day: "numeric" }).format(new Date());
    const me = await api("/api/me/").catch(() => ({ authenticated: false }));
    document.querySelectorAll("[data-auth-link]").forEach((node) => { node.hidden = !me.authenticated; });
    document.querySelectorAll("[data-guest-link]").forEach((node) => { node.hidden = me.authenticated; });
    document.querySelectorAll("[data-logout]").forEach((node) => { node.hidden = !me.authenticated; node.addEventListener("click", async () => { try { await api("/api/auth/logout/", { method: "POST", body: "{}" }); window.location.href = "/"; } catch (error) { toast(error.message, true); } }); });
    document.querySelectorAll("[data-admin-link]").forEach((node) => { node.hidden = !me.is_staff; });
    document.querySelectorAll("[data-plan-link]").forEach((node) => { if (me.authenticated) { node.href = me.has_profile ? "/dashboard/" : "/profile/"; node.innerHTML = `${me.has_profile ? "My dashboard" : "Create my plan"} <span aria-hidden="true">↗</span>`; } });
    const greeting = document.querySelector("[data-greeting]");
    if (greeting && me.authenticated) greeting.textContent = (me.name || me.email.split("@")[0]).split(" ")[0] + ".";
    if (["result", "plan", "nutrition"].includes(document.body.dataset.page)) await loadPlan();
    if (document.body.dataset.page === "dashboard") await loadDashboard();
    if (document.body.dataset.page === "tips") await loadTips();
    if (document.body.dataset.page === "admin" && me.is_staff) {
      try {
        const stats = await api("/api/admin/stats/");
        document.querySelector("[data-admin-stats]").innerHTML = [["Users", stats.users], ["Plans", stats.plans], ["Feedback", stats.feedback], ["Tips", stats.tips]].map(([label, count]) => `<div class="admin-stat"><strong>${escapeHtml(count)}</strong><span>${label}</span></div>`).join("");
        const feedback = document.querySelector("[data-admin-feedback]");
        feedback.innerHTML = stats.recent_feedback.map((item) => `<div class="admin-feedback-row"><strong>${escapeHtml(item.user__username)}</strong><span>${escapeHtml(item.rating)} / 5 · ${escapeHtml(item.difficulty)}</span></div>`).join("") || `<p class="empty-state">No check-ins yet.</p>`;
      } catch (error) { toast(error.message, true); }
    }
  };
  document.addEventListener("DOMContentLoaded", init);
  window.FitBuddy = { api, toast };
})();
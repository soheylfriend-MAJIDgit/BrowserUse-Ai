/* Browser Use AI Studio — Frontend Controller (Works in PyWebView Desktop & Web Mode) */

const state = {
  providers: [],
  profiles: [],
  activeProfileId: null,
  fallbackProfileId: null,
  selectedProviderId: 'routeway',
  editingProfileId: null,
  settings: {},
  templates: [],
  systemHealth: null,
  agentPollTimer: null,
  codePollTimer: null,
  installPollTimer: null,
};

// ---------------- Helpers ----------------

function $(id) {
  return document.getElementById(id);
}

function escapeHtml(str) {
  return String(str ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function showToast(msg, duration = 3800) {
  const container = $('toastContainer');
  const el = document.createElement('div');
  el.className = 'toast';
  el.textContent = msg;
  container.appendChild(el);
  setTimeout(() => {
    el.style.opacity = '0';
    setTimeout(() => el.remove(), 250);
  }, duration);
}

async function apiFetch(path, options = {}) {
  const opts = {
    headers: { 'Content-Type': 'application/json', ...(options.headers || {}) },
    ...options,
  };
  const res = await fetch(path, opts);
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    throw new Error(data.detail || data.error || `HTTP ${res.status}`);
  }
  return data;
}

function hasPyWebView() {
  return Boolean(window.pywebview && window.pywebview.api);
}

function openExternalLink(url, event) {
  if (!url) return;
  if (hasPyWebView() && window.pywebview.api.open_external_url) {
    if (event) event.preventDefault();
    window.pywebview.api.open_external_url(url);
  }
}

async function saveFileUniversal(content, filename) {
  if (hasPyWebView() && window.pywebview.api.save_text_file) {
    const savedPath = await window.pywebview.api.save_text_file(content, filename);
    if (savedPath) {
      showToast(`💾 فایل با موفقیت ذخیره شد: ${savedPath}`);
    }
    return;
  }
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  showToast(`💾 فایل ${filename} دانلود شد.`);
}

// ---------------- Navigation & Theme ----------------

function switchTab(tabName) {
  document.querySelectorAll('.nav-tab').forEach((btn) => {
    btn.classList.toggle('active', btn.dataset.tab === tabName);
  });
  document.querySelectorAll('.tab-panel').forEach((panel) => {
    panel.classList.toggle('active', panel.id === `tab-${tabName}`);
  });
  if (tabName === 'python') {
    regeneratePythonCode(false);
  } else if (tabName === 'history') {
    refreshHistory();
  }
}

window.switchTab = switchTab;

function initTheme() {
  const saved = localStorage.getItem('bu_studio_theme') || 'dark';
  document.documentElement.setAttribute('data-theme', saved);
  $('btnToggleTheme').addEventListener('click', () => {
    const cur = document.documentElement.getAttribute('data-theme') || 'dark';
    const next = cur === 'dark' ? 'light' : 'dark';
    document.documentElement.setAttribute('data-theme', next);
    localStorage.setItem('bu_studio_theme', next);
  });
}

// ---------------- System Health & Topbar ----------------

function renderSystemHealth(health) {
  state.systemHealth = health;
  const dot = $('browserHealthDot');
  const txt = $('browserHealthText');

  if (health.browser_ready && health.browsers.length > 0) {
    dot.className = 'status-dot';
    txt.textContent = `مرورگر آماده: ${health.browsers[0].name}`;
  } else {
    dot.className = 'status-dot warn';
    txt.textContent = 'مرورگر نصب نشده (نصب از تنظیمات)';
  }

  if (health.chrome_profile_hint) {
    $('chromeProfileHintText').innerHTML =
      `⚠️ اگر می‌خواهید از لاگین‌های کروم خودتان استفاده کنید، ابتدا تمام پنجره‌های کروم را ببندید. مسیر پیش‌فرض سیستم شما: <code class="ltr">${escapeHtml(health.chrome_profile_hint)}</code>`;
  }

  const box = $('doctorDetailsBox');
  if (!box) return;

  const browsersHtml = health.browsers.length
    ? health.browsers
        .map(
          (b) =>
            `<div style="padding:8px 10px; border-radius:8px; background:var(--bg-surface-3); font-size:12.5px;">
              <strong>✅ ${escapeHtml(b.name)}</strong>
              <div class="ltr" style="color:var(--text-secondary); font-size:11.5px;">${escapeHtml(b.path)}</div>
            </div>`
        )
        .join('')
    : `<div style="padding:10px; border-radius:8px; background:var(--rose-soft); color:var(--rose); font-size:13px;">
        ⚠️ هیچ مرورگر کروم یا مایکروسافت اج در مسیرهای پیش‌فرض پیدا نشد. دکمه «نصب خودکار مرورگر Chromium» در پایین همین کارت را بزنید یا مسیر فایل اجرایی مرورگر را دستی انتخاب کنید.
      </div>`;

  box.innerHTML = `
    <div style="display:grid; grid-template-columns:1fr 1fr; gap:8px; font-size:13px;">
      <div style="padding:10px; border-radius:9px; background:var(--bg-surface-2);">🖥️ سیستم‌عامل: <strong class="ltr">${escapeHtml(health.os)} ${escapeHtml(health.os_release)}</strong></div>
      <div style="padding:10px; border-radius:9px; background:var(--bg-surface-2);">🐍 نسخه پایتون: <strong class="ltr">${escapeHtml(health.python_version)}</strong></div>
      <div style="padding:10px; border-radius:9px; background:var(--bg-surface-2);">🌐 هسته Browser Use: <strong class="ltr">v${escapeHtml(health.browser_use_version)}</strong></div>
      <div style="padding:10px; border-radius:9px; background:var(--bg-surface-2);">🪟 رابط PyWebView: <strong class="ltr">v${escapeHtml(health.pywebview_version)}</strong></div>
    </div>
    <div style="font-size:13px; font-weight:700; margin-top:6px;">مرورگرهای شناسایی‌شده روی سیستم شما (${health.browsers.length}):</div>
    ${browsersHtml}
  `;
}

// ---------------- Profiles & Multi-LLM Switcher ----------------

function updateProfilesState(profilesState) {
  state.profiles = profilesState.profiles || [];
  state.activeProfileId = profilesState.active_profile_id || null;
  state.fallbackProfileId = profilesState.fallback_profile_id || null;

  $('profilesCountBadge').textContent = String(state.profiles.length);
  $('onboardingBanner').style.display = state.profiles.length === 0 ? 'flex' : 'none';

  // Render Top Header Quick Switcher (grouped cleanly by provider when multiple providers exist!)
  const headerSel = $('headerProfileSelect');
  if (state.profiles.length === 0) {
    headerSel.innerHTML = `<option value="">⚠️ هنوز کلیدی ثبت نشده — کلیک کنید</option>`;
  } else {
    const groupsMap = new Map();
    state.profiles.forEach((p) => {
      const prov = state.providers.find((x) => x.id === p.provider);
      const groupTitle = prov ? prov.short_name : p.provider;
      if (!groupsMap.has(groupTitle)) groupsMap.set(groupTitle, []);
      groupsMap.get(groupTitle).push(p);
    });

    if (groupsMap.size > 1) {
      headerSel.innerHTML = Array.from(groupsMap.entries())
        .map(([gName, items]) => {
          const opts = items
            .map((p) => {
              const selected = p.id === state.activeProfileId ? 'selected' : '';
              return `<option value="${escapeHtml(p.id)}" ${selected}>${escapeHtml(p.name)} (${escapeHtml(p.model)})</option>`;
            })
            .join('');
          return `<optgroup label="── ${escapeHtml(gName)} ──">${opts}</optgroup>`;
        })
        .join('');
    } else {
      headerSel.innerHTML = state.profiles
        .map((p) => {
          const prov = state.providers.find((x) => x.id === p.provider);
          const pShort = prov ? prov.short_name : p.provider;
          const selected = p.id === state.activeProfileId ? 'selected' : '';
          return `<option value="${escapeHtml(p.id)}" ${selected}>${escapeHtml(p.name)} (${escapeHtml(pShort)} • ${escapeHtml(p.model)})</option>`;
        })
        .join('');
    }
  }

  // Render Fallback Select
  const fbSel = $('fallbackProfileSelect');
  const otherProfiles = state.profiles.filter((p) => p.id !== state.activeProfileId);
  fbSel.innerHTML =
    `<option value="">بدون مدل پشتیبان (فقط مدل فعال)</option>` +
    otherProfiles
      .map(
        (p) =>
          `<option value="${escapeHtml(p.id)}" ${p.id === state.fallbackProfileId ? 'selected' : ''}>🛡️ ${escapeHtml(p.name)} (${escapeHtml(p.model)})</option>`
      )
      .join('');

  renderSavedProfilesList();
}

function renderSavedProfilesList() {
  const container = $('profilesListContainer');
  if (state.profiles.length === 0) {
    container.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🔑</div>
        <div><strong>هنوز هیچ کلید یا مدلی ذخیره نکرده‌اید</strong></div>
        <p style="font-size:13px; margin-top:4px;">از فرم سمت چپ یکی از سرویس‌ها (مثلاً Google Gemini رایگان، Groq برای Llama، OpenRouter یا Ollama لوکال) را انتخاب و ذخیره کنید.</p>
      </div>
    `;
    return;
  }

  container.innerHTML = state.profiles
    .map((p) => {
      const isActive = p.id === state.activeProfileId;
      const isFallback = p.id === state.fallbackProfileId;
      const prov = state.providers.find((x) => x.id === p.provider);
      const provLabel = prov ? prov.short_name : p.provider;

      let testBadge = `<span class="badge" style="background:var(--bg-surface-3); color:var(--text-secondary);">تست نشده</span>`;
      if (p.last_test_ok === true) {
        testBadge = `<span class="badge badge-emerald">✅ کلید سالم</span>`;
      } else if (p.last_test_ok === false) {
        testBadge = `<span class="badge badge-rose">❌ خطا در آخرین تست</span>`;
      }

      return `
        <div class="profile-card ${isActive ? 'active-profile' : ''}">
          <div style="display:flex; justify-content:space-between; align-items:flex-start; gap:8px; flex-wrap:wrap;">
            <div>
              <div style="font-size:15px; font-weight:700; display:flex; align-items:center; gap:7px; flex-wrap:wrap;">
                <span>${escapeHtml(p.name)}</span>
                ${isActive ? '<span class="badge badge-amber">⭐ مدل فعال فعلی</span>' : ''}
                ${isFallback ? '<span class="badge badge-cyan">🛡️ پشتیبان</span>' : ''}
                ${p.free_only ? '<span class="badge badge-emerald">🔒 فقط رایگان (:free)</span>' : ''}
                ${p.vision_enabled ? '<span class="badge badge-violet">📸 Vision</span>' : '<span class="badge" style="background:var(--bg-surface-3); color:var(--text-secondary);">📄 متنی</span>'}
              </div>
              <div style="font-size:12.5px; color:var(--text-secondary); margin-top:4px;">
                سرویس: <strong>${escapeHtml(provLabel)}</strong> • مدل: <code class="ltr">${escapeHtml(p.model)}</code> • کلید: <code class="ltr">${escapeHtml(p.masked_key)}</code>
              </div>
            </div>
            ${testBadge}
          </div>

          ${p.last_test_msg ? `<div style="font-size:12px; color:var(--text-secondary); margin-top:8px;">${escapeHtml(p.last_test_msg)}</div>` : ''}

          <div style="display:flex; gap:7px; margin-top:12px; flex-wrap:wrap;">
            ${
              !isActive
                ? `<button class="btn btn-sm btn-primary" onclick="activateProfile('${escapeHtml(p.id)}')">⚡ انتخاب به عنوان مدل فعال</button>`
                : `<button class="btn btn-sm btn-success" disabled>✓ در حال حاضر فعال است</button>`
            }
            <button class="btn btn-sm" onclick="testSavedProfile('${escapeHtml(p.id)}', this)">🧪 تست اتصال</button>
            <button class="btn btn-sm" onclick="editProfile('${escapeHtml(p.id)}')">✏️ ویرایش</button>
            <button class="btn btn-sm btn-danger" onclick="removeProfile('${escapeHtml(p.id)}')">🗑️ حذف</button>
          </div>
        </div>
      `;
    })
    .join('');
}

function renderProviderCards() {
  const grid = $('providerCardsGrid');
  grid.innerHTML = state.providers
    .map((p) => {
      const sel = p.id === state.selectedProviderId ? 'selected' : '';
      return `
        <div class="provider-option ${sel}" onclick="selectProvider('${escapeHtml(p.id)}')">
          <div class="provider-option-title">${escapeHtml(p.short_name)}</div>
          <div class="provider-option-badge">${escapeHtml(p.badge)}</div>
        </div>
      `;
    })
    .join('');
  updateProviderFormDetails();
}

function selectProvider(providerId, preserveValues = false) {
  state.selectedProviderId = providerId;
  document.querySelectorAll('.provider-option').forEach((el, idx) => {
    const p = state.providers[idx];
    el.classList.toggle('selected', p && p.id === providerId);
  });
  updateProviderFormDetails(preserveValues);
}

window.selectProvider = selectProvider;

function updateProviderFormDetails(preserveValues = false) {
  const prov = state.providers.find((p) => p.id === state.selectedProviderId) || state.providers[0];
  if (!prov) return;

  $('providerGuideTitle').textContent = `ℹ️ راهنمای ${prov.name}`;
  $('providerSummaryText').textContent = prov.summary_fa || '';
  $('providerGuideSteps').textContent = prov.guide_fa || '';

  const keyLinkBtn = $('providerKeyLinkBtn');
  if (prov.key_url) {
    keyLinkBtn.style.display = 'inline-flex';
    keyLinkBtn.href = prov.key_url;
    keyLinkBtn.onclick = (e) => openExternalLink(prov.key_url, e);
  } else {
    keyLinkBtn.style.display = 'none';
  }

  // Models select
  const modelSel = $('profSuggestedModelSelect');
  modelSel.innerHTML = (prov.models || [])
    .map((m) => `<option value="${escapeHtml(m.id)}" data-vision="${m.vision}">${escapeHtml(m.label)}</option>`)
    .join('');

  if (!preserveValues) {
    $('profModelInput').value = prov.default_model || '';
    $('profBaseUrlInput').value = prov.default_base_url || '';
    $('profVisionChk').checked = Boolean(prov.vision_recommended);
    $('profFreeOnlyChk').checked = prov.id === 'routeway' || prov.id === 'openrouter';
    $('profCompatChk').checked = false;
  }

  $('profApiKeyInput').placeholder = prov.api_key_placeholder || 'کلید API...';
  $('apiKeyGroup').style.opacity = prov.requires_api_key ? '1' : '0.85';
  $('apiKeyFieldHelp').textContent = prov.requires_api_key
    ? 'کلیدها فقط به صورت محلی روی کامپیوتر خودتان ذخیره می‌شوند.'
    : 'این سرویس لوکال/سفارشی نیازی به کلید اجباری ندارد (در صورت نداشتن خالی بگذارید).';

  // Base URL & presets
  $('baseUrlGroup').style.display = prov.supports_base_url ? 'block' : 'none';
  const presetsRow = $('baseUrlPresetsRow');
  if (prov.presets && prov.presets.length) {
    presetsRow.style.display = 'flex';
    presetsRow.innerHTML =
      `<span style="font-size:11.5px; color:var(--text-muted);">انتخاب سریع آدرس:</span>` +
      prov.presets
        .map(
          (pr) =>
            `<button type="button" class="chip" onclick="applyPreset('${escapeHtml(pr.base_url)}', '${escapeHtml(pr.sample_model)}', '${escapeHtml(pr.label)}')">${escapeHtml(pr.label)}</button>`
        )
        .join('');
  } else {
    presetsRow.style.display = 'none';
  }

  $('btnScanRouteway').style.display = prov.id === 'routeway' ? 'inline-flex' : 'none';
  $('btnScanOpenRouter').style.display = prov.id === 'openrouter' ? 'inline-flex' : 'none';
  $('freeOnlyWrap').style.display = prov.id === 'routeway' || prov.id === 'openrouter' ? 'inline-flex' : 'none';
  $('routewayBulkBox').style.display = prov.id === 'routeway' && !state.editingProfileId ? 'block' : 'none';
  $('openrouterBulkBox').style.display = prov.id === 'openrouter' && !state.editingProfileId ? 'block' : 'none';
  $('btnScanOllama').style.display = prov.id === 'ollama' ? 'inline-flex' : 'none';
  $('compatModeWrap').style.display = prov.id === 'custom_openai' ? 'inline-flex' : 'none';
  $('testResultInline').style.display = 'none';
}

window.applyPreset = function (baseUrl, sampleModel, label) {
  $('profBaseUrlInput').value = baseUrl;
  if (sampleModel) $('profModelInput').value = sampleModel;
  if (!$('profNameInput').value.trim()) {
    $('profNameInput').value = label;
  }
  showToast(`آدرس ${label} جایگذاری شد.`);
};

window.activateProfile = async function (profileId) {
  try {
    const res = await apiFetch('/api/profiles/switch', {
      method: 'POST',
      body: JSON.stringify({ active_profile_id: profileId }),
    });
    updateProfilesState(res.profiles_state);
    const active = state.profiles.find((p) => p.id === profileId);
    showToast(`⚡ هوش مصنوعی فعال تغییر کرد به: ${active ? active.name : ''}`);
  } catch (err) {
    showToast(`خطا: ${err.message}`);
  }
};

window.testSavedProfile = async function (profileId, btnEl) {
  const origTxt = btnEl ? btnEl.textContent : '';
  if (btnEl) {
    btnEl.disabled = true;
    btnEl.textContent = '⏳ در حال تست...';
  }
  try {
    const res = await apiFetch('/api/profiles/test', {
      method: 'POST',
      body: JSON.stringify({ profile_id: profileId }),
    });
    updateProfilesState(res.profiles_state);
    showToast(res.message_fa, 5000);
  } catch (err) {
    showToast(`خطا در تست: ${err.message}`);
  } finally {
    if (btnEl) {
      btnEl.disabled = false;
      btnEl.textContent = origTxt;
    }
  }
};

window.editProfile = function (profileId) {
  const p = state.profiles.find((x) => x.id === profileId);
  if (!p) return;
  state.editingProfileId = p.id;
  $('profIdInput').value = p.id;
  $('profileFormTitle').textContent = `✏️ ویرایش پروفایل: ${p.name}`;
  selectProvider(p.provider, true);
  $('profNameInput').value = p.name || '';
  $('profModelInput').value = p.model || '';
  $('profApiKeyInput').value = '';
  $('profApiKeyInput').placeholder = p.has_api_key
    ? `${p.masked_key} (برای حفظ کلید قبلی خالی بگذارید)`
    : 'کلید جدید را وارد کنید...';
  $('profBaseUrlInput').value = p.base_url || '';
  $('profTempInput').value = p.temperature ?? 0.2;
  $('tempValLabel').textContent = String(p.temperature ?? 0.2);
  $('profVisionChk').checked = Boolean(p.vision_enabled);
  $('profFreeOnlyChk').checked = (p.provider === 'routeway' || p.provider === 'openrouter') ? Boolean(p.free_only ?? true) : false;
  $('profCompatChk').checked = Boolean(p.compat_schema_mode);
  $('routewayBulkBox').style.display = 'none';
  $('openrouterBulkBox').style.display = 'none';
  $('btnSaveProfile').textContent = '💾 ذخیره تغییرات پروفایل';
  showToast(`در حال ویرایش «${p.name}»`);
};

function resetProfileForm() {
  state.editingProfileId = null;
  $('profIdInput').value = '';
  $('profileFormTitle').textContent = '➕ افزودن کلید API یا مدل جدید';
  $('profNameInput').value = '';
  $('profApiKeyInput').value = '';
  $('profTempInput').value = 0.2;
  $('tempValLabel').textContent = '0.2';
  $('btnSaveProfile').textContent = '💾 ذخیره و فعال‌سازی این پروفایل';
  selectProvider(state.selectedProviderId || 'routeway', false);
}

window.removeProfile = async function (profileId) {
  const p = state.profiles.find((x) => x.id === profileId);
  if (!confirm(`آیا مطمئن هستید که پروفایل «${p ? p.name : ''}» حذف شود؟`)) return;
  try {
    const res = await apiFetch(`/api/profiles/${encodeURIComponent(profileId)}`, { method: 'DELETE' });
    updateProfilesState(res.profiles_state);
    if (state.editingProfileId === profileId) resetProfileForm();
    showToast('🗑️ پروفایل حذف شد.');
  } catch (err) {
    showToast(`خطا: ${err.message}`);
  }
};

// ---------------- Templates ----------------

function renderTemplates() {
  const grid = $('templatesGrid');
  grid.innerHTML = state.templates
    .map(
      (t) => `
      <div class="template-card">
        <div>
          <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:8px;">
            <span style="font-size:26px;">${t.icon}</span>
            <span class="badge badge-cyan">${escapeHtml(t.category)}</span>
          </div>
          <div style="font-size:15px; font-weight:700; margin-bottom:6px;">${escapeHtml(t.title)}</div>
          <p style="font-size:13px; color:var(--text-secondary); margin-bottom:10px;">${escapeHtml(t.description)}</p>
          <div style="font-size:12px; background:var(--bg-surface-2); padding:9px 11px; border-radius:8px; border:1px solid var(--border-color); color:var(--text-secondary);">
            «${escapeHtml(t.prompt)}»
          </div>
        </div>
        <button class="btn btn-primary" onclick="useTemplate('${escapeHtml(t.id)}')">🚀 انتقال به میز کار و استفاده</button>
      </div>
    `
    )
    .join('');
}

window.useTemplate = function (templateId) {
  const t = state.templates.find((x) => x.id === templateId);
  if (!t) return;
  $('taskInput').value = t.prompt;
  switchTab('workspace');
  $('taskInput').focus();
  showToast(`✨ دستور «${t.title}» در میز کار قرار گرفت!`);
};

// ---------------- Live Agent Runner ----------------

function renderAgentState(st) {
  const statusMap = {
    idle: { text: 'آماده به کار', dot: 'status-dot' },
    starting: { text: 'در حال راه‌اندازی مرورگر...', dot: 'status-dot pulse' },
    running: { text: `در حال کار (گام ${st.current_step} از ${st.max_steps})`, dot: 'status-dot pulse' },
    paused: { text: 'متوقف موقت (منتظر ادامه شما)', dot: 'status-dot warn' },
    stopping: { text: 'در حال توقف ایمن...', dot: 'status-dot warn' },
    completed: { text: 'تکمیل شد ✅', dot: 'status-dot' },
    error: { text: 'متوقف به دلیل خطا', dot: 'status-dot err' },
    stopped: { text: 'متوقف توسط کاربر', dot: 'status-dot warn' },
  };
  const info = statusMap[st.status] || statusMap.idle;
  $('runStatusDot').className = info.dot;
  $('runStatusText').textContent = info.text;

  const isBusy = ['starting', 'running', 'paused', 'stopping'].includes(st.status);
  $('btnStartAgent').style.display = isBusy ? 'none' : 'inline-flex';
  $('btnPauseAgent').style.display = st.status === 'running' ? 'inline-flex' : 'none';
  $('btnResumeAgent').style.display = st.status === 'paused' ? 'inline-flex' : 'none';
  $('btnStopAgent').style.display = isBusy ? 'inline-flex' : 'none';
  $('followupBar').style.display = ['running', 'paused'].includes(st.status) ? 'block' : 'none';

  if (st.profile_name) {
    $('agentMetaSubtitle').textContent = `مدل: ${st.profile_name} (${st.model_name}) • زمان سپری‌شده: ${st.elapsed_seconds} ثانیه`;
  }

  // URL & Live Screenshot
  $('liveUrlBar').textContent = st.current_url || 'about:blank';
  if (st.latest_screenshot) {
    const mime = st.latest_screenshot.startsWith('/9j/') ? 'image/jpeg' : 'image/png';
    const src = st.latest_screenshot.startsWith('data:')
      ? st.latest_screenshot
      : `data:${mime};base64,${st.latest_screenshot}`;
    $('liveScreenshotImg').src = src;
    $('liveScreenshotImg').style.display = 'block';
    $('liveEmptyState').style.display = 'none';
  }

  // Logs
  if (st.logs && st.logs.length) {
    const logsBox = $('liveLogsBox');
    logsBox.textContent = st.logs.join('\n');
    logsBox.scrollTop = logsBox.scrollHeight;
  }

  // Final Result or Error
  const resBox = $('finalResultBox');
  if (st.status === 'error' && st.error_message) {
    resBox.className = 'result-banner error';
    resBox.style.display = 'block';
    $('finalResultTitle').textContent = '⚠️ خطا در حین انجام عملیات:';
    $('finalResultText').textContent = st.error_message;
    $('btnDownloadGif').style.display = 'none';
  } else if (st.final_result && ['completed', 'stopped'].includes(st.status)) {
    resBox.className = 'result-banner';
    resBox.style.display = 'block';
    $('finalResultTitle').textContent = '✅ نتیجه نهایی تحویل‌شده توسط ربات:';
    $('finalResultText').textContent = st.final_result;
    if (st.gif_url) {
      $('btnDownloadGif').href = st.gif_url;
      $('btnDownloadGif').style.display = 'inline-flex';
    } else {
      $('btnDownloadGif').style.display = 'none';
    }
  } else if (isBusy) {
    resBox.style.display = 'none';
  }

  // Steps timeline (newest first so user always sees latest action immediately)
  if (st.steps && st.steps.length > 0) {
    const reversed = [...st.steps].reverse();
    $('stepsContainer').innerHTML = reversed
      .map(
        (s) => `
        <div class="step-card">
          <div class="step-header">
            <span class="step-badge">گام ${s.step}</span>
            <span class="ltr">${escapeHtml(s.time)} ${s.url ? '• ' + escapeHtml(s.url.slice(0, 55)) : ''}</span>
          </div>
          ${s.next_goal ? `<div class="step-goal">🎯 هدف این گام: ${escapeHtml(s.next_goal)}</div>` : ''}
          ${s.evaluation ? `<div style="font-size:12.5px; color:var(--text-secondary);">🔍 ارزیابی گام قبل: ${escapeHtml(s.evaluation)}</div>` : ''}
          ${
            s.actions && s.actions.length
              ? `<div class="step-actions">${s.actions.map((a) => `<span class="action-tag">${escapeHtml(a)}</span>`).join('')}</div>`
              : ''
          }
        </div>
      `
      )
      .join('');
  }
}

function startAgentPolling() {
  if (state.agentPollTimer) clearInterval(state.agentPollTimer);
  state.agentPollTimer = setInterval(async () => {
    try {
      const st = await apiFetch('/api/agent/state');
      renderAgentState(st);
      if (!['starting', 'running', 'paused', 'stopping'].includes(st.status)) {
        clearInterval(state.agentPollTimer);
        state.agentPollTimer = null;
        refreshHistory();
      }
    } catch (_) {
      // ignore transient poll errors
    }
  }, 1100);
}

// ---------------- Settings & Doctor ----------------

function applySettingsToForm(s) {
  state.settings = s;
  $('chkShowBrowser').checked = !Boolean(s.headless);
  $('chkUseVision').checked = Boolean(s.use_vision);
  $('chkPersianOutput').checked = Boolean(s.force_persian_output);
  $('numQuickMaxSteps').value = s.max_steps || 35;

  $('setBrowserChannel').value = s.browser_channel || 'auto';
  $('customExeGroup').style.display = s.browser_channel === 'custom' ? 'block' : 'none';
  $('setExecutablePath').value = s.executable_path || '';
  $('setUserDataDir').value = s.user_data_dir || '';
  $('setMaxSteps').value = s.max_steps || 35;
  $('setMaxActions').value = s.max_actions_per_step || 4;
  $('setKeepAlive').checked = Boolean(s.keep_browser_open);
  $('setFlashMode').checked = Boolean(s.flash_mode);
  $('setEnablePlanning').checked = Boolean(s.enable_planning);
  $('setGenerateGif').checked = Boolean(s.generate_gif);
  $('setCustomInstructions').value = s.custom_instructions || '';
}

// ---------------- Python Playground ----------------

async function regeneratePythonCode(notify = true) {
  try {
    const res = await apiFetch('/api/code/generate', {
      method: 'POST',
      body: JSON.stringify({
        task: $('taskInput').value.trim(),
        profile_id: state.activeProfileId,
      }),
    });
    $('pythonCodeEditor').value = res.code || '';
    if (notify) showToast('🔄 کد پایتون بر اساس دستور و کلید فعال شما بروزرسانی شد.');
  } catch (err) {
    if (notify) showToast(`خطا: ${err.message}`);
  }
}

// ---------------- History ----------------

async function refreshHistory() {
  try {
    const res = await apiFetch('/api/history');
    renderHistory(res.items || []);
  } catch (_) {}
}

function renderHistory(items) {
  $('historyCountBadge').textContent = String(items.length);
  const box = $('historyListContainer');
  if (!items.length) {
    box.innerHTML = `
      <div class="empty-state">
        <div class="empty-icon">🕘</div>
        <div>هنوز تاریخچه‌ای ثبت نشده است.</div>
      </div>
    `;
    return;
  }

  box.innerHTML = items
    .map(
      (it, idx) => `
      <div class="profile-card">
        <div style="display:flex; justify-content:space-between; align-items:center; flex-wrap:wrap; gap:8px;">
          <div>
            <strong>${escapeHtml(it.task.slice(0, 110))}${it.task.length > 110 ? '...' : ''}</strong>
            <div style="font-size:12px; color:var(--text-secondary); margin-top:3px;">
              📅 <span class="ltr">${escapeHtml(it.date_str)}</span> • 🤖 ${escapeHtml(it.profile_name)} (${escapeHtml(it.model_name)}) • ${it.steps_count} گام در ${it.duration_seconds} ثانیه
            </div>
          </div>
          <span class="badge ${it.status === 'completed' ? 'badge-emerald' : 'badge-rose'}">
            ${it.status === 'completed' ? 'موفق' : escapeHtml(it.status)}
          </span>
        </div>
        <div class="result-content" style="max-height:180px; margin-top:10px;">${escapeHtml(it.final_result || '')}</div>
        <div style="display:flex; gap:8px; margin-top:10px; flex-wrap:wrap;">
          <button class="btn btn-sm btn-primary" onclick="rerunHistoryItem(${idx})">🔄 انتقال دستور به میز کار</button>
          <button class="btn btn-sm" onclick="copyHistoryResult(${idx})">📋 کپی نتیجه</button>
        </div>
      </div>
    `
    )
    .join('');
  state._historyItems = items;
}

window.rerunHistoryItem = function (idx) {
  const it = (state._historyItems || [])[idx];
  if (!it) return;
  $('taskInput').value = it.task;
  switchTab('workspace');
  showToast('دستور در میز کار قرار گرفت.');
};

window.copyHistoryResult = function (idx) {
  const it = (state._historyItems || [])[idx];
  if (!it) return;
  navigator.clipboard.writeText(it.final_result || '');
  showToast('📋 متن نتیجه کپی شد.');
};

// ---------------- Event Listeners & Bootstrap ----------------

async function initApp() {
  initTheme();

  // Tab buttons
  document.querySelectorAll('.nav-tab').forEach((btn) => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  $('btnQuickAddKey').addEventListener('click', () => {
    resetProfileForm();
    switchTab('profiles');
  });

  // Header profile switcher
  $('headerProfileSelect').addEventListener('change', (e) => {
    const val = e.target.value;
    if (!val) {
      switchTab('profiles');
      return;
    }
    window.activateProfile(val);
  });

  // Fallback profile switcher
  $('fallbackProfileSelect').addEventListener('change', async (e) => {
    try {
      const res = await apiFetch('/api/profiles/switch', {
        method: 'POST',
        body: JSON.stringify({
          active_profile_id: state.activeProfileId,
          fallback_profile_id: e.target.value || '',
        }),
      });
      updateProfilesState(res.profiles_state);
      showToast(e.target.value ? '🛡️ مدل پشتیبان خودکار فعال شد!' : 'مدل پشتیبان غیرفعال شد.');
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    }
  });

  // Prompt helper chips
  document.querySelectorAll('.chip[data-append]').forEach((chip) => {
    chip.addEventListener('click', () => {
      const box = $('taskInput');
      box.value = (box.value.trim() + ' ' + chip.dataset.append.trim()).trim();
      box.focus();
    });
  });

  $('btnClearTask').addEventListener('click', () => {
    $('taskInput').value = '';
    $('taskInput').focus();
  });

  // Suggested model dropdown syncs to free-text model input & vision checkbox
  $('profSuggestedModelSelect').addEventListener('change', (e) => {
    const opt = e.target.selectedOptions[0];
    if (opt) {
      $('profModelInput').value = opt.value;
      $('profVisionChk').checked = opt.dataset.vision === 'true';
    }
  });

  $('profTempInput').addEventListener('input', (e) => {
    $('tempValLabel').textContent = e.target.value;
  });

  $('btnToggleKeyVisibility').addEventListener('click', () => {
    const inp = $('profApiKeyInput');
    inp.type = inp.type === 'password' ? 'text' : 'password';
  });

  $('btnResetProfileForm').addEventListener('click', resetProfileForm);

  // Scan live Routeway Free models
  $('btnScanRouteway').addEventListener('click', async () => {
    const key = $('profApiKeyInput').value.trim();
    const baseUrl = $('profBaseUrlInput').value.trim() || 'https://api.routeway.ai/v1';
    const btn = $('btnScanRouteway');
    btn.disabled = true;
    btn.textContent = '⏳ در حال دریافت...';
    try {
      const qs = `api_key=${encodeURIComponent(key)}&base_url=${encodeURIComponent(baseUrl)}`;
      const res = await apiFetch(`/api/routeway/models?${qs}`);
      showToast(res.message_fa, 5000);
      if (res.ok && res.models && res.models.length > 0) {
        const prov = state.providers.find((x) => x.id === 'routeway');
        if (prov) prov.models = res.models;
        const sel = $('profSuggestedModelSelect');
        sel.innerHTML = res.models
          .map((m) => `<option value="${escapeHtml(m.id)}" data-vision="${m.vision}">${escapeHtml(m.label)}</option>`)
          .join('');
        $('profModelInput').value = res.models[0].id;
        $('profVisionChk').checked = Boolean(res.models[0].vision);
      }
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = '🔄 بروزرسانی لیست رایگان';
    }
  });

  // 1-click Bulk Setup for top 5 Routeway Free models
  $('btnCreateRoutewayPack').addEventListener('click', async () => {
    const apiKey = $('profApiKeyInput').value.trim();
    const baseUrl = $('profBaseUrlInput').value.trim() || 'https://api.routeway.ai/v1';
    const btn = $('btnCreateRoutewayPack');
    btn.disabled = true;
    btn.textContent = '⏳ در حال ساخت ۵ پروفایل رایگان...';
    try {
      const res = await apiFetch('/api/routeway/bulk-pack', {
        method: 'POST',
        body: JSON.stringify({ api_key: apiKey, base_url: baseUrl }),
      });
      if (!res.ok) {
        showToast(`⚠️ ${res.error || 'خطا'}`);
        $('profApiKeyInput').focus();
        return;
      }
      updateProfilesState(res.profiles_state);
      resetProfileForm();
      showToast(res.message_fa, 6000);
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ ساخت خودکار پک ۵ مدل رایگان Routeway با همین کلید';
    }
  });

  // Scan live OpenRouter FREE ($0.00) models
  $('btnScanOpenRouter').addEventListener('click', async () => {
    const key = $('profApiKeyInput').value.trim();
    const baseUrl = $('profBaseUrlInput').value.trim() || 'https://openrouter.ai/api/v1';
    const btn = $('btnScanOpenRouter');
    btn.disabled = true;
    btn.textContent = '⏳ در حال دریافت...';
    try {
      const qs = `api_key=${encodeURIComponent(key)}&base_url=${encodeURIComponent(baseUrl)}`;
      const res = await apiFetch(`/api/openrouter/models?${qs}`);
      showToast(res.message_fa, 5000);
      if (res.ok && res.models && res.models.length > 0) {
        const prov = state.providers.find((x) => x.id === 'openrouter');
        if (prov) prov.models = res.models;
        const sel = $('profSuggestedModelSelect');
        sel.innerHTML = res.models
          .map((m) => `<option value="${escapeHtml(m.id)}" data-vision="${m.vision}">${escapeHtml(m.label)}</option>`)
          .join('');
        $('profModelInput').value = res.models[0].id;
        $('profVisionChk').checked = Boolean(res.models[0].vision);
      }
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = '🔄 بروزرسانی لیست رایگان OpenRouter';
    }
  });

  // 1-click Separate Bulk Setup for top 5 OpenRouter Free models
  $('btnCreateOpenRouterPack').addEventListener('click', async () => {
    const apiKey = $('profApiKeyInput').value.trim();
    const baseUrl = $('profBaseUrlInput').value.trim() || 'https://openrouter.ai/api/v1';
    const btn = $('btnCreateOpenRouterPack');
    btn.disabled = true;
    btn.textContent = '⏳ در حال ساخت ۵ پروفایل رایگان OpenRouter...';
    try {
      const res = await apiFetch('/api/openrouter/bulk-pack', {
        method: 'POST',
        body: JSON.stringify({ api_key: apiKey, base_url: baseUrl }),
      });
      if (!res.ok) {
        showToast(`⚠️ ${res.error || 'خطا'}`);
        $('profApiKeyInput').focus();
        return;
      }
      updateProfilesState(res.profiles_state);
      resetProfileForm();
      showToast(res.message_fa, 6500);
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = '⚡ ساخت خودکار پک ۵ مدل رایگان OpenRouter با همین کلید';
    }
  });

  // Scan local Ollama models
  $('btnScanOllama').addEventListener('click', async () => {
    const host = $('profBaseUrlInput').value.trim() || 'http://localhost:11434';
    const btn = $('btnScanOllama');
    btn.disabled = true;
    btn.textContent = '⏳ در حال جستجو...';
    try {
      const res = await apiFetch(`/api/ollama/models?host=${encodeURIComponent(host)}`);
      showToast(res.message_fa, 4500);
      if (res.ok && res.models.length > 0) {
        const sel = $('profSuggestedModelSelect');
        sel.innerHTML = res.models
          .map((m) => `<option value="${escapeHtml(m.id)}" data-vision="false">${escapeHtml(m.id)} (${m.size_gb} GB)</option>`)
          .join('');
        $('profModelInput').value = res.models[0].id;
      }
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    } finally {
      btn.disabled = false;
      btn.textContent = '🔄 اسکن Ollama';
    }
  });

  // Test form profile before saving
  $('btnTestFormProfile').addEventListener('click', async () => {
    const btn = $('btnTestFormProfile');
    const inlineBox = $('testResultInline');
    btn.disabled = true;
    btn.textContent = '⏳ در حال تست ارتباط با مدل...';
    inlineBox.style.display = 'none';
    try {
      const res = await apiFetch('/api/profiles/test', {
        method: 'POST',
        body: JSON.stringify({
          profile_id: $('profIdInput').value || null,
          provider: state.selectedProviderId,
          model: $('profModelInput').value.trim(),
          api_key: $('profApiKeyInput').value.trim() || null,
          base_url: $('profBaseUrlInput').value.trim(),
          temperature: parseFloat($('profTempInput').value || '0.2'),
          free_only: (state.selectedProviderId === 'routeway' || state.selectedProviderId === 'openrouter') ? $('profFreeOnlyChk').checked : false,
          compat_schema_mode: $('profCompatChk').checked,
        }),
      });
      inlineBox.style.display = 'block';
      inlineBox.style.borderRightColor = res.ok ? 'var(--emerald)' : 'var(--rose)';
      inlineBox.textContent = res.message_fa;
      if (res.profiles_state) updateProfilesState(res.profiles_state);
    } catch (err) {
      inlineBox.style.display = 'block';
      inlineBox.style.borderRightColor = 'var(--rose)';
      inlineBox.textContent = `❌ خطا: ${err.message}`;
    } finally {
      btn.disabled = false;
      btn.textContent = '🧪 تست سلامت همین کلید';
    }
  });

  // Save profile
  $('btnSaveProfile').addEventListener('click', async () => {
    const payload = {
      id: $('profIdInput').value || null,
      name: $('profNameInput').value.trim(),
      provider: state.selectedProviderId,
      model: $('profModelInput').value.trim(),
      api_key: $('profApiKeyInput').value.trim(),
      keep_existing_key: true,
      base_url: $('profBaseUrlInput').value.trim(),
      temperature: parseFloat($('profTempInput').value || '0.2'),
      vision_enabled: $('profVisionChk').checked,
      free_only: (state.selectedProviderId === 'routeway' || state.selectedProviderId === 'openrouter') ? $('profFreeOnlyChk').checked : false,
      compat_schema_mode: $('profCompatChk').checked,
      set_active: true,
    };
    try {
      const res = await apiFetch('/api/profiles', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      updateProfilesState(res.profiles_state);
      resetProfileForm();
      showToast(`✅ پروفایل «${res.profile.name}» ذخیره و فعال شد!`);
    } catch (err) {
      showToast(`خطا در ذخیره: ${err.message}`);
    }
  });

  // Start / Pause / Resume / Stop Agent
  $('btnStartAgent').addEventListener('click', async () => {
    const task = $('taskInput').value.trim();
    if (!task) {
      showToast('✍️ لطفاً ابتدا دستور خود را در کادر بالا بنویسید (یا از تب دستورهای آماده انتخاب کنید).');
      $('taskInput').focus();
      return;
    }
    if (state.profiles.length === 0) {
      showToast('🔑 ابتدا یک کلید هوش مصنوعی (API Key) یا مدل لوکال ثبت کنید.');
      switchTab('profiles');
      return;
    }

    $('stepsContainer').innerHTML = '';
    $('finalResultBox').style.display = 'none';

    try {
      const res = await apiFetch('/api/agent/start', {
        method: 'POST',
        body: JSON.stringify({
          task,
          profile_id: state.activeProfileId,
          override_settings: {
            headless: !$('chkShowBrowser').checked,
            use_vision: $('chkUseVision').checked,
            force_persian_output: $('chkPersianOutput').checked,
            max_steps: parseInt($('numQuickMaxSteps').value || '35', 10),
          },
        }),
      });
      if (!res.ok) {
        showToast(res.error || 'خطا در شروع عملیات');
        return;
      }
      showToast('🚀 عملیات آغاز شد! مراحل را به صورت زنده دنبال کنید.');
      startAgentPolling();
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    }
  });

  $('btnPauseAgent').addEventListener('click', async () => {
    const res = await apiFetch('/api/agent/pause', { method: 'POST' });
    if (res.ok) showToast('⏸️ عملیات موقتاً متوقف شد.');
  });

  $('btnResumeAgent').addEventListener('click', async () => {
    const res = await apiFetch('/api/agent/resume', { method: 'POST' });
    if (res.ok) showToast('▶️ ربات کار خود را از سر گرفت.');
  });

  $('btnStopAgent').addEventListener('click', async () => {
    const res = await apiFetch('/api/agent/stop', { method: 'POST' });
    if (res.ok) showToast('⏹️ دستور توقف به ربات ارسال شد.');
  });

  $('btnSendFollowup').addEventListener('click', async () => {
    const txt = $('followupInput').value.trim();
    if (!txt) return;
    const res = await apiFetch('/api/agent/followup', {
      method: 'POST',
      body: JSON.stringify({ task: txt }),
    });
    if (res.ok) {
      $('followupInput').value = '';
      showToast('➕ دستور تکمیلی به ربات منتقل شد.');
    }
  });

  $('btnCopyResult').addEventListener('click', () => {
    navigator.clipboard.writeText($('finalResultText').textContent || '');
    showToast('📋 متن نتیجه در کلیپ‌بورد کپی شد.');
  });

  $('btnSaveResult').addEventListener('click', () => {
    const content = `# گزارش عملیات Browser Use\n\n## دستور:\n${$('taskInput').value}\n\n## نتیجه:\n${$('finalResultText').textContent}\n`;
    saveFileUniversal(content, 'browser_use_report.md');
  });

  // Screenshot zoom modal
  $('liveScreenshotImg').addEventListener('click', () => {
    $('modalScreenshotImg').src = $('liveScreenshotImg').src;
    $('screenshotModal').classList.add('open');
  });
  $('screenshotModal').addEventListener('click', () => {
    $('screenshotModal').classList.remove('open');
  });

  // Settings tab handlers
  $('setBrowserChannel').addEventListener('change', (e) => {
    $('customExeGroup').style.display = e.target.value === 'custom' ? 'block' : 'none';
  });

  $('btnBrowseExe').addEventListener('click', async () => {
    if (hasPyWebView() && window.pywebview.api.pick_browser_exe) {
      const picked = await window.pywebview.api.pick_browser_exe();
      if (picked) $('setExecutablePath').value = picked;
    } else {
      showToast('در حالت وب، مسیر فایل .exe را مستقیماً در کادر کپی کنید (پنجره انتخاب فایل در اجرای دسکتاپ با start.bat فعال است).');
    }
  });

  $('btnBrowseUserData').addEventListener('click', async () => {
    if (hasPyWebView() && window.pywebview.api.pick_folder) {
      const picked = await window.pywebview.api.pick_folder();
      if (picked) $('setUserDataDir').value = picked;
    } else {
      showToast('در حالت وب، مسیر پوشه را مستقیماً در کادر وارد کنید (پنجره انتخاب پوشه در اجرای دسکتاپ با start.bat فعال است).');
    }
  });

  $('btnSaveSettings').addEventListener('click', async () => {
    const payload = {
      headless: !$('chkShowBrowser').checked,
      browser_channel: $('setBrowserChannel').value,
      executable_path: $('setExecutablePath').value.trim(),
      user_data_dir: $('setUserDataDir').value.trim(),
      max_steps: parseInt($('setMaxSteps').value || '35', 10),
      max_actions_per_step: parseInt($('setMaxActions').value || '4', 10),
      keep_browser_open: $('setKeepAlive').checked,
      flash_mode: $('setFlashMode').checked,
      enable_planning: $('setEnablePlanning').checked,
      generate_gif: $('setGenerateGif').checked,
      use_vision: $('chkUseVision').checked,
      force_persian_output: $('chkPersianOutput').checked,
      custom_instructions: $('setCustomInstructions').value.trim(),
    };
    try {
      const res = await apiFetch('/api/settings', {
        method: 'POST',
        body: JSON.stringify(payload),
      });
      applySettingsToForm(res.settings);
      showToast('💾 تنظیمات مرورگر و ربات با موفقیت ذخیره شد.');
    } catch (err) {
      showToast(`خطا: ${err.message}`);
    }
  });

  $('btnRefreshDoctor').addEventListener('click', async () => {
    const health = await apiFetch('/api/system');
    renderSystemHealth(health);
    showToast('🩺 وضعیت سیستم بروزرسانی شد.');
  });

  $('btnInstallChromium').addEventListener('click', async () => {
    const res = await apiFetch('/api/browser/install', { method: 'POST' });
    if (!res.ok) {
      showToast(res.error || 'خطا');
      return;
    }
    const logBox = $('chromiumInstallLogs');
    logBox.style.display = 'block';
    $('btnInstallChromium').disabled = true;
    state.installPollTimer = setInterval(async () => {
      const st = await apiFetch('/api/browser/install/status');
      logBox.textContent = st.logs || '';
      logBox.scrollTop = logBox.scrollHeight;
      if (!st.installing) {
        clearInterval(state.installPollTimer);
        $('btnInstallChromium').disabled = false;
        const health = await apiFetch('/api/system');
        renderSystemHealth(health);
        showToast(st.done_ok ? '✅ مرورگر Chromium با موفقیت نصب شد!' : '❌ نصب مرورگر با خطا مواجه شد.');
      }
    }, 1200);
  });

  // Python Playground buttons
  $('btnRegenerateCode').addEventListener('click', () => regeneratePythonCode(true));
  $('btnCopyCode').addEventListener('click', () => {
    navigator.clipboard.writeText($('pythonCodeEditor').value || '');
    showToast('📋 کد پایتون کپی شد.');
  });
  $('btnSavePyFile').addEventListener('click', () => {
    saveFileUniversal($('pythonCodeEditor').value || '', 'browser_use_task.py');
  });

  $('btnRunPythonCode').addEventListener('click', async () => {
    const code = $('pythonCodeEditor').value;
    const res = await apiFetch('/api/code/run', {
      method: 'POST',
      body: JSON.stringify({ code, profile_id: state.activeProfileId }),
    });
    if (!res.ok) {
      showToast(res.error || 'خطا');
      return;
    }
    $('btnRunPythonCode').style.display = 'none';
    $('btnStopPythonCode').style.display = 'inline-flex';
    if (state.codePollTimer) clearInterval(state.codePollTimer);
    state.codePollTimer = setInterval(async () => {
      const st = await apiFetch('/api/code/state');
      const term = $('pythonTerminalOutput');
      term.textContent = st.output || '';
      term.scrollTop = term.scrollHeight;
      if (!st.running) {
        clearInterval(state.codePollTimer);
        $('btnRunPythonCode').style.display = 'inline-flex';
        $('btnStopPythonCode').style.display = 'none';
      }
    }, 800);
  });

  $('btnStopPythonCode').addEventListener('click', async () => {
    await apiFetch('/api/code/stop', { method: 'POST' });
    showToast('⏹️ اسکریپت متوقف شد.');
  });

  $('btnClearHistory').addEventListener('click', async () => {
    if (!confirm('آیا تمام تاریخچه اجراهای قبلی پاک شود؟')) return;
    await apiFetch('/api/history', { method: 'DELETE' });
    renderHistory([]);
    showToast('🗑️ تاریخچه پاک شد.');
  });

  // Bootstrap initial data from backend
  try {
    const boot = await apiFetch('/api/bootstrap');
    state.providers = boot.providers || [];
    state.templates = boot.templates || [];
    renderProviderCards();
    renderTemplates();
    updateProfilesState(boot.profiles_state || { profiles: [] });
    applySettingsToForm(boot.settings || {});
    renderSystemHealth(boot.system_health || { browsers: [] });
    renderHistory(boot.history || []);
    if (boot.agent_state) {
      renderAgentState(boot.agent_state);
      if (['starting', 'running', 'paused', 'stopping'].includes(boot.agent_state.status)) {
        startAgentPolling();
      }
    }
    regeneratePythonCode(false);
  } catch (err) {
    showToast(`خطا در بارگذاری اولیه برنامه: ${err.message}`, 6000);
  }
}

document.addEventListener('DOMContentLoaded', initApp);

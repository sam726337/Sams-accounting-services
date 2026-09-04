const currentYear = new Date().getFullYear();
document.querySelectorAll(".current-year").forEach((node) => {
  node.textContent = currentYear;
});

const attributionKeys = [
  "utm_source",
  "utm_medium",
  "utm_campaign",
  "utm_content",
  "utm_term",
  "gclid",
  "fbclid",
  "msclkid",
];
const attributionStorageKeys = {
  firstTouch: "jishu_first_touch_attribution",
  lastTouch: "jishu_last_touch_attribution",
};

const readStoredAttribution = (key) => {
  try {
    return JSON.parse(window.localStorage.getItem(key)) || {};
  } catch {
    return {};
  }
};

const storeAttribution = (key, value) => {
  try {
    window.localStorage.setItem(key, JSON.stringify(value));
  } catch {
    // Tracking must never interrupt the visitor's journey.
  }
};

const currentCampaignAttribution = attributionKeys.reduce((values, key) => {
  const value = new URLSearchParams(window.location.search).get(key);
  if (value) values[key] = value.slice(0, 100);
  return values;
}, {});

if (Object.keys(currentCampaignAttribution).length) {
  const attribution = {
    ...currentCampaignAttribution,
    landing_page: window.location.pathname,
    captured_at: new Date().toISOString(),
  };

  if (!Object.keys(readStoredAttribution(attributionStorageKeys.firstTouch)).length) {
    storeAttribution(attributionStorageKeys.firstTouch, attribution);
  }
  storeAttribution(attributionStorageKeys.lastTouch, attribution);
}

const getAttributionParameters = () => {
  const firstTouch = readStoredAttribution(attributionStorageKeys.firstTouch);
  const lastTouch = readStoredAttribution(attributionStorageKeys.lastTouch);

  return attributionKeys.reduce((parameters, key) => {
    if (firstTouch[key]) parameters[`first_${key}`] = firstTouch[key];
    if (lastTouch[key]) parameters[`last_${key}`] = lastTouch[key];
    return parameters;
  }, {});
};

const trackEvent = (eventName, parameters = {}) => {
  if (typeof window.gtag !== "function") return;

  window.gtag("event", eventName, {
    page_path: window.location.pathname,
    ...getAttributionParameters(),
    ...parameters,
  });
};

const siteHeader = document.querySelector(".site-header");
const mainNavigation = siteHeader?.querySelector(".nav-links");

if (siteHeader && mainNavigation) {
  const navigationId = mainNavigation.id || "main-navigation";
  const menuButton = document.createElement("button");

  mainNavigation.id = navigationId;
  menuButton.className = "nav-toggle";
  menuButton.type = "button";
  menuButton.setAttribute("aria-controls", navigationId);
  menuButton.setAttribute("aria-expanded", "false");
  menuButton.setAttribute("aria-label", "Open navigation menu");
  menuButton.innerHTML = '<span aria-hidden="true"></span><span class="nav-toggle-label">Menu</span>';
  siteHeader.insertBefore(menuButton, mainNavigation);
  siteHeader.classList.add("nav-ready");

  const setMenuOpen = (isOpen) => {
    menuButton.setAttribute("aria-expanded", String(isOpen));
    menuButton.setAttribute("aria-label", isOpen ? "Close navigation menu" : "Open navigation menu");
    mainNavigation.dataset.open = String(isOpen);
  };

  menuButton.addEventListener("click", () => {
    setMenuOpen(menuButton.getAttribute("aria-expanded") !== "true");
  });

  mainNavigation.addEventListener("click", (event) => {
    if (event.target.closest("a")) setMenuOpen(false);
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") setMenuOpen(false);
  });

  window.addEventListener("resize", () => {
    if (window.innerWidth > 860) setMenuOpen(false);
  });
}

const whatsappForm = document.querySelector("[data-whatsapp-form]");

if (whatsappForm) {
  whatsappForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const formData = new FormData(whatsappForm);
    const whatsappNumber = whatsappForm.dataset.whatsappNumber;
    const status = whatsappForm.querySelector(".form-status");
    const message = [
      "Hello The Jishu IT Solution,",
      "",
      "I would like to discuss a project.",
      `Name: ${formData.get("name")}`,
      `Contact: ${formData.get("contact")}`,
      `Service: ${formData.get("service")}`,
      `Budget: ${formData.get("budget")}`,
      `Timeline: ${formData.get("timeline")}`,
      "",
      "Project details:",
      formData.get("message"),
    ].join("\n");

    status.textContent = "Opening WhatsApp with your enquiry...";
    trackEvent("contact_form_intent", {
      contact_method: "whatsapp",
      service: String(formData.get("service") || "not_selected").slice(0, 100),
    });
    window.location.href = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
  });
}

const websiteAuditForm = document.querySelector("[data-website-audit-form]");

if (websiteAuditForm) {
  websiteAuditForm.addEventListener("submit", (event) => {
    event.preventDefault();

    const formData = new FormData(websiteAuditForm);
    const whatsappNumber = websiteAuditForm.dataset.whatsappNumber;
    const status = websiteAuditForm.querySelector(".form-status");
    const message = [
      "Hello The Jishu IT Solution,",
      "",
      "I would like to request a free website audit.",
      `Name: ${formData.get("name")}`,
      `Contact: ${formData.get("contact")}`,
      `Website: ${formData.get("website")}`,
      `Business: ${formData.get("business")}`,
      `Target market: ${formData.get("market")}`,
      `Primary goal: ${formData.get("goal")}`,
      "",
      "Biggest concern:",
      formData.get("concern"),
      "",
      "I understand that the initial audit reviews public pages and does not guarantee rankings or sales results.",
    ].join("\n");

    status.textContent = "Opening WhatsApp with your free audit request...";
    trackEvent("free_audit_request", {
      contact_method: "whatsapp",
      target_market: String(formData.get("market") || "not_selected").slice(0, 100),
      primary_goal: String(formData.get("goal") || "not_selected").slice(0, 100),
    });
    window.location.href = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
  });
}

document.addEventListener("click", (event) => {
  const link = event.target.closest("a[href]");
  if (!link) return;

  const href = link.href;

  if (/\.exe(?:$|[?#])/i.test(href)) {
    trackEvent("installer_download", {
      file_name: href.split("/").pop()?.split(/[?#]/)[0] || "windows_installer",
      link_url: href,
    });
  }

  if (/https?:\/\/(?:www\.)?(?:wa\.me|api\.whatsapp\.com)\//i.test(href)) {
    trackEvent("whatsapp_click", {
      link_text: link.textContent.trim().slice(0, 100),
      link_location: link.closest("form") ? "form" : "page_link",
    });
  }

  if (link.protocol === "mailto:" || link.protocol === "tel:") {
    trackEvent("contact_click", {
      contact_method: link.protocol === "mailto:" ? "email" : "phone",
      link_location: link.closest("footer") ? "footer" : "page",
    });
  }
});

document.querySelectorAll("video").forEach((video, videoIndex) => {
  const videoName = video.getAttribute("aria-label") || `video_${videoIndex + 1}`;
  const reportedMilestones = new Set();

  video.addEventListener("play", () => {
    if (reportedMilestones.has("play")) return;
    reportedMilestones.add("play");
    trackEvent("demo_video_play", { video_name: videoName });
  });

  video.addEventListener("timeupdate", () => {
    if (!Number.isFinite(video.duration) || video.duration <= 0) return;

    const progress = (video.currentTime / video.duration) * 100;
    [25, 50, 75].forEach((milestone) => {
      if (progress < milestone || reportedMilestones.has(milestone)) return;
      reportedMilestones.add(milestone);
      trackEvent("demo_video_progress", {
        video_name: videoName,
        video_percent: milestone,
      });
    });
  });

  video.addEventListener("ended", () => {
    if (reportedMilestones.has("complete")) return;
    reportedMilestones.add("complete");
    trackEvent("demo_video_complete", { video_name: videoName });
  });
});

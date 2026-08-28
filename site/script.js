const currentYear = new Date().getFullYear();
document.querySelectorAll(".current-year").forEach((node) => {
  node.textContent = currentYear;
});

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
    window.location.href = `https://wa.me/${whatsappNumber}?text=${encodeURIComponent(message)}`;
  });
}

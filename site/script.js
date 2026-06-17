const currentYear = new Date().getFullYear();
document.querySelectorAll(".current-year").forEach((node) => {
  node.textContent = currentYear;
});

(() => {
  const date = document.getElementById("date");
  if (!date) return;

  date.textContent = `DATE / ${new Date().toLocaleDateString("ru-RU")}`;
})();

(() => {
  const timer = document.getElementById("timer");
  if (!timer) return;
  const startTime = Date.now();

  function updateTimer() {
    const elapsed = Math.floor((Date.now() - startTime) / 1000);

    const hours = Math.floor(elapsed / 3600);
    const minutes = Math.floor((elapsed % 3600) / 60);
    const seconds = elapsed % 60;

    const format = (value) => String(value).padStart(2, "0");

    timer.textContent = `REC ${format(hours)}:${format(minutes)}:${format(seconds)}`;
  }

  updateTimer();
  setInterval(updateTimer, 1000);
})();

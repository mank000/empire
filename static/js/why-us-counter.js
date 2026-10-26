(() => {
  const numbers = [...document.querySelectorAll(".achievements .achievement-number strong")];
  if (!numbers.length || window.matchMedia("(prefers-reduced-motion: reduce)").matches || !window.IntersectionObserver) return;

  const targets = numbers.map((number) => Number(number.textContent.trim()));
  if (targets.some((target) => !Number.isFinite(target))) return;

  numbers.forEach((number, index) => {
    number.style.display = "inline-block";
    number.style.width = `${String(targets[index]).length}ch`;
    number.style.textAlign = "right";
    number.textContent = "0";
  });

  const achievements = document.querySelector(".why-us-achievements");
  const observer = new IntersectionObserver((entries) => {
    if (!entries[0].isIntersecting) return;
    observer.disconnect();

    const duration = 1000;
    const start = performance.now();

    const tick = (now) => {
      const progress = Math.min((now - start) / duration, 1);
      const eased = 1 - (1 - progress) ** 3;

      numbers.forEach((number, index) => {
        number.textContent = String(Math.round(targets[index] * eased));
      });

      if (progress < 1) requestAnimationFrame(tick);
    };

    requestAnimationFrame(tick);
  }, { threshold: 0.25 });

  observer.observe(achievements);
})();

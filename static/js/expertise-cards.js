(() => {
  const cards = document.querySelector(".expertise-cards");
  if (!cards || !window.IntersectionObserver || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  cards.classList.add("is-reveal-ready");

  const observer = new IntersectionObserver(([entry]) => {
    if (!entry.isIntersecting) return;
    observer.disconnect();
    cards.classList.add("is-visible");
  }, { threshold: 0.15 });

  observer.observe(cards);
})();

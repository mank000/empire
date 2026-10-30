(() => {
  const section = document.querySelector(".area-of-work");
  if (!section) return;

  const panel = section.querySelector(".area-of-work-content");
  const track = section.querySelector(".collection-cards");
  const windowWidth = track.parentElement;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
  let distance = 0;
  let start = 0;

  function onScroll() {
    if (!section.classList.contains("is-pinned")) return;

    const moved = Math.max(0, Math.min(distance, window.scrollY - start));
    track.style.transform = `translate3d(${-moved}px, 0, 0)`;
  }

  function measure() {
    section.classList.remove("is-pinned");
    track.style.transform = "";
    distance = Math.max(0, track.scrollWidth - windowWidth.clientWidth);

    if (distance === 0 || window.innerWidth <= 760 || reducedMotion.matches) {
      section.style.removeProperty("--area-scroll");
      return;
    }

    section.style.setProperty("--area-scroll", `${distance}px`);
    section.classList.add("is-pinned");

    if (panel.scrollHeight > panel.clientHeight + 1) {
      section.classList.remove("is-pinned");
      section.style.removeProperty("--area-scroll");
      return;
    }

    start = section.getBoundingClientRect().top + window.scrollY;
    onScroll();
  }

  window.addEventListener("scroll", onScroll, { passive: true });
  window.addEventListener("resize", measure);
  reducedMotion.addEventListener("change", measure);
  document.fonts.ready.then(measure);
  measure();
})();

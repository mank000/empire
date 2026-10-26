(() => {
  const tickets = document.querySelectorAll(".ticket-creator");
  if (!tickets.length || !window.IntersectionObserver || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  tickets.forEach((ticket) => ticket.classList.add("is-glow-ready"));

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) return;
      entry.target.classList.add("is-visible");
      observer.unobserve(entry.target);
    });
  }, { threshold: 0.2 });

  tickets.forEach((ticket) => observer.observe(ticket));
})();

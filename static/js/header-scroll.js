const header = document.querySelector("body > header");

if (header) {
  let lastY = window.scrollY;

  window.addEventListener(
    "scroll",
    () => {
      const currentY = window.scrollY;

      if (currentY <= header.offsetHeight) {
        header.classList.remove("header-hidden");
        lastY = currentY;
        return;
      }

      if (Math.abs(currentY - lastY) >= 5) {
        header.classList.toggle("header-hidden", currentY > lastY);
        lastY = currentY;
      }
    },
    { passive: true },
  );
}

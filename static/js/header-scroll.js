(() => {
  const header = document.querySelector("body > header");

  if (header) {
    const menuToggle = header.querySelector(".header-menu-toggle");
    const menu = header.querySelector(".header-menu");
    const menuBackdrop = header.querySelector(".header-menu-backdrop");
    const menuClose = header.querySelector(".header-menu-close");
    let lastY = window.scrollY;

    if (menuToggle && menu) {
      const mobileQuery = window.matchMedia("(max-width: 760px)");

      const setMenuOpen = (open, returnFocus = false) => {
        menu.classList.toggle("is-open", open);
        menuBackdrop.classList.toggle("is-open", open);
        document.body.classList.toggle("header-menu-open", open);
        menuToggle.setAttribute("aria-expanded", String(open));
        menuToggle.setAttribute("aria-label", open ? "Закрыть меню" : "Открыть меню");
        if (open) {
          menu.setAttribute("role", "dialog");
          menu.setAttribute("aria-modal", "true");
          menu.setAttribute("aria-label", "Меню");
          menuClose.focus();
        } else {
          menu.removeAttribute("role");
          menu.removeAttribute("aria-modal");
          menu.removeAttribute("aria-label");
          if (returnFocus) menuToggle.focus();
        }
        header.classList.remove("header-hidden");
      };

      menuToggle.addEventListener("click", () => {
        setMenuOpen(menuToggle.getAttribute("aria-expanded") !== "true", true);
      });

      menuClose.addEventListener("click", () => setMenuOpen(false, true));
      menuBackdrop.addEventListener("click", () => setMenuOpen(false, true));

      menu.addEventListener("click", (event) => {
        if (event.target.closest("a")) setMenuOpen(false);
      });

      document.addEventListener("click", (event) => {
        if (menu.classList.contains("is-open") && !header.contains(event.target)) {
          setMenuOpen(false, true);
        }
      });

      document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && menu.classList.contains("is-open")) {
          setMenuOpen(false, true);
        }

        if (event.key === "Tab" && menu.classList.contains("is-open")) {
          const focusable = [...menu.querySelectorAll("a, button")];
          const first = focusable[0];
          const last = focusable[focusable.length - 1];
          if (event.shiftKey && document.activeElement === first) {
            event.preventDefault();
            last.focus();
          } else if (!event.shiftKey && document.activeElement === last) {
            event.preventDefault();
            first.focus();
          }
        }
      });

      mobileQuery.addEventListener("change", () => setMenuOpen(false));
    }

    window.addEventListener(
      "scroll",
      () => {
        const currentY = window.scrollY;

        if (menu?.classList.contains("is-open")) {
          lastY = currentY;
          return;
        }

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
})();

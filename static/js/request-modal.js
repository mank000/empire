const requestModal = document.querySelector("#request-modal");

if (requestModal) {
  let requestModalOpener;

  document.querySelectorAll("[data-request-modal-open]").forEach((button) => {
    button.addEventListener("click", (event) => {
      event.preventDefault();
      requestModalOpener = button;
      requestModal.showModal();
      document.body.classList.add("request-modal-open");
    });
  });

  requestModal.querySelector(".request-modal-close").addEventListener("click", () => {
    requestModal.close();
  });

  requestModal.addEventListener("click", (event) => {
    if (event.target === requestModal) requestModal.close();
  });

  requestModal.addEventListener("close", () => {
    document.body.classList.remove("request-modal-open");
    requestModalOpener?.focus();
  });
}

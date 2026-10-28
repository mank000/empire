const requestModal = document.querySelector("#request-modal");
const requestSuccessModal = document.querySelector("#request-success-modal");

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
    if (!requestSuccessModal?.open) {
      document.body.classList.remove("request-modal-open");
      requestModalOpener?.focus();
    }
  });
}

if (requestSuccessModal) {
  const closeSuccess = () => requestSuccessModal.close();

  document.querySelectorAll(".contact-form").forEach((form) => {
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      if (requestModal?.open) requestModal.close();
      requestSuccessModal.showModal();
      document.body.classList.add("request-modal-open");
      form.reset();
    });
  });

  requestSuccessModal.querySelector(".request-modal-close").addEventListener("click", closeSuccess);
  requestSuccessModal.querySelector(".request-success-home").addEventListener("click", () => {
    closeSuccess();
    window.scrollTo({ top: 0, behavior: "smooth" });
  });

  requestSuccessModal.addEventListener("click", (event) => {
    if (event.target === requestSuccessModal) closeSuccess();
  });

  requestSuccessModal.addEventListener("close", () => {
    if (!requestModal?.open) document.body.classList.remove("request-modal-open");
  });
}

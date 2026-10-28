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
    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const submit = form.querySelector('[type="submit"]');
      const error = form.querySelector(".form-submit-error");
      if (submit.disabled) return;
      error.hidden = true;
      form.querySelectorAll(".is-invalid").forEach((input) => input.classList.remove("is-invalid"));
      submit.disabled = true;
      try {
        const response = await fetch(form.dataset.url, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": form.elements.csrfmiddlewaretoken.value,
          },
          body: JSON.stringify({
            name: form.elements.name.value,
            phone: form.elements.phone.value,
            agreement: form.elements.agreement.checked,
          }),
        });
        const result = await response.json().catch(() => ({}));
        if (!response.ok || !result.success) {
          if (result.errors) {
            Object.entries(result.errors).forEach(([field, messages]) => {
              const input = form.elements[field];
              if (!input) return;
              input.classList.add("is-invalid");
              const fieldError = input.closest(".form-field")?.querySelector(".form-field-error");
              if (fieldError) fieldError.textContent = messages[0].message;
            });
          }
          throw new Error(result.error || (result.errors ? "Проверьте данные формы." : "Не удалось отправить заявку. Попробуйте позже."));
        }
        if (requestModal?.open) requestModal.close();
        requestSuccessModal.showModal();
        document.body.classList.add("request-modal-open");
        form.reset();
      } catch (failure) {
        error.textContent = failure.message || "Не удалось отправить заявку. Попробуйте позже.";
        error.hidden = false;
      } finally {
        submit.disabled = false;
      }
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

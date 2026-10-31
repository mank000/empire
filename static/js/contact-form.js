(() => {
  const formatPhone = (value) => {
    const digits = value.replace(/\D/g, "");
    if (!digits) return "";
    const number = (digits.startsWith("7") || digits.startsWith("8") ? digits.slice(1) : digits).slice(0, 10);
    if (!number) return "+7";
    let formatted = `+7 (${number.slice(0, 3)}`;
    if (number.length > 3) formatted += `) ${number.slice(3, 6)}`;
    if (number.length > 6) formatted += `-${number.slice(6, 8)}`;
    if (number.length > 8) formatted += `-${number.slice(8)}`;
    return formatted;
  };

  document.querySelectorAll(".contact-form").forEach((form) => {
    const submit = form.querySelector('[type="submit"]');
    const error = form.querySelector(".form-submit-error");
    const success = form.querySelector(".form-submit-success");
    const phone = form.elements.phone;

    phone.addEventListener("input", () => {
      phone.value = formatPhone(phone.value);
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      if (submit.disabled) return;
      error.hidden = true;
      success.hidden = true;
      form.querySelectorAll(".is-invalid").forEach((input) => input.classList.remove("is-invalid"));
      submit.disabled = true;
      try {
        const response = await fetch(form.action, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-CSRFToken": form.elements.csrfmiddlewaretoken.value,
          },
          body: JSON.stringify({
            name: form.elements.name.value,
            phone: phone.value,
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
          throw new Error(result.error || (response.status === 429 ? "Слишком много заявок. Попробуйте немного позже." : result.errors ? "Проверьте данные формы." : "Не удалось отправить заявку. Попробуйте позже."));
        }

        form.reset();
        const requestModal = document.querySelector("#request-modal");
        const successModal = document.querySelector("#request-success-modal");
        if (successModal) {
          if (requestModal?.open) requestModal.close();
          successModal.showModal();
          document.body.classList.add("request-modal-open");
        } else {
          success.hidden = false;
        }
      } catch (failure) {
        error.textContent = failure.message || "Не удалось отправить заявку. Попробуйте позже.";
        error.hidden = false;
      } finally {
        submit.disabled = false;
      }
    });

    submit.disabled = false;
  });
})();

document.querySelectorAll(".form-field-clear").forEach((button) => {
  const input = button.previousElementSibling;

  button.addEventListener("click", () => {
    input.value = "";
    input.classList.add("is-invalid");
    input.focus();
  });

  input.addEventListener("input", () => input.classList.remove("is-invalid"));
});

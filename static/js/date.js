const date = document.getElementById("date");
const nowDate = new Date();
function updateDate() {
  date.textContent = `DATE / ${nowDate.toLocaleDateString()}`;
}
updateDate();

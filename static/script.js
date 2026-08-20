document.addEventListener("DOMContentLoaded", () => {
  var modeEnr = localStorage.getItem("mode") || "clair";
  var them = document.getElementById("theme");
  if (them) {
    them.href = them.dataset[modeEnr];
  }

  var mode = document.getElementById("mode");
  var them = document.getElementById("theme");
  if (mode && them) {
    mode.checked = (localStorage.getItem("mode") || "sombre") === "sombre";

    mode.addEventListener("change", () => {
      let nouveau = mode.checked ? "sombre" : "clair";
      them.href = them.dataset[nouveau];
      localStorage.setItem("mode", nouveau);
    });
  }
});

const chk = document.getElementById("check");
let role = document.getElementById("rol");
let btn = document.getElementById("btn");
let btn1 = document.getElementById("btn1");
let btn_C = document.getElementById("btn_C");
let btn_I = document.getElementById("btn_I");
let button = document.getElementById("retour");

chk?.addEventListener("click", () => {
  document.getElementById("password").type = chk.checked ? "text" : "password";
});

role?.addEventListener("change", () => {
  document.getElementById("code").style.display =
    role.value == "etudiant" ? "none" : "flex";
});

btn?.addEventListener("click", () => {
  document.getElementById("inscription").style.display = "none";
  document.getElementById("connection").style.display = "flex";
});

btn1?.addEventListener("click", () => {
  document.getElementById("connection").style.display = "none";
  document.getElementById("inscription").style.display = "flex";
});

btn_C?.addEventListener("click", () => {
  document.getElementById("hello").style.display = "none";
  document.getElementById("connection").style.display = "flex";
});
btn_I?.addEventListener("click", () => {
  document.getElementById("hello").style.display = "none";
  document.getElementById("inscription").style.display = "flex";
});

let click = false;
button?.addEventListener("click", () => {
  click = !click;
  if (click) {
    document.getElementById("vi").style.display = "none";
    document.getElementById("even").style.display = "flex";
    button.textContent = "Retour";
  } else {
    document.getElementById("even").style.display = "none";
    document.getElementById("vi").style.display = "block";
    button.textContent = "Evenements";
  }
});

let voir = (id, url) => {
  let zone = document.getElementById("player-" + id);
  let btn = document.getElementById("btn-" + id);
  if (zone.innerHTML != "") {
    zone.innerHTML = "";
    btn.textContent = "Ouvrir";
    return;
  }
  zone.innerHTML = `
<video width ="100%" controls autoplay><source src="${url}">ne supporte pas</video>
`;
  btn.textContent = "Quitter";
};

setInterval(() => {
  const now = new Date();
  const time = now.toLocaleTimeString();
  document.getElementById("clock").innerText = time;
}, 1000);

const cherche = document.getElementById("cherche");
const use = document.querySelectorAll(".user");
cherche?.addEventListener("keyup", () => {
  const q = cherche.value.toLowerCase();
  use.forEach((u) => {
    const texte = u.textContent.toLowerCase();
    if (texte.includes(q)) {
      u.style.display = "";
    } else {
      u.style.display = "none";
    }
  });
});

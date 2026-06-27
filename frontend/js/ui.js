// Мелкие UI-помощники (без фреймворка).
import { tg } from "./api.js";

const WD_SHORT = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];
const MONTHS = [
  "января", "февраля", "марта", "апреля", "мая", "июня",
  "июля", "августа", "сентября", "октября", "ноября", "декабря",
];

// Рекурсивно добавляет детей (узлы/строки/массивы), пропуская null/false.
function addChild(node, c) {
  if (c === null || c === undefined || c === false) return;
  if (Array.isArray(c)) {
    for (const x of c) addChild(node, x);
    return;
  }
  node.append(c.nodeType ? c : document.createTextNode(String(c)));
}

// Гипертекстовый конструктор элементов: h("div", {class:"x", onClick:fn}, [child])
export function h(tag, attrs = {}, children = []) {
  const e = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") e.className = v;
    else if (k === "html") e.innerHTML = v;
    else if (k.startsWith("on") && typeof v === "function")
      e.addEventListener(k.slice(2).toLowerCase(), v);
    else e.setAttribute(k, v === true ? "" : v);
  }
  addChild(e, children);
  return e;
}

export function clear(node) {
  while (node.firstChild) node.removeChild(node.firstChild);
}

export function mount(node, ...children) {
  clear(node);
  addChild(node, children);
  return node;
}

export function toast(msg) {
  if (tg && tg.showAlert) tg.showAlert(String(msg));
  else alert(msg);
}

export function confirmDialog(msg) {
  return new Promise((resolve) => {
    if (tg && tg.showConfirm) tg.showConfirm(String(msg), (ok) => resolve(!!ok));
    else resolve(window.confirm(msg));
  });
}

export function haptic(type = "light") {
  try {
    tg && tg.HapticFeedback && tg.HapticFeedback.impactOccurred(type);
  } catch (_) {}
}

function parseDt(value) {
  // бэкенд отдаёт наивный ISO без зоны — парсим как локальное время
  const d = new Date(value);
  return isNaN(d) ? null : d;
}

export function fmtDate(value) {
  const d = parseDt(value);
  if (!d) return value;
  return `${WD_SHORT[(d.getDay() + 6) % 7]}, ${d.getDate()} ${MONTHS[d.getMonth()]}`;
}

export function fmtTime(value) {
  const d = parseDt(value);
  if (!d) return "";
  return `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
}

export function fmtDateTime(value) {
  return `${fmtDate(value)} · ${fmtTime(value)}`;
}

// Преобразование datetime-local (<input>) <-> ISO для API
export function toIsoLocal(localValue) {
  // localValue = "2026-09-01T18:00" → отдаём как есть (наивное локальное)
  return localValue ? `${localValue}:00` : null;
}

export function isoToLocalInput(iso) {
  if (!iso) return "";
  const d = parseDt(iso);
  if (!d) return "";
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}T${p(d.getHours())}:${p(d.getMinutes())}`;
}

export function loading(node, text = "Загрузка…") {
  mount(node, h("div", { class: "loader" }, text));
}

export function errorBox(node, err) {
  mount(node, h("div", { class: "empty err" }, String(err && err.message ? err.message : err)));
}

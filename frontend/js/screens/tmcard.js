// F6 — карточка тайм-менеджмента: контент + мини-задание.
import { api } from "../api.js";
import { h, mount } from "../ui.js";
import { MODULE } from "./tm.js";

export async function render(view, app, params) {
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  let card;
  try {
    const cards = await api.tm();
    card = cards.find((c) => c.id === params.id);
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }
  if (!card) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty" }, "Карточка не найдена")));
    return;
  }

  const m = MODULE[card.module] || MODULE.horizons;
  let answer = card.answer || "";

  const btn = h("button", {
    class: "btn btn--block",
    style: "margin-top:20px;",
    onClick: async () => {
      btn.disabled = true;
      try {
        await api.completeCard(card.id, answer);
        app.toast("Отмечено как пройдено!");
        app.back();
      } catch (e) {
        btn.disabled = false;
        app.toast(e.message, "err");
      }
    },
  }, card.completed ? "Сохранить ответ" : "Отметить пройденной");

  mount(view, h("div", { class: "screen" }, [
    h("div", { class: "center fade", style: "padding-top:8px;display:flex;flex-direction:column;align-items:center;" }, [
      h("div", { class: "avatar", style: `width:80px;height:80px;border-radius:24px;font-size:40px;background:${m.soft};animation:popIn .5s both;` }, m.icon),
      h("div", { style: `font-size:12px;font-weight:700;letter-spacing:.06em;text-transform:uppercase;color:${m.accent};margin-top:14px;` }, card.completed ? "Пройдено" : "Тайм-менеджмент"),
      h("h1", { style: "margin:6px 0 0;" }, card.title),
    ]),
    h("p", { style: "margin:20px 2px 0;font-size:16px;line-height:1.55;white-space:pre-line;" }, card.content),
    h("div", { style: `margin-top:20px;border-radius:16px;border:1.5px dashed ${m.accent};padding:16px;background:${m.soft};` }, [
      h("div", { style: `font-size:13px;font-weight:700;color:${m.accent};margin-bottom:10px;` }, "✍️ Мини-задание"),
      h("div", { style: "font-size:14.5px;font-weight:600;margin-bottom:12px;" }, card.task),
      h("textarea", { style: "background:var(--cell);border:none;", placeholder: "Твой ответ…", value: answer, onInput: (e) => (answer = e.target.value) }),
    ]),
    btn,
  ]));
}

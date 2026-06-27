// F6 — хаб тайм-менеджмента: hero + список карточек.
import { api } from "../api.js";
import { h, mount } from "../ui.js";

export const MODULE = {
  horizons: { icon: "🗺️", soft: "rgba(91,141,239,.14)", accent: "#5B8DEF" },
  goals: { icon: "🎯", soft: "rgba(52,199,89,.14)", accent: "#34C759" },
};

export async function render(view, app) {
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  let cards;
  try {
    cards = await api.tm();
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }
  const done = cards.filter((c) => c.completed).length;

  mount(view, h("div", { class: "screen" }, [
    h("div", { class: "hero hero--tm rise", style: "position:relative;" }, [
      h("div", { style: "position:absolute;right:-20px;top:-20px;font-size:110px;opacity:.16;" }, "🧭"),
      h("div", { style: "font-size:13px;font-weight:600;opacity:.9;" }, "Программа тайм-менеджмента"),
      h("div", { style: "font-size:21px;font-weight:800;margin-top:6px;max-width:80%;" }, "Две карточки, чтобы взять время под контроль"),
      h("div", { style: "font-size:13.5px;opacity:.92;margin-top:8px;" }, `Пройдено ${done} из ${cards.length}`),
    ]),
    h("div", { class: "stack", style: "margin-top:16px;" },
      cards.map((c, i) => {
        const m = MODULE[c.module] || MODULE.horizons;
        return h("button", {
          class: "cell-tap rise",
          style: `display:flex;align-items:center;gap:14px;width:100%;text-align:left;background:var(--cell);border:none;border-radius:16px;box-shadow:var(--shadow);padding:16px;font-family:inherit;color:var(--text);animation-delay:${i * 90}ms;`,
          onClick: () => app.go("tmcard", { id: c.id }),
        }, [
          h("span", { class: "avatar", style: `width:50px;height:50px;border-radius:14px;font-size:25px;background:${m.soft};` }, m.icon),
          h("div", { class: "grow" }, [
            h("div", { style: "font-size:16.5px;font-weight:700;" }, c.title),
            h("div", { class: "muted small", style: "margin-top:2px;" }, `Карточка ${i + 1} из ${cards.length}`),
          ]),
          h("span", { class: c.completed ? "tag" : "muted small", style: c.completed ? "background:var(--greenSoft);color:var(--green);" : "" }, c.completed ? "✓ пройдено" : "›"),
        ]);
      })
    ),
  ]));
}

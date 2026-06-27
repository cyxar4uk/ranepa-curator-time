// F8 — кабинет организатора: список своих мероприятий.
import { api } from "../api.js";
import { h, mount, fmtDate, fmtTime } from "../ui.js";
import { eventVisual } from "../theme.js";

const STATUS = {
  published: { label: "опубликовано", bg: "var(--greenSoft)", color: "var(--green)" },
  moderation: { label: "на модерации", bg: "var(--orangeSoft)", color: "var(--orange)" },
  draft: { label: "черновик", bg: "var(--cell2)", color: "var(--text2)" },
};

export async function render(view, app) {
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  let events;
  try {
    events = await api.myEvents();
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }
  const totalReg = events.reduce((s, e) => s + e.registered_count, 0);

  mount(view, h("div", { class: "screen" }, [
    h("div", { class: "hero hero--green rise", style: "position:relative;" }, [
      h("div", { style: "position:absolute;right:-16px;top:-16px;font-size:96px;opacity:.16;" }, "📣"),
      h("div", { style: "font-size:13px;font-weight:600;opacity:.92;" }, "Кабинет организатора"),
      h("div", { style: "font-size:21px;font-weight:800;margin-top:5px;" }, `${events.length} мероприятий · ${totalReg} записей`),
    ]),
    h("button", { class: "btn btn--block", style: "margin-top:16px;", onClick: () => app.go("orgnew", {}) }, "＋ Добавить мероприятие"),
    h("div", { class: "section-title" }, "Мои мероприятия"),
    events.length
      ? h("div", { class: "stack" }, events.map((ev, i) => card(ev, i, app)))
      : h("div", { class: "empty" }, [h("div", { class: "em" }, "📣"), h("b", {}, "Пока нет мероприятий"), h("p", { class: "muted small" }, "Создай первое — кнопка выше.")]),
  ]));
}

function card(ev, i, app) {
  const v = eventVisual(ev);
  const s = STATUS[ev.status] || STATUS.draft;
  return h("div", { class: "card rise", style: `padding:14px 15px;animation-delay:${i * 60}ms;` }, [
    h("div", { class: "row", style: "gap:12px;" }, [
      h("span", { class: "avatar", style: `width:44px;height:44px;border-radius:12px;font-size:22px;background:${v.soft};` }, v.emoji),
      h("div", { class: "grow", style: "min-width:0;" }, [
        h("div", { style: "font-size:15.5px;font-weight:700;line-height:1.25;" }, ev.title),
        h("div", { class: "muted small", style: "margin-top:2px;" }, `${fmtDate(ev.starts_at)}, ${fmtTime(ev.starts_at)}`),
      ]),
      h("span", { class: "tag", style: `background:${s.bg};color:${s.color};` }, s.label),
    ]),
    h("div", { class: "row", style: "gap:10px;margin-top:13px;padding-top:13px;border-top:1px solid var(--sep);" }, [
      h("div", { class: "grow row", style: "gap:8px;" }, [
        h("span", { style: "font-size:22px;font-weight:800;color:var(--accent);font-variant-numeric:tabular-nums;" }, String(ev.registered_count)),
        h("span", { class: "muted small" }, ev.capacity != null ? `записались из ${ev.capacity}` : "записались"),
      ]),
      h("button", { class: "btn btn--ghost tap", style: "padding:9px 16px;font-size:13.5px;", onClick: () => app.go("orgnew", { id: ev.id }) }, "Редактировать"),
    ]),
  ]);
}

// F3/F4 — лента мероприятий: фильтр по интересам/все, теги, rich-карточки с ценностью.
import { api } from "../api.js";
import { h, mount, fmtDate, fmtTime } from "../ui.js";
import { eventVisual, tagIcon } from "../theme.js";

const state = { mode: "interests", tagId: null, tags: null };

export async function render(view, app) {
  if (state.tags === null) {
    try { state.tags = await api.tags(); } catch (_) { state.tags = []; }
  }

  const list = h("div", {});
  const screen = h("div", { class: "screen" }, [
    seg(),
    tagBar(),
    list,
  ]);
  mount(view, screen);
  load();

  function seg() {
    const mk = (mode, label) =>
      h("button", { class: state.mode === mode ? "active" : "", onClick: () => { state.mode = mode; state.tagId = null; render(view, app); } }, label);
    return h("div", { class: "seg", style: "margin-bottom:12px;" }, [mk("interests", "По интересам"), mk("all", "Все")]);
  }

  function tagBar() {
    if (!state.tags.length) return h("div", {});
    return h("div", { class: "chips chips--scroll", style: "margin-bottom:14px;" },
      state.tags.map((t) =>
        h("button", {
          class: "chip tap" + (state.tagId === t.id ? " selected" : ""),
          onClick: () => { state.tagId = state.tagId === t.id ? null : t.id; render(view, app); },
        }, [h("span", {}, tagIcon(t.name)), t.name])
      )
    );
  }

  async function load() {
    mount(list, h("div", { class: "loader" }, "Загрузка…"));
    try {
      const events = await api.events({ byInterests: state.mode === "interests", tagIds: state.tagId ? [state.tagId] : [] });
      if (!events.length) {
        mount(list, h("div", { class: "empty fade" }, [
          h("div", { class: "em" }, "🔍"),
          h("b", {}, "Ничего не нашлось"),
          h("p", { class: "muted small" }, state.mode === "interests" ? "По интересам пока пусто — загляни во вкладку «Все»." : "Попробуй убрать фильтр по тегу."),
        ]));
        return;
      }
      mount(list, h("div", { class: "stack" }, events.map((ev, i) => card(ev, i))));
    } catch (e) {
      mount(list, h("div", { class: "empty err" }, e.message));
    }
  }

  function card(ev, i) {
    const v = eventVisual(ev);
    const btn = h("button", {
      class: "btn " + (ev.is_registered ? "btn--registered" : ""),
      style: "flex:1;",
      onClick: async (e) => {
        e.stopPropagation();
        try {
          if (ev.is_registered) { await api.cancel(ev.id); ev.is_registered = false; app.toast("Запись отменена", "info"); }
          else { const r = await api.register(ev.id); ev.is_registered = true; app.toast(r.conflict ? r.conflict.message : "Записал(а)!", r.conflict && r.conflict.level === "class" ? "info" : "ok"); }
          load();
        } catch (err) { app.toast(err.message, "err"); }
      },
    }, ev.is_registered ? "✓ Вы записаны" : "Записаться");

    const spots = ev.capacity != null ? `${ev.capacity - ev.registered_count}` : `${ev.registered_count}`;
    const spotsLbl = ev.capacity != null ? "мест" : "идут";

    return h("div", { class: "card card--pad0 rise", style: `animation-delay:${i * 70}ms;` }, [
      h("button", { class: "cell-tap", style: "display:block;width:100%;text-align:left;border:none;background:transparent;padding:0;font-family:inherit;color:var(--text);", onClick: () => app.go("event", { id: ev.id }) }, [
        h("div", { class: "row", style: "gap:13px;padding:15px 16px 12px;" }, [
          h("span", { class: "avatar", style: `width:50px;height:50px;border-radius:14px;font-size:25px;background:${v.soft};` }, v.emoji),
          h("div", { class: "grow", style: "min-width:0;" }, [
            h("div", { style: "font-size:16.5px;font-weight:700;letter-spacing:-.01em;line-height:1.25;" }, ev.title),
            h("div", { class: "muted small", style: "margin-top:3px;" }, (ev.tags[0] ? ev.tags[0].name : "Мероприятие")),
          ]),
        ]),
        h("div", { class: "row", style: "gap:8px;padding:0 16px 12px;flex-wrap:wrap;" }, [
          h("span", { style: "display:flex;align-items:center;gap:5px;font-size:13px;font-weight:600;background:var(--cell2);padding:6px 11px;border-radius:9px;" }, `🗓️ ${fmtDate(ev.starts_at)}, ${fmtTime(ev.starts_at)}`),
          ev.location ? h("span", { class: "muted", style: "display:flex;align-items:center;gap:5px;font-size:13px;background:var(--cell2);padding:6px 11px;border-radius:9px;" }, `📍 ${ev.location}`) : null,
          fitPill(ev.conflict),
        ]),
        valueBlock(ev, v),
      ]),
      h("div", { class: "row", style: "gap:12px;padding:0 16px 15px;" }, [
        btn,
        h("div", { style: "text-align:right;flex-shrink:0;" }, [
          h("div", { style: "font-size:13px;font-weight:700;font-variant-numeric:tabular-nums;" }, spots),
          h("div", { class: "muted", style: "font-size:11px;" }, spotsLbl),
        ]),
      ]),
    ]);
  }
}

function fitPill(c) {
  if (!c) return null;
  const map = {
    free: ["var(--greenSoft)", "var(--green)", "✅ впишется в окно"],
    protected: ["var(--orangeSoft)", "var(--orange)", "🛡 защищённый час"],
    class: ["var(--redSoft)", "var(--red)", "⚠️ пересекается с парой"],
  };
  const m = map[c.level];
  if (!m) return null;
  return h("span", { style: `display:flex;align-items:center;gap:5px;font-size:12.5px;font-weight:600;padding:6px 11px;border-radius:9px;background:${m[0]};color:${m[1]};` }, m[2]);
}

function valueBlock(ev, v) {
  const rows = [];
  if (ev.value.skill) rows.push(["🧠", ev.value.skill]);
  if (ev.value.points) rows.push(["⭐", `+${ev.value.points} баллов в рейтинг`]);
  if (ev.value.portfolio) rows.push(["📁", ev.value.portfolio]);
  if (!rows.length) return h("div", {});
  return h("div", { class: "value", style: `margin:0 12px 12px;background:${v.soft};` }, [
    h("div", { class: "value__title", style: `color:${v.color};` }, "Зачем идти"),
    ...rows.map(([em, txt]) =>
      h("div", { class: "row", style: "gap:9px;margin-top:8px;" }, [h("span", { style: "font-size:15px;" }, em), h("span", { style: "font-size:13.5px;font-weight:500;" }, txt)])
    ),
  ]);
}

export { valueBlock };

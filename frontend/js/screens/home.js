// Главная — хаб действия: сводка + «Впишется в твоё окно» (запись прямо тут).
import { api } from "../api.js";
import { h, mount, fmtDate, fmtTime } from "../ui.js";
import { eventVisual } from "../theme.js";

const WD_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const mins = (t) => (+t.slice(0, 2)) * 60 + (+t.slice(3, 5));
const fmtH = (m) => {
  const r = Math.round((m / 60) * 2) / 2;
  return (Number.isInteger(r) ? r : r.toString().replace(".5", "½")) + " ч";
};

const SLOT = {
  free: { bg: "var(--greenSoft)", color: "var(--green)", ic: "🟢", lbl: "Свободное окно" },
  protected: { bg: "var(--orangeSoft)", color: "var(--orange)", ic: "🛡", lbl: "Защищённый час" },
};

export async function render(viewEl, app) {
  mount(viewEl, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  let week, events, tm;
  try {
    [week, events, tm] = await Promise.all([
      api.week(),
      api.events({ byInterests: true }).catch(() => []),
      api.tm().catch(() => []),
    ]);
  } catch (e) {
    mount(viewEl, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }

  let totalFree = 0;
  week.days.forEach((d) => d.free.forEach((f) => (totalFree += mins(f.end) - mins(f.start))));
  let protectedLabel = null;
  for (const d of week.days) {
    if (d.protected.length) { protectedLabel = `${WD_SHORT[d.weekday]} ${d.protected[0].start}–${d.protected[0].end}`; break; }
  }
  const matched = (events || [])
    .filter((e) => e.conflict && (e.conflict.level === "free" || e.conflict.level === "protected") && !e.is_registered)
    .slice(0, 4);
  const tmDone = (tm || []).filter((c) => c.completed).length;
  const tmTotal = (tm || []).length || 2;

  const reload = () => render(viewEl, app);

  const blocks = [
    // hero — идентичность + ценность
    h("div", { class: "hero rise" }, [
      h("div", { style: "font-size:13px;font-weight:600;opacity:.9;" }, `Привет${app.me.full_name ? ", " + app.me.full_name.split(" ")[0] : ""}!`),
      h("div", { class: "row", style: "align-items:baseline;gap:8px;margin-top:8px;" }, [
        h("span", { class: "hero__big" }, fmtH(totalFree).replace(" ч", "")),
        h("span", { style: "font-size:16px;font-weight:600;opacity:.92;" }, "свободных часов на неделе"),
      ]),
      h("div", { style: "font-size:13.5px;opacity:.9;margin-top:6px;" },
        week.has_group ? `группа ${week.group_name || ""}` : "укажи группу, чтобы увидеть окна и подбор"),
    ]),
  ];

  if (!week.has_group) {
    blocks.push(h("button", { class: "btn btn--soft btn--block", style: "margin-top:14px;", onClick: () => app.go("settings") }, "Указать группу"));
  } else {
    // защищённый час — одной строкой
    if (protectedLabel)
      blocks.push(h("button", {
        class: "banner banner--warn tap", style: "margin-top:14px;width:100%;text-align:left;", onClick: () => app.go("hours", {}, { tab: true }),
      }, [
        h("span", { class: "badge-ico" }, "🛡️"),
        h("div", { class: "grow" }, [
          h("div", { style: "font-size:14.5px;font-weight:700;" }, `Защищённый час · ${protectedLabel}`),
          h("div", { class: "sub muted", style: "font-size:12.5px;" }, "это время никто не займёт парами"),
        ]),
        h("span", { class: "muted", style: "font-size:18px;" }, "›"),
      ]));

    // ГЛАВНОЕ: что впишется в окно
    blocks.push(
      h("div", { class: "row row--between", style: "margin:24px 2px 4px;align-items:baseline;" }, [
        h("span", { class: "section-title", style: "margin:0;" }, "Впишется в твоё окно"),
        h("button", { class: "tap", style: "border:none;background:none;color:var(--accent);font-size:13.5px;font-weight:600;", onClick: () => app.go("feed", {}, { tab: true }) }, "Вся лента ›"),
      ]),
      h("p", { class: "muted small", style: "margin:0 2px 14px;" }, "Мероприятия по интересам, которые попадают в свободное время — без пересечений с парами."),
    );

    if (matched.length) {
      blocks.push(h("div", { class: "stack" }, matched.map((ev, i) => matchCard(ev, app, reload, i))));
    } else {
      blocks.push(h("div", { class: "card center", style: "padding:28px 18px;" }, [
        h("div", { style: "font-size:40px;animation:floatY 4s ease-in-out infinite;" }, "🗓️"),
        h("b", { style: "display:block;font-size:15px;margin-top:10px;" }, (events || []).length ? "Ты записан на всё, что подходит" : "Пока нет мероприятий по интересам"),
        h("p", { class: "muted small", style: "margin-top:6px;" }, "Загляни в полную ленту — там есть события и по другим направлениям."),
        h("button", { class: "btn btn--soft", style: "margin-top:14px;", onClick: () => app.go("feed", {}, { tab: true }) }, "Открыть ленту"),
      ]));
    }

    // быстрый доступ к окнам недели
    blocks.push(h("button", {
      class: "row-cell cell-tap", style: "margin-top:18px;border:1px solid var(--sep);border-radius:14px;background:var(--cell);", onClick: () => app.go("hours", {}, { tab: true }),
    }, [
      h("span", { class: "ico" }, "🕒"),
      h("span", { class: "grow" }, "Все свободные окна на неделе"),
      h("span", { class: "chev" }, "›"),
    ]));
  }

  // нудж по тайм-менеджменту
  if (tmDone < tmTotal) {
    blocks.push(h("button", {
      class: "row-cell cell-tap", style: "margin-top:10px;border:1px solid var(--sep);border-radius:14px;background:var(--cell);", onClick: () => app.go("tm", {}, { tab: true }),
    }, [
      h("span", { class: "ico" }, "🧭"),
      h("div", { class: "grow" }, [
        h("div", { style: "font-weight:500;" }, "Тайм-менеджмент"),
        h("div", { class: "muted small" }, `пройдено ${tmDone} из ${tmTotal} — закрепи навык`),
      ]),
      h("span", { class: "chev" }, "›"),
    ]));
  }

  mount(viewEl, h("div", { class: "screen" }, blocks));
}

function matchCard(ev, app, reload, i) {
  const v = eventVisual(ev);
  const slot = SLOT[ev.conflict.level] || SLOT.free;
  const points = ev.value && ev.value.points
    ? h("span", { style: `font-size:11.5px;font-weight:700;color:${v.color};background:${v.soft};padding:2px 7px;border-radius:6px;` }, `⭐ +${ev.value.points}`)
    : null;

  const btn = h("button", { class: "btn btn--block", style: "margin:0 14px 13px;width:auto;", onClick: async (e) => {
    e.stopPropagation();
    btn.disabled = true;
    try {
      const r = await api.register(ev.id);
      app.toast(r.conflict ? r.conflict.message : "Записал(а)!");
      reload();
    } catch (err) { btn.disabled = false; app.toast(err.message, "err"); }
  } }, "Записаться");

  return h("div", { class: "card card--pad0 rise", style: `animation-delay:${i * 70}ms;` }, [
    h("div", { class: "row", style: `gap:7px;padding:9px 14px;background:${slot.bg};` }, [
      h("span", { style: "font-size:13px;" }, slot.ic),
      h("span", { style: `font-size:12.5px;font-weight:700;color:${slot.color};` }, `${slot.lbl} · ${fmtDate(ev.starts_at)}, ${fmtTime(ev.starts_at)}`),
    ]),
    h("button", { class: "cell-tap", style: "display:flex;align-items:center;gap:13px;width:100%;text-align:left;border:none;background:transparent;padding:13px 14px 12px;font-family:inherit;color:var(--text);", onClick: () => app.go("event", { id: ev.id }) }, [
      h("span", { class: "avatar", style: `width:46px;height:46px;border-radius:13px;font-size:23px;background:${v.soft};` }, v.emoji),
      h("div", { class: "grow", style: "min-width:0;" }, [
        h("div", { style: "font-size:15.5px;font-weight:700;line-height:1.25;" }, ev.title),
        h("div", { class: "row", style: "gap:8px;margin-top:3px;align-items:center;" }, [
          h("span", { class: "muted small" }, ev.tags[0] ? ev.tags[0].name : "Мероприятие"),
          points,
        ]),
      ]),
    ]),
    btn,
  ]);
}

// Вкладка «Часы»: исследование свободных окон недели в трёх видах.
import { api } from "../api.js";
import { h, mount } from "../ui.js";

const WD_SHORT = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];
const COLORS = { class: "#9aa3ad", protected: "var(--orange)", free: "var(--green)" };
const SOFT = { class: "var(--cell2)", protected: "var(--orangeSoft)", free: "var(--greenSoft)" };
const FG = { class: "var(--text2)", protected: "var(--orange)", free: "var(--green)" };
const ICON = { class: "📚", protected: "🛡", free: "🟢" };

const ui = { variant: "bars" }; // запоминается между заходами

const mins = (t) => (+t.slice(0, 2)) * 60 + (+t.slice(3, 5));
const fmtH = (m) => {
  const r = Math.round((m / 60) * 2) / 2;
  return (Number.isInteger(r) ? r : r.toString().replace(".5", "½")) + " ч";
};
const pad2 = (n) => String(n).padStart(2, "0");

export async function render(viewEl, app) {
  mount(viewEl, h("div", { class: "screen" }, h("div", { class: "loader" }, "Считаем свободные часы…")));
  let week;
  try {
    week = await api.week();
  } catch (e) {
    mount(viewEl, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }

  if (!week.has_group) {
    mount(viewEl, h("div", { class: "screen" }, h("div", { class: "empty" }, [
      h("div", { class: "em" }, "🕒"),
      h("b", {}, "Группа не выбрана"),
      h("p", { class: "muted small" }, "Укажи группу в профиле, чтобы увидеть свободные окна."),
      h("button", { class: "btn btn--soft", style: "margin-top:14px;", onClick: () => app.go("settings") }, "Указать группу"),
    ])));
    return;
  }

  const dayStart = mins(week.day_start), dayEnd = mins(week.day_end);
  const span = Math.max(1, dayEnd - dayStart);
  let totalFree = 0;
  week.days.forEach((d) => d.free.forEach((f) => (totalFree += mins(f.end) - mins(f.start))));
  let selected = 0;

  const combined = (day) => {
    const it = [];
    day.busy.forEach((b) => it.push({ start: b.start, end: b.end, title: b.title || "Пара", kind: "class" }));
    day.protected.forEach((p) => it.push({ start: p.start, end: p.end, title: p.title || "Внеучебный час", kind: "protected" }));
    day.free.forEach((f) => it.push({ start: f.start, end: f.end, title: "Свободно", kind: "free" }));
    return it.sort((a, b) => a.start.localeCompare(b.start));
  };
  const stateAt = (day, m) => {
    for (const b of day.busy) if (m >= mins(b.start) && m < mins(b.end)) return "class";
    for (const p of day.protected) if (m >= mins(p.start) && m < mins(p.end)) return "protected";
    for (const f of day.free) if (m >= mins(f.start) && m < mins(f.end)) return "free";
    return null;
  };
  const legend = () => h("div", { class: "legend" }, [
    h("span", {}, [h("i", { style: `background:${COLORS.free}` }), "свободно"]),
    h("span", {}, [h("i", { style: `background:${COLORS.class}` }), "пары"]),
    h("span", {}, [h("i", { style: `background:${COLORS.protected}` }), "защищённый час"]),
  ]);

  const variantWrap = h("div", {});
  const detailWrap = h("div", { style: "margin-top:14px;" });

  function bars() {
    const wrap = h("div", {});
    const card = h("div", { class: "card", style: "padding:16px 12px 12px;" }, [
      h("div", { class: "weekbars" }, week.days.map((day, idx) => {
        const segs = [];
        const place = (s, e, c) => segs.push(h("div", { class: "weekbars__seg", style: `bottom:${((mins(s) - dayStart) / span) * 100}%;height:${((mins(e) - mins(s)) / span) * 100}%;background:${c};` }));
        day.free.forEach((f) => place(f.start, f.end, COLORS.free));
        day.busy.forEach((b) => place(b.start, b.end, COLORS.class));
        day.protected.forEach((p) => place(p.start, p.end, COLORS.protected));
        const freeMin = day.free.reduce((s, f) => s + (mins(f.end) - mins(f.start)), 0);
        return h("button", { class: "weekbars__day tap", onClick: () => { selected = idx; drawDetail(); [...card.querySelectorAll(".weekbars__col")].forEach((c, i) => c.classList.toggle("sel", i === idx)); } }, [
          h("div", { class: "weekbars__col" + (idx === selected ? " sel" : "") }, segs),
          h("span", { class: "weekbars__lbl" + (day.is_today ? " today" : "") }, WD_SHORT[day.weekday]),
          h("span", { class: "weekbars__h" }, fmtH(freeMin)),
        ]);
      })),
      legend(),
    ]);
    mount(wrap, [card, detailWrap]);
    drawDetail();
    return wrap;
  }
  function drawDetail() {
    const day = week.days[selected];
    mount(detailWrap, [
      h("div", { style: "font-size:14px;font-weight:700;margin:0 4px 10px;" }, `${day.weekday_name}${day.is_today ? " · сегодня" : ""}`),
      h("div", { class: "stack" }, combined(day).map((s) =>
        h("div", { class: "dayslot" }, [
          h("span", { class: "barv", style: `background:${COLORS[s.kind]}` }),
          h("div", { class: "grow" }, [
            h("b", {}, s.kind === "free" ? "Свободное окно" : s.kind === "protected" ? `🛡 ${s.title}` : s.title),
            h("div", { class: "sub" }, s.kind === "free" ? "можно занять мероприятием" : s.kind === "protected" ? "гарантированное внеучебное время" : "занятие группы"),
          ]),
          h("span", { class: "time" }, `${s.start}–${s.end}`),
        ])
      )),
    ]);
  }
  function timeline() {
    return h("div", { class: "stack" }, week.days.map((day) => {
      const freeMin = day.free.reduce((s, f) => s + (mins(f.end) - mins(f.start)), 0);
      return h("div", { class: "card card--pad0 rise" }, [
        h("div", { class: "row row--between", style: "padding:12px 15px;border-bottom:1px solid var(--sep);" }, [
          h("span", { style: "font-size:15px;font-weight:700;" }, day.weekday_name + (day.is_today ? " · сегодня" : "")),
          h("span", { class: "tag", style: "background:var(--greenSoft);color:var(--green);" }, `${fmtH(freeMin)} свободно`),
        ]),
        h("div", { style: "padding:6px 8px 8px;" }, combined(day).map((s) =>
          h("div", { class: "row", style: "gap:11px;padding:8px;" }, [
            h("span", { style: "font-size:12px;font-weight:700;color:var(--text2);width:42px;font-variant-numeric:tabular-nums;" }, s.start),
            h("span", { class: "grow", style: `height:30px;border-radius:8px;background:${SOFT[s.kind]};display:flex;align-items:center;padding:0 12px;font-size:13px;font-weight:600;color:${FG[s.kind]};gap:7px;` }, [ICON[s.kind], s.kind === "free" ? "Свободно" : s.title]),
          ])
        )),
      ]);
    }));
  }
  function heatmap() {
    const startH = Math.floor(dayStart / 60), endH = Math.ceil(dayEnd / 60);
    const hours = [];
    for (let hh = startH; hh < endH; hh++) hours.push(hh);
    const cells = [h("span", {})];
    week.days.forEach((d) => cells.push(h("span", { style: `text-align:center;font-size:11px;font-weight:700;color:${d.is_today ? "var(--accent)" : "var(--text2)"};` }, WD_SHORT[d.weekday])));
    hours.forEach((hh) => {
      cells.push(h("span", { style: "font-size:10.5px;font-weight:700;color:var(--text2);display:flex;align-items:center;justify-content:flex-end;padding-right:4px;font-variant-numeric:tabular-nums;" }, pad2(hh)));
      week.days.forEach((d) => {
        const stt = stateAt(d, hh * 60 + 30);
        cells.push(h("button", {
          class: "tap",
          title: `${WD_SHORT[d.weekday]} ${pad2(hh)}:00`,
          style: `height:22px;border:none;border-radius:5px;background:${stt ? COLORS[stt] : "var(--cell2)"};display:flex;align-items:center;justify-content:center;font-size:10px;`,
          onClick: () => app.toast(`${d.weekday_name} ${pad2(hh)}:00 — ${stt === "free" ? "свободное окно" : stt === "class" ? "пара" : stt === "protected" ? "защищённый час" : "вне расписания"}`, stt === "class" ? "info" : "ok"),
        }, stt === "protected" ? "🛡" : ""));
      });
    });
    return h("div", { class: "card", style: "padding:14px 12px 12px;overflow-x:auto;" }, [
      h("div", { style: "display:grid;grid-template-columns:30px repeat(7,1fr);gap:4px;min-width:280px;align-items:center;" }, cells),
      legend(),
    ]);
  }

  function drawVariant() {
    mount(variantWrap, (ui.variant === "timeline" ? timeline : ui.variant === "heatmap" ? heatmap : bars)());
  }

  const VARIANTS = [["bars", "Столбики"], ["timeline", "Таймлайн"], ["heatmap", "Сетка"]];
  const toggle = h("div", { class: "seg", style: "margin:0 2px 14px;" },
    VARIANTS.map(([key, label]) => h("button", { class: ui.variant === key ? "active" : "", onClick: () => {
      ui.variant = key;
      [...toggle.children].forEach((b, i) => b.classList.toggle("active", VARIANTS[i][0] === key));
      drawVariant();
    } }, label))
  );

  mount(viewEl, h("div", { class: "screen" }, [
    h("div", { class: "card", style: "background:linear-gradient(150deg,var(--accent2),var(--accent));color:#fff;border:none;" }, [
      h("div", { class: "row", style: "align-items:baseline;gap:8px;" }, [
        h("span", { style: "font-size:34px;font-weight:800;letter-spacing:-.02em;" }, fmtH(totalFree).replace(" ч", "")),
        h("span", { style: "font-size:15px;font-weight:600;opacity:.92;" }, "свободных часов на неделе"),
      ]),
      h("div", { style: "font-size:13px;opacity:.9;margin-top:4px;" }, `группа ${week.group_name || ""} · окно дня ${week.day_start}–${week.day_end}`),
    ]),
    h("div", { class: "section-title" }, "Вид"),
    toggle,
    variantWrap,
  ]));
  drawVariant();
}

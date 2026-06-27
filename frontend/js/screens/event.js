// F4/F5 — карточка мероприятия: ценность, проверка пересечений, запись.
import { api } from "../api.js";
import { h, mount, fmtDate, fmtTime } from "../ui.js";
import { eventVisual } from "../theme.js";

const FLAG = {
  class: { ico: "⚠️", title: "Пересекается с парой" },
  protected: { ico: "🛡", title: "Защищённый час" },
  free: { ico: "✅", title: "Свободное окно" },
  unknown: { ico: "❔", title: "Не проверено" },
};

export async function render(view, app, params) {
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  let ev;
  try {
    ev = await api.event(params.id);
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }
  draw(ev, ev.conflict);

  async function doRegister(conflict) {
    try {
      const r = await api.register(ev.id);
      ev = await api.event(ev.id);
      draw(ev, r.conflict || conflict);
      app.toast(r.conflict ? r.conflict.message : "Записал(а)!", r.conflict && r.conflict.level === "class" ? "info" : "ok");
    } catch (e) {
      app.toast(e.message, "err");
    }
  }

  function confirmRegister() {
    const c = ev.conflict || { level: "free", message: "Свободное окно" };
    const meta = FLAG[c.level] || FLAG.unknown;
    const iconBg = c.level === "class" ? "var(--redSoft)" : c.level === "protected" ? "var(--orangeSoft)" : "var(--greenSoft)";
    app.sheet({
      icon: meta.ico,
      iconBg,
      title: c.message || meta.title,
      detail: (c.details && c.details.join(" · ")) || "Подтвердить запись на мероприятие?",
      confirmLabel: c.level === "class" ? "Всё равно записаться" : "Записаться",
      onConfirm: () => doRegister(c),
    });
  }

  async function doCancel() {
    try {
      await api.cancel(ev.id);
      ev = await api.event(ev.id);
      draw(ev);
      app.toast("Запись отменена", "info");
    } catch (e) {
      app.toast(e.message, "err");
    }
  }

  function draw(ev, conflict) {
    const v = eventVisual(ev);
    const metaRows = [
      ["🗓️", "Когда", `${fmtDate(ev.starts_at)}, ${fmtTime(ev.starts_at)}–${fmtTime(ev.ends_at)}`],
      ev.location ? ["📍", "Где", ev.location] : null,
      ev.organizer_name ? ["👤", "Организатор", ev.organizer_name] : null,
    ].filter(Boolean);

    const valRows = [];
    if (ev.value.skill) valRows.push(["🧠", "Навык", ev.value.skill]);
    if (ev.value.points) valRows.push(["⭐", `+${ev.value.points} баллов`, "в рейтинг активности"]);
    if (ev.value.portfolio) valRows.push(["📁", "Портфолио", ev.value.portfolio]);

    const c = conflict || ev.conflict;
    const flag = c
      ? h("div", { class: `flag flag--${c.level}`, style: "margin-top:18px;animation:popIn .4s both;" }, [
          h("span", { class: "fico" }, (FLAG[c.level] || FLAG.unknown).ico),
          h("div", {}, [
            h("b", {}, c.message),
            (c.details && c.details.length) ? h("div", { class: "sub" }, c.details.join(" · ")) : null,
          ]),
        ])
      : null;

    const spots = ev.capacity != null ? `${Math.max(0, ev.capacity - ev.registered_count)}` : `${ev.registered_count}`;
    const actionBtn = ev.is_registered
      ? h("button", { class: "btn btn--danger", style: "flex:1;", onClick: doCancel }, "Отменить запись")
      : h("button", { class: "btn", style: "flex:1;", onClick: confirmRegister }, "Записаться");

    const screen = h("div", { class: "screen screen--flush" }, [
      h("div", { class: "evhead", style: `background:linear-gradient(150deg,${v.color},${v.dark});` }, h("span", { class: "em" }, v.emoji)),
      h("div", { style: "padding:18px 18px 90px;" }, [
        ev.tags[0] ? h("div", { style: `font-size:13px;font-weight:600;color:${v.color};` }, ev.tags[0].name) : null,
        h("h1", { style: "margin:6px 0 0;line-height:1.18;" }, ev.title),
        h("div", { class: "meta", style: "margin-top:16px;" },
          metaRows.map((m) => h("div", { class: "meta__row" }, [
            h("span", { class: "ico" }, m[0]),
            h("span", { class: "lbl" }, m[1]),
            h("span", { class: "val" }, m[2]),
          ]))
        ),
        valRows.length
          ? h("div", { class: "value", style: `margin-top:16px;background:${v.soft};` }, [
              h("div", { class: "value__title", style: `color:${v.color};` }, "Ценность · зачем идти"),
              ...valRows.map((r) => h("div", { class: "value__row" }, [
                h("span", { class: "em" }, r[0]),
                h("div", {}, [h("b", {}, r[1]), r[2] ? h("div", { class: "sub" }, r[2]) : null]),
              ])),
            ])
          : null,
        ev.description ? h("p", { style: "margin:18px 4px 0;font-size:15px;line-height:1.55;" }, ev.description) : null,
        h("div", { class: "section-title", style: "margin:22px 2px 10px;" }, "Проверка пересечений"),
        flag,
        ev.is_registered && ev.my_conflict_note ? h("p", { class: "muted small", style: "margin-top:8px;" }, "При записи: " + ev.my_conflict_note) : null,
      ]),
      // sticky action bar
      h("div", { class: "actionbar", style: "position:sticky;bottom:0;" }, [
        h("div", { class: "spots" }, [h("b", {}, spots), h("span", {}, ev.capacity != null ? "мест свободно" : "уже идут")]),
        actionBtn,
      ]),
    ]);
    mount(view, screen);
  }
}

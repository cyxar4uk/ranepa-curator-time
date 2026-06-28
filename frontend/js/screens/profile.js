// Профиль: аватар, статистика, интересы, переходы (редактирование/кураторы/роли).
import { api } from "../api.js";
import { h, mount } from "../ui.js";
import { tagIcon } from "../theme.js";

const ROLE_LABEL = { student: "Первокурсник", organizer: "Организатор", admin: "Администратор" };

export async function render(view, app) {
  const me = app.me || {};
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));

  let tmDone = 0, tmTotal = 2, regCount = 0, freeH = "—";
  try {
    const [tm, week, events] = await Promise.all([
      api.tm().catch(() => []),
      api.week().catch(() => null),
      api.events({ byInterests: false, includePast: true }).catch(() => []),
    ]);
    tmDone = tm.filter((c) => c.completed).length;
    tmTotal = tm.length || 2;
    regCount = events.filter((e) => e.is_registered).length;
    if (week) {
      let m = 0;
      week.days.forEach((d) => d.free.forEach((f) => (m += (+f.end.slice(0, 2) * 60 + +f.end.slice(3)) - (+f.start.slice(0, 2) * 60 + +f.start.slice(3)))));
      freeH = Math.round(m / 60);
    }
  } catch (_) {}

  const rows = [
    { icon: "✏️", label: "Редактировать профиль", to: "settings" },
    { icon: "💬", label: "Кураторы отделения", to: "contacts" },
  ];
  if (me.role === "organizer" || me.role === "admin") rows.push({ icon: "📣", label: "Кабинет организатора", to: "organizer" });
  if (me.role === "admin") rows.push({ icon: "🛠️", label: "Админка", to: "admin" });

  mount(view, h("div", { class: "screen" }, [
    h("div", { class: "center rise", style: "display:flex;flex-direction:column;align-items:center;" }, [
      h("div", { class: "avatar", style: "width:88px;height:88px;border-radius:50%;font-size:38px;color:#fff;background:linear-gradient(150deg,var(--accent2),var(--accent));box-shadow:0 12px 26px -10px var(--accentSoft);" }, "🎓"),
      h("div", { style: "font-size:21px;font-weight:800;margin-top:12px;" }, ROLE_LABEL[me.role] || me.role),
      h("div", { class: "muted", style: "font-size:14px;margin-top:2px;" }, [me.department && me.department.name, me.group && me.group.name].filter(Boolean).join(" · ") || "профиль не заполнен"),
    ]),
    h("div", { class: "row", style: "gap:10px;margin-top:18px;" }, [
      stat(regCount, "записей", "var(--accent)"),
      stat(`${tmDone}/${tmTotal}`, "ТМ-карточки", "var(--green)"),
      stat(freeH, "своб. часов", "var(--orange)"),
    ]),
    me.interests && me.interests.length ? h("div", { class: "section-title" }, "Интересы") : null,
    me.interests && me.interests.length
      ? h("div", { class: "chips" }, me.interests.map((t) => h("span", { class: "chip" }, [h("span", {}, tagIcon(t.name)), t.name])))
      : null,
    h("div", { class: "list", style: "margin-top:22px;" },
      rows.map((r) =>
        h("button", { class: "row-cell cell-tap", onClick: () => app.go(r.to) }, [
          h("span", { class: "ico" }, r.icon),
          h("span", { class: "grow" }, r.label),
          h("span", { class: "chev" }, "›"),
        ])
      )
    ),
    h("div", { class: "muted small center", style: "margin-top:18px;" }, "Telegram ID: " + me.tg_id),
  ]));
}

function stat(value, label, color) {
  return h("div", { class: "stat rise" }, [
    h("b", { style: `color:${color};` }, String(value)),
    h("span", {}, label),
  ]);
}

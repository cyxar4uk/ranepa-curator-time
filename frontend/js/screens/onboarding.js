// F1 — онбординг: приветствие → отделение → группа → интересы → цель → согласие.
import { api } from "../api.js";
import { h, mount } from "../ui.js";
import { tagIcon } from "../theme.js";

const STEPS = ["welcome", "dept", "group", "interests", "goal", "consent"];
const BULLETS = [
  { icon: "🕒", text: "Покажу твои свободные часы на неделю" },
  { icon: "🎯", text: "Соберу мероприятия по твоим интересам" },
  { icon: "💡", text: "На каждом — польза: навык, баллы, портфолио" },
];
const GOAL_SUGGESTIONS = [
  "найти команду для проекта",
  "прокачать публичные выступления",
  "удержать повышенную стипендию",
];

export async function render(view, app) {
  const me = app.me || {};
  const st = {
    step: 0,
    deptId: me.department ? me.department.id : null,
    groupId: me.group ? me.group.id : null,
    interests: new Set((me.interests || []).map((t) => t.id)),
    goal: me.goal || "",
    consent: false,
    departments: [],
    groups: [],
    tags: [],
    saving: false,
  };

  mount(view, h("div", { class: "loader" }, "Загрузка…"));
  try {
    const [departments, tags] = await Promise.all([api.departments(), api.tags()]);
    st.departments = departments;
    st.tags = tags;
  } catch (e) {
    mount(view, h("div", { class: "empty err" }, e.message));
    return;
  }
  draw();

  function canNext() {
    const cur = STEPS[st.step];
    if (cur === "dept") return !!st.deptId;
    if (cur === "group") return !!st.groupId;
    if (cur === "interests") return st.interests.size > 0;
    if (cur === "consent") return st.consent;
    return true;
  }

  async function next() {
    const cur = STEPS[st.step];
    if (!canNext()) return;
    if (cur === "consent") return save();
    if (cur === "dept") {
      try {
        st.groups = await api.groups(st.deptId);
      } catch (_) {
        st.groups = [];
      }
    }
    st.step += 1;
    draw();
  }

  function prev() {
    if (st.step > 0) st.step -= 1;
    draw();
  }

  async function save() {
    st.saving = true;
    draw();
    try {
      await api.updateProfile({
        group_id: Number(st.groupId),
        interest_ids: [...st.interests],
        goal: st.goal,
        consent: true,
      });
      app.toast("Профиль создан — добро пожаловать!");
      await app.reload();
    } catch (e) {
      st.saving = false;
      draw();
      app.toast(e.message, "err");
    }
  }

  function deptName() {
    const d = st.departments.find((x) => x.id === st.deptId);
    return d ? d.name : "";
  }

  function draw() {
    const cur = STEPS[st.step];
    const progress = Math.round(((st.step + 1) / STEPS.length) * 100);

    const top = h("div", { class: "row", style: "padding:16px 16px 6px;gap:12px;" }, [
      st.step > 0
        ? h("button", { class: "tap", style: "width:30px;height:30px;border:none;background:none;color:var(--accent);font-size:24px;", onClick: prev }, "‹")
        : null,
      h("div", { class: "progressbar" }, h("i", { style: `width:${progress}%` })),
      h("span", { class: "small muted", style: "min-width:34px;text-align:right;" }, `${st.step + 1}/${STEPS.length}`),
    ]);

    const body = h("div", { style: "flex:1;overflow-y:auto;padding:8px 20px 20px;" }, [stepBody(cur)]);

    const cta = h("div", { style: "padding:12px 20px calc(18px + env(safe-area-inset-bottom));background:linear-gradient(0deg,var(--bg) 70%,transparent);" }, [
      h("button", { class: "btn btn--block", disabled: st.saving || !canNext(), onClick: next },
        cur === "consent" ? (st.saving ? "Создаём…" : "Создать профиль") : "Далее"),
    ]);

    mount(view, h("div", { style: "position:absolute;inset:0;display:flex;flex-direction:column;background:var(--bg);" }, [top, body, cta]));
  }

  function stepBody(cur) {
    if (cur === "welcome")
      return h("div", { class: "fade center", style: "padding-top:30px;display:flex;flex-direction:column;align-items:center;" }, [
        h("div", { style: "width:96px;height:96px;border-radius:28px;background:linear-gradient(155deg,var(--accent2),var(--accent));display:flex;align-items:center;justify-content:center;font-size:46px;animation:floatY 4s ease-in-out infinite;" }, "🧭"),
        h("h1", { style: "margin:26px 0 0;font-size:27px;" }, "Школа кураторов"),
        h("p", { class: "muted", style: "max-width:300px;margin-top:14px;" }, "Привет! За одну сессию помогу разобраться во внеучебке: покажу свободные часы, ценные мероприятия и помогу записаться."),
        h("div", { class: "stack", style: "margin-top:30px;width:100%;" },
          BULLETS.map((b) =>
            h("div", { class: "row rise", style: "background:var(--cell);border-radius:14px;padding:13px 15px;box-shadow:var(--shadow);text-align:left;" }, [
              h("span", { style: "font-size:22px;" }, b.icon),
              h("span", { style: "font-size:14.5px;font-weight:500;" }, b.text),
            ])
          )
        ),
      ]);

    if (cur === "dept")
      return h("div", { class: "fade" }, [
        h("h1", {}, "Твоё отделение"),
        h("p", { class: "muted", style: "margin-bottom:20px;" }, "Выбери, где ты учишься — подберём расписание и кураторов."),
        h("div", { class: "stack" },
          st.departments.map((d) =>
            h("button", {
              class: "tap row",
              style: `background:var(--cell);border:1.5px solid ${st.deptId === d.id ? "var(--accent)" : "var(--sep)"};border-radius:14px;padding:13px;width:100%;`,
              onClick: () => { st.deptId = d.id; st.groupId = null; draw(); },
            }, [
              h("span", { class: "avatar", style: "width:40px;height:40px;border-radius:11px;background:var(--accentSoft);font-size:20px;" }, "🎓"),
              h("span", { class: "grow", style: "text-align:left;font-size:16px;font-weight:600;" }, d.name),
              st.deptId === d.id ? h("span", { style: "color:var(--accent);font-weight:800;" }, "✓") : null,
            ])
          )
        ),
      ]);

    if (cur === "group")
      return h("div", { class: "fade" }, [
        h("h1", {}, "Твоя группа"),
        h("p", { class: "muted", style: "margin-bottom:20px;" }, `${deptName()} · выбери группу.`),
        h("div", { style: "display:grid;grid-template-columns:1fr 1fr;gap:10px;" },
          st.groups.length
            ? st.groups.map((g) =>
                h("button", {
                  class: "tap",
                  style: `border:1.5px solid ${st.groupId === g.id ? "var(--accent)" : "var(--sep)"};background:${st.groupId === g.id ? "var(--accentSoft)" : "var(--cell)"};color:var(--text);border-radius:13px;padding:14px;font-size:15px;font-weight:700;`,
                  onClick: () => { st.groupId = g.id; draw(); },
                }, g.name)
              )
            : [h("p", { class: "muted small" }, "В этом отделении пока нет групп.")]
        ),
      ]);

    if (cur === "interests")
      return h("div", { class: "fade" }, [
        h("h1", {}, "Что тебе интересно?"),
        h("p", { class: "muted", style: "margin-bottom:20px;" }, "Выбери хотя бы одно — по ним соберём ленту. Можно поменять позже."),
        h("div", { class: "chips" },
          st.tags.map((t) =>
            h("button", {
              class: "chip tap" + (st.interests.has(t.id) ? " selected" : ""),
              onClick: () => { st.interests.has(t.id) ? st.interests.delete(t.id) : st.interests.add(t.id); draw(); },
            }, [h("span", {}, tagIcon(t.name)), t.name])
          )
        ),
      ]);

    if (cur === "goal")
      return h("div", { class: "fade" }, [
        h("h1", {}, "Цель на семестр"),
        h("p", { class: "muted", style: "margin-bottom:16px;" }, "Необязательно — но так куратору проще помочь."),
        h("textarea", { placeholder: "Например: найти команду для проекта и прокачать выступления", value: st.goal, onInput: (e) => (st.goal = e.target.value) }),
        h("div", { class: "chips", style: "margin-top:14px;" },
          GOAL_SUGGESTIONS.map((s) =>
            h("button", { class: "chip tap", style: "border-style:dashed;background:transparent;color:var(--text2);font-weight:500;", onClick: () => { st.goal = s; draw(); } }, "+ " + s)
          )
        ),
      ]);

    // consent
    const rows = [
      { icon: "🎓", label: "Отделение", value: deptName() },
      { icon: "👥", label: "Группа", value: (st.groups.find((g) => g.id === st.groupId) || {}).name || "—" },
      { icon: "🎯", label: "Интересы", value: `${st.interests.size} выбрано` },
    ];
    return h("div", { class: "fade" }, [
      h("h1", {}, "Почти готово"),
      h("p", { class: "muted", style: "margin-bottom:18px;" }, "Проверь данные и дай согласие — без него профиль не сохраним."),
      h("div", { class: "list", style: "margin-bottom:16px;" },
        rows.map((r) =>
          h("div", { class: "meta__row" }, [
            h("span", { class: "ico" }, r.icon),
            h("span", { class: "lbl" }, r.label),
            h("span", { class: "val" }, r.value),
          ])
        )
      ),
      h("button", {
        class: "tap row",
        style: "align-items:flex-start;gap:12px;width:100%;text-align:left;background:var(--cell);border:1px solid var(--sep);border-radius:16px;padding:15px;",
        onClick: () => { st.consent = !st.consent; draw(); },
      }, [
        h("span", { style: `width:24px;height:24px;border-radius:7px;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:14px;color:#fff;background:${st.consent ? "var(--accent)" : "var(--cell2)"};border:1.5px solid ${st.consent ? "var(--accent)" : "var(--sep)"};` }, st.consent ? "✓" : ""),
        h("span", { class: "small muted", style: "line-height:1.45;" }, "Согласен на обработку персональных данных по 152-ФЗ. Хранится только необходимое: группа, интересы, цель и записи. Идентификатор — Telegram ID."),
      ]),
    ]);
  }
}

// F9 — админка: расписание (CSV), модерация, защищённое окно, справочники, роли.
import { api } from "../api.js";
import { h, mount } from "../ui.js";

const WD = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"];

export async function render(view, app) {
  let departments = [];
  try { departments = await api.departments(); } catch (_) {}

  mount(view, h("div", { class: "screen stack" }, [
    importCard(app),
    moderationCard(app),
    protectedCard(app, departments),
    refsCard(app, departments, async () => { departments = await api.departments(); }),
    rolesCard(app),
  ]));
}

function box(title, children) {
  return h("div", { class: "card stack" }, [h("h2", { style: "margin:0;" }, title), ...children]);
}
const field = (label, node) => h("div", {}, [h("label", { class: "field" }, label), node]);

// --- CSV импорт ---
function importCard(app) {
  const file = h("input", { type: "file", accept: ".csv,text/csv" });
  const result = h("div", { class: "muted small" });
  const btn = h("button", {
    class: "btn btn--soft btn--block tap",
    style: "border:1.5px dashed var(--accent);",
    onClick: async () => {
      const f = file.files && file.files[0];
      if (!f) return app.toast("Выбери CSV-файл", "err");
      btn.disabled = true;
      try {
        const r = await api.importSchedule(f);
        result.innerHTML = `Групп создано: <b>${r.created_groups}</b>, строк: <b>${r.created_rows}</b>, пропущено: <b>${r.skipped}</b>` +
          (r.errors && r.errors.length ? "<br>" + r.errors.slice(0, 8).join("<br>") : "");
        app.toast("Расписание загружено");
      } catch (e) { result.textContent = e.message; app.toast(e.message, "err"); }
      finally { btn.disabled = false; }
    },
  }, "⬆️ Загрузить CSV расписания");
  return box("🗓️ Расписание групп (CSV)", [
    h("p", { class: "muted small" }, "Колонки: group, weekday (0=Пн…6=Вс), start, end, title. Повторная загрузка группы заменяет её расписание."),
    file, btn, result,
  ]);
}

// --- модерация ---
function moderationCard(app) {
  const list = h("div", { class: "stack" }, h("p", { class: "muted small" }, "Загрузка…"));
  async function refresh() {
    try {
      const events = await api.moderationQueue();
      if (!events.length) {
        mount(list, h("div", { class: "center", style: "padding:14px;" }, [h("div", { style: "font-size:30px;" }, "✅"), h("div", { class: "muted small", style: "margin-top:6px;" }, "Заявок нет")]));
        return;
      }
      mount(list, events.map((ev) =>
        h("div", { style: "border:1px solid var(--sep);border-radius:14px;padding:12px;" }, [
          h("div", { style: "font-weight:700;" }, ev.title),
          h("div", { class: "row", style: "gap:9px;margin-top:10px;" }, [
            h("button", { class: "btn btn--green tap", style: "flex:1;padding:10px;font-size:14px;", onClick: () => act(ev.id, true) }, "✓ Опубликовать"),
            h("button", { class: "btn btn--danger tap", style: "padding:10px 16px;font-size:14px;", onClick: () => act(ev.id, false) }, "Отклонить"),
          ]),
        ])
      ));
    } catch (e) { mount(list, h("p", { class: "err small" }, e.message)); }
  }
  async function act(id, approve) {
    try { await api.moderate(id, approve); app.toast(approve ? "Опубликовано" : "Отклонено"); refresh(); }
    catch (e) { app.toast(e.message, "err"); }
  }
  refresh();
  return box("Модерация мероприятий", [list]);
}

// --- защищённое окно ---
function protectedCard(app, departments) {
  const list = h("div", { class: "stack" });
  const f = { department_id: "", weekday: "2", start_time: "13:00", end_time: "14:00", title: "Внеучебный час" };
  async function refresh() {
    try {
      const rows = await api.protectedWindows();
      mount(list, rows.length
        ? rows.map((p) => h("div", { class: "row small", style: "gap:8px;" }, [
            h("span", { class: "tag" }, WD[p.weekday]),
            h("span", {}, `${p.start_time}–${p.end_time}`),
            h("span", { class: "muted" }, p.title + (p.department_id ? "" : " · глобально")),
          ]))
        : h("p", { class: "muted small" }, "Окон пока нет."));
    } catch (e) { mount(list, h("p", { class: "err small" }, e.message)); }
  }
  refresh();
  return box("🛡️ Защищённый час", [
    list,
    field("Отделение (пусто = для всех)",
      h("select", { onChange: (e) => (f.department_id = e.target.value) }, [h("option", { value: "" }, "Все отделения"), ...departments.map((d) => h("option", { value: d.id }, d.name))])),
    field("День недели", h("select", { onChange: (e) => (f.weekday = e.target.value) }, WD.map((w, i) => h("option", { value: i, selected: i === 2 }, w)))),
    h("div", { class: "row", style: "gap:12px;" }, [
      h("div", { class: "grow" }, field("Начало", h("input", { type: "time", value: f.start_time, onInput: (e) => (f.start_time = e.target.value) }))),
      h("div", { class: "grow" }, field("Конец", h("input", { type: "time", value: f.end_time, onInput: (e) => (f.end_time = e.target.value) }))),
    ]),
    field("Название", h("input", { type: "text", value: f.title, onInput: (e) => (f.title = e.target.value) })),
    h("button", { class: "btn btn--block tap", onClick: async () => {
      try { await api.addProtectedWindow({ department_id: f.department_id ? Number(f.department_id) : null, weekday: Number(f.weekday), start_time: f.start_time, end_time: f.end_time, title: f.title }); app.toast("Добавлено"); refresh(); }
      catch (e) { app.toast(e.message, "err"); }
    } }, "Добавить окно"),
  ]);
}

// --- справочники ---
function refsCard(app, departments, onChanged) {
  const dep = h("input", { type: "text", placeholder: "Название отделения" });
  const tag = h("input", { type: "text", placeholder: "Тег / интерес" });
  const grpName = h("input", { type: "text", placeholder: "Группа, напр. ЭМИТ-101" });
  const grpDir = h("input", { type: "text", placeholder: "Направление (необязательно)" });
  const grpDep = h("select", {}, [h("option", { value: "" }, "— отделение —"), ...departments.map((d) => h("option", { value: d.id }, d.name))]);
  const curName = h("input", { type: "text", placeholder: "ФИО куратора" });
  const curContact = h("input", { type: "text", placeholder: "@username / телефон" });
  const curDep = h("select", {}, [h("option", { value: "" }, "— отделение —"), ...departments.map((d) => h("option", { value: d.id }, d.name))]);
  const wrap = async (fn) => { try { await fn(); app.toast("Готово"); } catch (e) { app.toast(e.message, "err"); } };

  return box("Справочники", [
    field("Отделение", dep),
    h("button", { class: "btn btn--ghost btn--block tap", onClick: () => wrap(async () => { await api.adminAddDepartment(dep.value.trim()); dep.value = ""; await onChanged(); }) }, "+ отделение"),
    field("Тег / интерес", tag),
    h("button", { class: "btn btn--ghost btn--block tap", onClick: () => wrap(async () => { await api.adminAddTag(tag.value.trim()); tag.value = ""; }) }, "+ тег"),
    field("Группа", h("div", { class: "stack" }, [grpName, grpDir, grpDep])),
    h("button", { class: "btn btn--ghost btn--block tap", onClick: () => wrap(async () => { await api.adminAddGroup({ name: grpName.value.trim(), direction: grpDir.value.trim() || null, department_id: grpDep.value ? Number(grpDep.value) : null }); grpName.value = ""; }) }, "+ группа"),
    field("Куратор", h("div", { class: "stack" }, [curName, curContact, curDep])),
    h("button", { class: "btn btn--ghost btn--block tap", onClick: () => wrap(async () => { await api.adminAddCurator({ full_name: curName.value.trim(), contact: curContact.value.trim(), department_id: curDep.value ? Number(curDep.value) : null }); curName.value = ""; curContact.value = ""; }) }, "+ куратор"),
  ]);
}

// --- роли ---
function rolesCard(app) {
  const tgId = h("input", { type: "number", placeholder: "Telegram ID" });
  const role = h("select", {}, [h("option", { value: "organizer" }, "Организатор"), h("option", { value: "student" }, "Студент")]);
  return box("Выдать доступ", [
    h("p", { class: "muted small" }, "Telegram ID виден на вкладке «Профиль». Роль admin — только через ADMIN_TG_IDS."),
    field("Telegram ID", tgId),
    field("Роль", role),
    h("button", { class: "btn btn--block tap", onClick: async () => {
      if (!tgId.value) return app.toast("Укажи Telegram ID", "err");
      try { await api.grantRole({ tg_id: Number(tgId.value), role: role.value }); app.toast("Роль выдана"); tgId.value = ""; }
      catch (e) { app.toast(e.message, "err"); }
    } }, "Выдать роль"),
  ]);
}

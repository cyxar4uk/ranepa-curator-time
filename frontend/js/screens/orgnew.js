// F8 — создание/редактирование мероприятия.
import { api } from "../api.js";
import { h, mount, toIsoLocal, isoToLocalInput } from "../ui.js";
import { tagIcon } from "../theme.js";

export async function render(view, app, params) {
  const isEdit = !!(params && params.id);
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));

  let tags = [];
  let ev = null;
  try {
    tags = await api.tags();
    if (isEdit) ev = await api.event(params.id);
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }

  const f = {
    title: ev ? ev.title : "",
    description: ev ? ev.description || "" : "",
    starts_at: ev ? isoToLocalInput(ev.starts_at) : "",
    ends_at: ev ? isoToLocalInput(ev.ends_at) : "",
    location: ev ? ev.location || "" : "",
    tagIds: new Set(ev ? (ev.tags || []).map((t) => t.id) : []),
    value_skill: ev ? ev.value.skill || "" : "",
    value_points: ev ? ev.value.points || "" : "",
    value_portfolio: ev ? ev.value.portfolio || "" : "",
    capacity: ev && ev.capacity != null ? ev.capacity : "",
  };

  app.setHeader({ title: isEdit ? "Редактирование" : "Новое мероприятие", back: true });

  async function submit() {
    const payload = {
      title: f.title.trim(),
      description: f.description.trim() || null,
      starts_at: toIsoLocal(f.starts_at),
      ends_at: toIsoLocal(f.ends_at),
      location: f.location.trim() || null,
      tag_ids: [...f.tagIds],
      value_skill: f.value_skill.trim() || null,
      value_points: Number(f.value_points) || 0,
      value_portfolio: f.value_portfolio.trim() || null,
      capacity: f.capacity === "" ? null : Number(f.capacity),
    };
    if (!payload.title || !payload.starts_at || !payload.ends_at) return app.toast("Заполни название, начало и конец", "err");
    try {
      if (isEdit) { await api.updateEvent(ev.id, payload); app.toast("Сохранено"); }
      else { await api.createEvent(payload); app.toast("Мероприятие создано"); }
      app.back();
    } catch (e) {
      app.toast(e.message, "err");
    }
  }

  const field = (label, node) => h("div", { style: "margin-bottom:16px;" }, [h("label", { class: "field" }, label), node]);
  const inp = (key, attrs = {}) => h("input", { value: f[key], onInput: (e) => (f[key] = e.target.value), ...attrs });

  mount(view, h("div", { class: "screen" }, [
    field("Название", inp("title", { type: "text", placeholder: "Например: Хакатон ЭМИТ" })),
    field("Описание", h("textarea", { placeholder: "Коротко о мероприятии", onInput: (e) => (f.description = e.target.value) }, f.description)),
    h("div", { class: "row", style: "gap:12px;" }, [
      h("div", { class: "grow" }, field("Начало", inp("starts_at", { type: "datetime-local" }))),
      h("div", { class: "grow" }, field("Окончание", inp("ends_at", { type: "datetime-local" }))),
    ]),
    field("Место", inp("location", { type: "text", placeholder: "Корпус, аудитория" })),
    h("label", { class: "field" }, "Теги"),
    h("div", { class: "chips", style: "margin-bottom:16px;" },
      tags.map((t) =>
        h("button", {
          class: "chip tap" + (f.tagIds.has(t.id) ? " selected" : ""),
          onClick: (e) => { f.tagIds.has(t.id) ? f.tagIds.delete(t.id) : f.tagIds.add(t.id); e.currentTarget.classList.toggle("selected"); },
        }, [h("span", {}, tagIcon(t.name)), t.name])
      )
    ),
    h("div", { class: "section-title", style: "margin-top:6px;" }, "Ценность (зачем идти)"),
    field("Какой навык даёт", inp("value_skill", { type: "text", placeholder: "например: публичные выступления" })),
    h("div", { class: "row", style: "gap:12px;" }, [
      h("div", { class: "grow" }, field("Баллы в рейтинг", inp("value_points", { type: "number", min: "0", placeholder: "10" }))),
      h("div", { class: "grow" }, field("Вместимость", inp("capacity", { type: "number", min: "0", placeholder: "30" }))),
    ]),
    field("Что в портфолио", inp("value_portfolio", { type: "text", placeholder: "например: кейс-проект" })),
    h("button", { class: "btn btn--block", style: "margin-top:8px;", onClick: submit }, isEdit ? "Сохранить" : "Создать"),
  ]));
}

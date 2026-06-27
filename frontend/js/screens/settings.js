// Редактирование профиля: отделение / группа / интересы / цель.
import { api } from "../api.js";
import { h, mount } from "../ui.js";
import { tagIcon } from "../theme.js";

export async function render(view, app) {
  const me = app.me || {};
  const st = {
    deptId: me.department ? me.department.id : null,
    groupId: me.group ? me.group.id : null,
    interests: new Set((me.interests || []).map((t) => t.id)),
    goal: me.goal || "",
    departments: [],
    groups: [],
    tags: [],
  };

  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  try {
    const [departments, tags] = await Promise.all([api.departments(), api.tags()]);
    st.departments = departments;
    st.tags = tags;
    if (st.deptId) st.groups = await api.groups(st.deptId);
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }
  draw();

  async function pickDept(id) {
    st.deptId = id;
    st.groupId = null;
    st.groups = await api.groups(id);
    draw();
  }

  async function save() {
    try {
      await api.updateProfile({
        group_id: st.groupId ? Number(st.groupId) : null,
        interest_ids: [...st.interests],
        goal: st.goal,
        consent: true,
      });
      await app.reloadMe();
      app.toast("Сохранено");
      app.back();
    } catch (e) {
      app.toast(e.message, "err");
    }
  }

  function draw() {
    mount(view, h("div", { class: "screen" }, [
      h("label", { class: "field" }, "Отделение"),
      h("div", { class: "stack", style: "margin-bottom:20px;" },
        st.departments.map((d) =>
          h("button", {
            class: "tap row",
            style: `background:var(--cell);border:1.5px solid ${st.deptId === d.id ? "var(--accent)" : "var(--sep)"};border-radius:14px;padding:12px;width:100%;`,
            onClick: () => pickDept(d.id),
          }, [
            h("span", { class: "avatar", style: "width:36px;height:36px;border-radius:10px;background:var(--accentSoft);font-size:18px;" }, "🎓"),
            h("span", { class: "grow", style: "text-align:left;font-weight:600;" }, d.name),
            st.deptId === d.id ? h("span", { style: "color:var(--accent);font-weight:800;" }, "✓") : null,
          ])
        )
      ),
      h("label", { class: "field" }, "Группа"),
      h("div", { style: "display:grid;grid-template-columns:1fr 1fr 1fr;gap:9px;margin-bottom:20px;" },
        st.groups.length
          ? st.groups.map((g) =>
              h("button", {
                class: "tap",
                style: `border:1.5px solid ${st.groupId === g.id ? "var(--accent)" : "var(--sep)"};background:${st.groupId === g.id ? "var(--accentSoft)" : "var(--cell)"};color:var(--text);border-radius:12px;padding:12px 8px;font-weight:700;font-size:14px;`,
                onClick: () => { st.groupId = g.id; draw(); },
              }, g.name)
            )
          : [h("p", { class: "muted small" }, "Сначала выбери отделение.")]
      ),
      h("label", { class: "field" }, "Интересы"),
      h("div", { class: "chips", style: "margin-bottom:20px;" },
        st.tags.map((t) =>
          h("button", {
            class: "chip tap" + (st.interests.has(t.id) ? " selected" : ""),
            onClick: () => { st.interests.has(t.id) ? st.interests.delete(t.id) : st.interests.add(t.id); draw(); },
          }, [h("span", {}, tagIcon(t.name)), t.name])
        )
      ),
      h("label", { class: "field" }, "Цель на семестр"),
      h("textarea", { placeholder: "Чего хочешь добиться?", value: st.goal, onInput: (e) => (st.goal = e.target.value) }),
      h("button", { class: "btn btn--block", style: "margin-top:22px;", onClick: save }, "Сохранить"),
    ]));
  }
}

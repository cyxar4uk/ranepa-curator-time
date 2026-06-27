// F7 — контакты кураторов отделения.
import { api } from "../api.js";
import { h, mount } from "../ui.js";

const SOFT = ["rgba(52,199,89,.14)", "rgba(91,141,239,.14)", "rgba(175,82,222,.14)", "rgba(255,149,0,.15)"];

function contactHref(contact) {
  const c = (contact || "").trim();
  if (c.startsWith("@")) return "https://t.me/" + c.slice(1);
  if (c.startsWith("http")) return c;
  if (/^\+?\d[\d\s()-]+$/.test(c)) return "tel:" + c.replace(/\s/g, "");
  return null;
}

export async function render(view, app) {
  mount(view, h("div", { class: "screen" }, h("div", { class: "loader" }, "Загрузка…")));
  let curators;
  try {
    curators = await api.curators();
  } catch (e) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty err" }, e.message)));
    return;
  }

  if (!curators.length) {
    mount(view, h("div", { class: "screen" }, h("div", { class: "empty" }, [h("div", { class: "em" }, "💬"), h("b", {}, "Контакты пока не добавлены")])));
    return;
  }

  mount(view, h("div", { class: "screen" }, [
    h("p", { class: "muted", style: "margin:0 4px 16px;font-size:14px;" }, "Кураторы — твои проводники во внеучебке. Напиши, если нужна помощь или просто хочется поговорить."),
    h("div", { class: "stack" },
      curators.map((c, i) => {
        const href = contactHref(c.contact);
        return h("div", { class: "card rise", style: `animation-delay:${i * 70}ms;` }, [
          h("div", { class: "row", style: "gap:13px;" }, [
            h("span", { class: "avatar", style: `width:52px;height:52px;border-radius:50%;font-size:24px;background:${SOFT[i % SOFT.length]};` }, "🧑‍🏫"),
            h("div", { class: "grow" }, [
              h("div", { style: "font-size:16.5px;font-weight:700;" }, c.full_name),
              h("div", { class: "muted small", style: "margin-top:1px;" }, [c.note, c.department_name].filter(Boolean).join(" · ")),
            ]),
          ]),
          href
            ? h("a", { class: "btn btn--soft btn--block tap", style: "margin-top:12px;", href, target: "_blank" }, `✈️ Написать ${c.contact}`)
            : h("div", { class: "muted small", style: "margin-top:12px;text-align:center;" }, c.contact),
        ]);
      })
    ),
  ]));
}

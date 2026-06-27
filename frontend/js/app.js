// Бутстрап Mini App: тема, навигация, роутинг, тосты, bottom-sheet.
import { api, tg } from "./api.js";
import { h, mount, clear } from "./ui.js";
import * as onboarding from "./screens/onboarding.js";
import * as home from "./screens/home.js";
import * as hours from "./screens/hours.js";
import * as feed from "./screens/feed.js";
import * as event from "./screens/event.js";
import * as tm from "./screens/tm.js";
import * as tmcard from "./screens/tmcard.js";
import * as contacts from "./screens/contacts.js";
import * as profile from "./screens/profile.js";
import * as settings from "./screens/settings.js";
import * as organizer from "./screens/organizer.js";
import * as orgnew from "./screens/orgnew.js";
import * as admin from "./screens/admin.js";

const headerEl = document.getElementById("header");
const viewEl = document.getElementById("view");
const navEl = document.getElementById("nav");
const overlayEl = document.getElementById("overlay");

const SCREENS = { home, hours, feed, event, tm, tmcard, contacts, profile, settings, organizer, orgnew, admin };

const ROUTE_META = {
  home: { title: "Главная", nav: true },
  hours: { title: "Свободные часы", nav: true },
  feed: { title: "Мероприятия", nav: true },
  tm: { title: "Тайм-менеджмент", nav: true },
  profile: { title: "Профиль", nav: true },
  event: { back: true },
  tmcard: { back: true },
  contacts: { title: "Кураторы", back: true },
  settings: { title: "Редактировать профиль", back: true },
  organizer: { title: "Кабинет организатора", back: true },
  orgnew: { title: "Мероприятие", back: true },
  admin: { title: "Админка", back: true },
};

const NAV = [
  { r: "home", ico: "🏠", l: "Главная" },
  { r: "hours", ico: "🕒", l: "Часы" },
  { r: "feed", ico: "🎯", l: "Лента" },
  { r: "tm", ico: "🧭", l: "ТМ" },
  { r: "profile", ico: "👤", l: "Профиль" },
];
const TOP_OF = {
  event: "feed", tmcard: "tm", contacts: "profile",
  settings: "profile", organizer: "profile", orgnew: "profile", admin: "profile",
};

let backButtonReady = false;

const app = {
  me: null,
  current: "home",
  params: {},
  history: [],
  theme: "light",
  go(route, params = {}, opts = {}) {
    if (opts.tab) app.history = [];
    else app.history.push({ route: app.current, params: app.params });
    app.current = route;
    app.params = params || {};
    render();
  },
  back() {
    const prev = app.history.pop();
    if (prev) {
      app.current = prev.route;
      app.params = prev.params;
    } else {
      app.current = "home";
      app.params = {};
    }
    render();
  },
  async reload() {
    await bootstrap();
  },
  async reloadMe() {
    app.me = await api.me();
  },
  setHeader,
  toast,
  sheet,
  closeSheet,
};

function setHeader({ title = "", sub = "", back = false, action = null } = {}) {
  headerEl.hidden = false;
  clear(headerEl);
  if (back) {
    headerEl.append(
      h("button", { class: "header__back tap", onClick: () => app.back() }, [
        h("span", {}, "‹"),
        "Назад",
      ])
    );
  }
  const t = h("div", { class: "header__title" }, [h("b", {}, title)]);
  if (sub) t.append(h("span", {}, sub));
  headerEl.append(t);
  if (action) {
    headerEl.append(
      h(
        "button",
        {
          class: "tap",
          style:
            "width:34px;height:34px;border:none;border-radius:50%;background:var(--cell2);color:var(--accent);font-size:16px;",
          onClick: action.onTap,
        },
        action.icon
      )
    );
  } else if (back) {
    headerEl.append(h("span", { class: "header__spacer" }));
  }
}

function renderNav(active) {
  navEl.hidden = false;
  clear(navEl);
  for (const item of NAV) {
    navEl.append(
      h("button", { class: "nav__item tap" + (item.r === active ? " active" : ""), onClick: () => app.go(item.r, {}, { tab: true }) }, [
        h("span", { class: "ico" }, item.ico),
        h("span", { class: "lbl" }, item.l),
      ])
    );
  }
}

function toast(msg, type = "ok") {
  const icon = type === "err" ? "⚠️" : type === "info" ? "ℹ️" : "✓";
  const el = h("div", { class: `toast toast--${type}` }, [
    h("span", {}, icon),
    h("span", {}, String(msg)),
  ]);
  overlayEl.append(el);
  setTimeout(() => el.remove(), 2400);
}

function closeSheet() {
  if (app._sheet) {
    app._sheet.forEach((n) => n.remove());
    app._sheet = null;
  }
}

function sheet(opts = {}) {
  closeSheet();
  const backdrop = h("div", { class: "sheet-backdrop", onClick: closeSheet });
  const s = h("div", { class: "sheet" }, [
    h("div", { class: "sheet__grip" }),
    h("div", { class: "center" }, [
      h("div", { class: "sheet__ico", style: `background:${opts.iconBg || "var(--accentSoft)"}` }, opts.icon || "❓"),
      h("div", { style: "font-size:19px;font-weight:800;margin-top:14px;color:var(--text)" }, opts.title || ""),
      opts.detail
        ? h("div", { class: "muted", style: "font-size:14.5px;margin-top:8px;line-height:1.5" }, opts.detail)
        : null,
    ]),
    h(
      "button",
      {
        class: `btn btn--block ${opts.confirmClass || ""}`,
        style: "margin-top:18px",
        onClick: async () => {
          if (opts.onConfirm) await opts.onConfirm();
          closeSheet();
        },
      },
      opts.confirmLabel || "Ок"
    ),
    h(
      "button",
      {
        class: "tap",
        style: "width:100%;margin-top:9px;border:none;background:transparent;color:var(--text2);font-size:15.5px;font-weight:600;padding:13px;border-radius:13px;",
        onClick: closeSheet,
      },
      "Отмена"
    ),
  ]);
  overlayEl.append(backdrop);
  overlayEl.append(s);
  app._sheet = [backdrop, s];
}

function applyTheme() {
  let scheme = "light";
  if (tg && tg.colorScheme) scheme = tg.colorScheme;
  else if (window.matchMedia && matchMedia("(prefers-color-scheme: dark)").matches) scheme = "dark";
  app.theme = scheme;

  const root = document.documentElement;
  root.setAttribute("data-theme", scheme);

  // Подстраиваем поверхности/текст/акцент под ТОЧНУЮ тему пользователя в Telegram.
  // Семантические цвета (green/red/orange) остаются нашими.
  const tp = tg && tg.themeParams ? tg.themeParams : null;
  const s = root.style;
  const set = (name, val) => (val ? s.setProperty(name, val) : s.removeProperty(name));
  set("--bg", tp && tp.bg_color);
  set("--cell", tp && (tp.section_bg_color || tp.secondary_bg_color));
  set("--cell2", tp && tp.secondary_bg_color);
  set("--text", tp && tp.text_color);
  set("--text2", tp && (tp.subtitle_text_color || tp.hint_color));
  set("--hint", tp && tp.hint_color);
  set("--link", tp && tp.link_color);
  set("--accent", tp && tp.button_color);
  set("--accent2", tp && tp.button_color);
  set("--onAccent", tp && tp.button_text_color);
  set("--header", tp && (tp.header_bg_color || tp.secondary_bg_color));
  set("--nav", tp && (tp.bottom_bar_bg_color || tp.secondary_bg_color || tp.bg_color));

  // Синхронизируем хром Telegram (шапка/фон) с темой.
  const fallback = scheme === "dark" ? "#0E1621" : "#EFEFF4";
  try { tg && tg.setBackgroundColor && tg.setBackgroundColor((tp && tp.bg_color) || fallback); } catch (_) {}
  try { tg && tg.setHeaderColor && tg.setHeaderColor((tp && (tp.header_bg_color || tp.secondary_bg_color)) || fallback); } catch (_) {}
}

// Куда открыть приложение сразу (deep-link для админа/организатора):
// ?screen=admin|organizer или start_param из t.me/<bot>?startapp=...
function requestedScreen() {
  let p = "";
  try { p = (tg && tg.initDataUnsafe && tg.initDataUnsafe.start_param) || ""; } catch (_) {}
  if (!p) p = new URLSearchParams(location.search).get("screen") || "";
  return (p || "").toLowerCase();
}

function startScreenFor(me) {
  const want = requestedScreen();
  if (want === "admin" && me.role === "admin") return "admin";
  if ((want === "organizer" || want === "org") && (me.role === "organizer" || me.role === "admin")) return "organizer";
  if (want && (want === "admin" || want === "organizer" || want === "org")) {
    setTimeout(() => toast("Недостаточно прав для этого раздела", "info"), 400);
  }
  return "home";
}

async function render() {
  const meta = ROUTE_META[app.current] || {};
  const screen = SCREENS[app.current] || SCREENS.home;

  setHeader({ title: meta.title || "", back: !!meta.back });
  if (meta.nav) renderNav(app.current);
  else navEl.hidden = true;

  if (tg && tg.BackButton) {
    if (!backButtonReady) {
      tg.BackButton.onClick(() => app.back());
      backButtonReady = true;
    }
    if (meta.back) tg.BackButton.show();
    else tg.BackButton.hide();
  }

  closeSheet();
  mount(viewEl, h("div", { class: "loader" }, "Загрузка…"));
  try {
    await screen.render(viewEl, app, app.params);
  } catch (e) {
    mount(viewEl, h("div", { class: "screen" }, h("div", { class: "empty err" }, (e && e.message) || String(e))));
  }
  viewEl.scrollTop = 0;
}

async function bootstrap() {
  if (tg) {
    try {
      tg.ready();
      tg.expand();
    } catch (_) {}
    if (tg.onEvent) tg.onEvent("themeChanged", applyTheme);
  }
  applyTheme();

  headerEl.hidden = true;
  navEl.hidden = true;
  mount(viewEl, h("div", { class: "loader" }, "Загрузка…"));

  try {
    app.me = await api.me();
  } catch (e) {
    headerEl.hidden = true;
    navEl.hidden = true;
    mount(
      viewEl,
      h("div", { class: "screen" }, h("div", { class: "empty err" }, [
        h("b", {}, "Не удалось авторизоваться"),
        h("p", { class: "small muted" }, (e && e.message) || ""),
        h("p", { class: "small muted" }, "Открой приложение через бота в Telegram."),
      ]))
    );
    return;
  }

  if (!app.me.has_profile) {
    headerEl.hidden = true;
    navEl.hidden = true;
    if (tg && tg.BackButton) tg.BackButton.hide();
    clear(viewEl);
    await onboarding.render(viewEl, app);
    return;
  }

  const start = startScreenFor(app.me);
  app.current = start;
  app.history = start === "home" ? [] : [{ route: "home", params: {} }];
  render();
}

// экспортируем top-of для возможной отладки и единообразия
app.TOP_OF = TOP_OF;
bootstrap();

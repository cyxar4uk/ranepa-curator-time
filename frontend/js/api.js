// Клиент API. Пути ОТНОСИТЕЛЬНЫЕ (резолвятся от <base> — работает и под /curator/).
export const tg = window.Telegram ? window.Telegram.WebApp : null;
const initData = tg && tg.initData ? tg.initData : "";

function devTgId() {
  return new URLSearchParams(location.search).get("dev_tg_id");
}

async function request(method, path, body, isForm = false) {
  const headers = {};
  if (initData) headers["X-Telegram-Init-Data"] = initData;
  const dev = devTgId();
  if (dev) headers["X-Dev-Tg-Id"] = dev;

  const opts = { method, headers };
  if (isForm) {
    opts.body = body;
  } else if (body !== undefined) {
    headers["Content-Type"] = "application/json";
    opts.body = JSON.stringify(body);
  }

  const res = await fetch(path, opts);
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const j = await res.json();
      detail = j.detail || JSON.stringify(j);
    } catch (_) {}
    throw new Error(typeof detail === "string" ? detail : "Ошибка запроса");
  }
  if (res.status === 204) return null;
  const ct = res.headers.get("content-type") || "";
  return ct.includes("application/json") ? res.json() : res.text();
}

function eventsQuery({ byInterests = true, tagIds = [], includePast = false } = {}) {
  const p = new URLSearchParams();
  p.set("by_interests", byInterests ? "true" : "false");
  (tagIds || []).forEach((t) => p.append("tag_id", t));
  if (includePast) p.set("include_past", "true");
  return p.toString();
}

export const api = {
  health: () => request("GET", "api/health"),

  // F1
  me: () => request("GET", "api/me"),
  updateProfile: (d) => request("PUT", "api/profile", d),
  departments: () => request("GET", "api/refs/departments"),
  groups: (depId) =>
    request("GET", depId ? `api/refs/groups?department_id=${depId}` : "api/refs/groups"),
  tags: () => request("GET", "api/refs/tags"),

  // F2
  week: () => request("GET", "api/schedule/week"),

  // F3/F4/F5
  events: (opts) => request("GET", `api/events?${eventsQuery(opts)}`),
  event: (id) => request("GET", `api/events/${id}`),
  register: (id) => request("POST", `api/events/${id}/register`),
  cancel: (id) => request("POST", `api/events/${id}/cancel`),

  // F6
  tm: () => request("GET", "api/tm"),
  completeCard: (id, answer) => request("POST", `api/tm/${id}/complete`, { answer }),

  // F7
  curators: () => request("GET", "api/curators"),

  // F8
  myEvents: () => request("GET", "api/organizer/events"),
  createEvent: (d) => request("POST", "api/organizer/events", d),
  updateEvent: (id, d) => request("PUT", `api/organizer/events/${id}`, d),

  // F9
  adminAddDepartment: (name) => request("POST", "api/admin/departments", { name }),
  adminAddTag: (name) => request("POST", "api/admin/tags", { name }),
  adminAddGroup: (d) => request("POST", "api/admin/groups", d),
  adminAddCurator: (d) => request("POST", "api/admin/curators", d),
  protectedWindows: () => request("GET", "api/admin/protected-windows"),
  addProtectedWindow: (d) => request("POST", "api/admin/protected-windows", d),
  grantRole: (d) => request("POST", "api/admin/grant-role", d),
  moderationQueue: () => request("GET", "api/admin/moderation"),
  moderate: (id, approve) => request("POST", `api/admin/moderation/${id}`, { approve }),
  importSchedule: (file) => {
    const fd = new FormData();
    fd.append("file", file);
    return request("POST", "api/admin/schedule/import", fd, true);
  },
};

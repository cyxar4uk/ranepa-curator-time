// Визуальные соответствия: иконки тегов/интересов и цвета мероприятий.
const TAG_ICONS = {
  "it": "💻", "айти": "💻", "программирование": "💻",
  "дизайн": "🎨", "творчество": "🎨",
  "наука": "🔬", "спорт": "🏀", "волонтёрство": "🤝", "волонтерство": "🤝",
  "бизнес": "📈", "карьера": "🚀", "медиа": "🎬", "музыка": "🎸",
  "дебаты": "🎤", "языки": "🗣️", "soft skills": "🌱", "настолки": "🎲",
};

const PALETTE = [
  { color: "#5B8DEF", dark: "#3A6FD8", soft: "rgba(91,141,239,.14)" },
  { color: "#AF52DE", dark: "#8E3FBD", soft: "rgba(175,82,222,.14)" },
  { color: "#34C759", dark: "#1FA34A", soft: "rgba(52,199,89,.14)" },
  { color: "#FF9500", dark: "#E07F00", soft: "rgba(255,149,0,.15)" },
  { color: "#FF2D55", dark: "#D81E45", soft: "rgba(255,45,85,.13)" },
  { color: "#5856D6", dark: "#3F3EAE", soft: "rgba(88,86,214,.14)" },
  { color: "#007AFF", dark: "#0060CC", soft: "rgba(0,122,255,.13)" },
];

const CATEGORY_EMOJI = {
  "it": "💻", "наука": "🔬", "спорт": "🏀", "творчество": "🎨",
  "волонтёрство": "🤝", "бизнес": "📈", "карьера": "🚀", "медиа": "🎬",
  "языки": "🗣️", "soft skills": "🌱",
};

function hash(str) {
  let h = 0;
  for (let i = 0; i < (str || "").length; i++) h = (h * 31 + str.charCodeAt(i)) | 0;
  return Math.abs(h);
}

export function tagIcon(name) {
  return TAG_ICONS[(name || "").toLowerCase()] || "🏷️";
}

// Стабильная визуальная пара (emoji + цвета) для мероприятия.
export function eventVisual(ev) {
  const firstTag = ev.tags && ev.tags[0] ? ev.tags[0].name : ev.title;
  const emoji =
    CATEGORY_EMOJI[(firstTag || "").toLowerCase()] || tagIcon(firstTag);
  const pal = PALETTE[hash(String(ev.id || ev.title || firstTag)) % PALETTE.length];
  return { emoji, ...pal };
}


// Главная страница: сумма, подписки и карты.
// Все данные берем из API функцией api() из api.js и рисуем на странице.

const $ = (id) => document.getElementById(id);
let cards = []; // карты пользователя, нужны еще и в форме подписки

const periodNames = { month: "раз в месяц", year: "раз в год" };
const kindNames = { rub_card: "российская", foreign_card: "иностранная" };

function money(value) {
  return Number(value).toLocaleString("ru-RU", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(isoDate) {
  return isoDate.split("-").reverse().join("."); // "2026-11-15" -> "15.11.2026"
}

function makeButton(text, onClick) {
  const button = document.createElement("button");
  button.type = "button";
  button.className = "secondary";
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

// Загружаем все с сервера и рисуем заново. Вызываем после любого изменения.
async function loadAll() {
  cards = await api("GET", "/api/payment-methods");
  const subscriptions = await api("GET", "/api/subscriptions");
  const summary = await api("GET", "/api/summary");
  showSummary(summary);
  showSubscriptions(subscriptions);
  showCards();
  fillCardSelect();
}

// ---------- Сумма ----------

function showSummary(summary) {
  $("month-total").textContent = money(summary.month_total_rub) + " ₽";
  $("year-total").textContent = money(summary.year_total_rub) + " ₽";

  let info = "Курсов пока нет, посчитаны только подписки в рублях";
  if (summary.rate_date) {
    info = "По курсу на " + new Date(summary.rate_date).toLocaleString("ru-RU");
  }
  if (summary.is_approx) info += ", примерно, по курсу ЦБ";
  if (summary.is_stale) info += ", курс устарел";
  $("rate-info").textContent = info;
  $("rate-info").className = summary.is_approx || summary.is_stale ? "warning" : "muted";
}

// ---------- Подписки ----------

function showSubscriptions(subscriptions) {
  const tbody = $("subscriptions");
  tbody.innerHTML = "";
  $("no-subscriptions").hidden = subscriptions.length > 0;

  for (const sub of subscriptions) {
    const card = cards.find((c) => c.id === sub.payment_method_id);
    const row = tbody.insertRow();
    if (!sub.is_active) row.className = "paused";

    // Текст ставим через textContent, а не innerHTML: так чужой HTML в названии не выполнится
    const nameCell = row.insertCell();
    if (sub.url) {
      const link = document.createElement("a");
      link.href = sub.url;
      link.target = "_blank";
      link.textContent = sub.name;
      nameCell.append(link);
    } else {
      nameCell.textContent = sub.name;
    }
    row.insertCell().textContent = money(sub.amount) + " " + sub.currency;
    row.insertCell().textContent = sub.price_rub === null ? "нет курса" : money(sub.price_rub) + " ₽";
    row.insertCell().textContent = periodNames[sub.period];
    row.insertCell().textContent = formatDate(sub.next_charge_date) + (sub.is_active ? "" : " (пауза)");
    row.insertCell().textContent = card ? card.name : "";
    row.insertCell().append(
      makeButton("Изменить", () => startEdit(sub)),
      makeButton(sub.is_active ? "Пауза" : "Включить", () => togglePause(sub)),
      makeButton("Удалить", () => deleteSubscription(sub)),
    );
  }
}

async function togglePause(sub) {
  try {
    await api("PATCH", "/api/subscriptions/" + sub.id, { is_active: !sub.is_active });
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
}

async function deleteSubscription(sub) {
  if (!confirm("Удалить подписку «" + sub.name + "»?")) return;
  try {
    await api("DELETE", "/api/subscriptions/" + sub.id);
    await loadAll();
  } catch (error) {
    alert(error.message);
  }
}

// Список карт в форме подписки
function fillCardSelect() {
  const select = $("sub-card");
  const selected = select.value;
  select.innerHTML = "";
  for (const card of cards) {
    select.add(new Option(card.name, card.id));
  }
  if (cards.some((c) => String(c.id) === selected)) select.value = selected;
  $("no-cards").hidden = cards.length > 0;
  fillCurrencySelect();
}

// Российской картой платим только в рублях, иностранной в долларах и евро
function fillCurrencySelect() {
  const card = cards.find((c) => String(c.id) === $("sub-card").value);
  const currencies = card && card.kind === "foreign_card" ? ["USD", "EUR"] : ["RUB"];
  const select = $("sub-currency");
  const selected = select.value;
  select.innerHTML = "";
  for (const currency of currencies) {
    select.add(new Option(currency, currency));
  }
  if (currencies.includes(selected)) select.value = selected;
}

// Кнопка "Изменить": заполняем форму данными подписки
function startEdit(sub) {
  $("sub-id").value = sub.id;
  $("sub-name").value = sub.name;
  $("sub-url").value = sub.url || "";
  $("sub-amount").value = sub.amount;
  $("sub-card").value = sub.payment_method_id;
  fillCurrencySelect();
  $("sub-currency").value = sub.currency;
  $("sub-period").value = sub.period;
  $("sub-date").value = sub.next_charge_date;
  $("sub-form-title").textContent = "Изменить подписку";
  $("sub-cancel").hidden = false;
  $("sub-form").scrollIntoView({ behavior: "smooth" });
}

function resetSubForm() {
  $("sub-form").reset();
  $("sub-id").value = "";
  $("sub-form-title").textContent = "Добавить подписку";
  $("sub-cancel").hidden = true;
  $("sub-error").textContent = "";
  fillCurrencySelect();
}

$("sub-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  if (cards.length === 0) {
    $("sub-error").textContent = "Сначала добавьте карту";
    return;
  }
  const data = {
    name: $("sub-name").value,
    url: $("sub-url").value || null,
    amount: Number($("sub-amount").value),
    currency: $("sub-currency").value,
    period: $("sub-period").value,
    next_charge_date: $("sub-date").value,
    payment_method_id: Number($("sub-card").value),
  };
  const id = $("sub-id").value;
  try {
    if (id) {
      await api("PATCH", "/api/subscriptions/" + id, data);
    } else {
      await api("POST", "/api/subscriptions", data);
    }
    resetSubForm();
    await loadAll();
  } catch (error) {
    $("sub-error").textContent = error.message;
  }
});

$("sub-cancel").addEventListener("click", resetSubForm);
$("sub-card").addEventListener("change", fillCurrencySelect);

// ---------- Карты ----------

function showCards() {
  const list = $("cards");
  list.innerHTML = "";
  for (const card of cards) {
    const item = document.createElement("li");
    let text = card.name + " — " + kindNames[card.kind];
    if (card.kind === "foreign_card") text += ", комиссия пополнения " + card.markup_percent + "%";
    item.textContent = text;
    item.append(makeButton("Удалить", () => deleteCard(card)));
    list.append(item);
  }
}

async function deleteCard(card) {
  if (!confirm("Удалить карту «" + card.name + "»?")) return;
  try {
    await api("DELETE", "/api/payment-methods/" + card.id);
    await loadAll();
  } catch (error) {
    alert(error.message); // например, к карте привязаны подписки
  }
}

$("card-form").addEventListener("submit", async (event) => {
  event.preventDefault();
  try {
    await api("POST", "/api/payment-methods", {
      name: $("card-name").value,
      kind: $("card-kind").value,
      markup_percent: Number($("card-markup").value || 0),
    });
    $("card-form").reset();
    $("card-markup-label").hidden = true;
    $("card-error").textContent = "";
    await loadAll();
  } catch (error) {
    $("card-error").textContent = error.message;
  }
});

// Поле комиссии показываем только для иностранной карты
$("card-kind").addEventListener("change", () => {
  $("card-markup-label").hidden = $("card-kind").value !== "foreign_card";
});

loadAll().catch((error) => alert(error.message));

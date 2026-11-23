
 // Одна функция для всех запросов к API. Подключена на всех страницах в base.html.
 // Пример: const cards = await api("GET", "/api/payment-methods");
 async function api(method, url, data) {
   const options = { method: method, headers: {} };
   if (data !== undefined) {
     options.headers["Content-Type"] = "application/json";
     options.body = JSON.stringify(data);
   }
   const response = await fetch(url, options);

   // Не вошли или вход истек: отправляем на страницу входа
   if (response.status === 401 && !url.startsWith("/api/auth/")) {
     window.location.href = "/login";
     throw new Error("Нужно войти");
   }
   // 204 значит "все хорошо, но отвечать нечем" (например, после удаления)
   if (response.status === 204) {
     return null;
   }
   const body = await response.json().catch(() => ({}));
   if (!response.ok) {
     // Текст ошибки FastAPI кладет в поле detail. Если неправильных полей несколько,
     // там список, и тогда показываем общий текст.
     const message = typeof body.detail === "string" ? body.detail : "Проверьте, что все поля заполнены правильно";
     throw new Error(message);
   }
   return body;
 }

 // Кнопка "Выйти" в шапке есть только у того, кто вошел
 const logoutButton = document.getElementById("logout");
 if (logoutButton) {
   logoutButton.addEventListener("click", async () => {
     await api("POST", "/api/auth/logout");
     window.location.href = "/login";
   });
 }

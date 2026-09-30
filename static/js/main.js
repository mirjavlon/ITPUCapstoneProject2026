document.querySelectorAll("form[data-confirm]").forEach((form) => {
  form.addEventListener("submit", (event) => {
    if (!window.confirm(form.dataset.confirm)) event.preventDefault();
  });
});

document.querySelectorAll(".alert").forEach((alert) => {
  window.setTimeout(() => {
    if (window.bootstrap?.Alert) {
      window.bootstrap.Alert.getOrCreateInstance(alert).close();
    } else {
      alert.remove();
    }
  }, 3000);
});

const interfaceTranslations = {
  uz: {
    "Tournaments": "Turnirlar", "Dashboard": "Boshqaruv paneli", "Sign out": "Chiqish",
    "Manager account": "Menejer hisobi", "Organizer account": "Tashkilotchi hisobi",
    "Mini Football Tournament Management": "Mini futbol turnirlarini boshqarish",
    "Fixtures, results and standings in one place.": "Jadval, natijalar va turnir jadvali bir joyda.",
    "All tournaments": "Barcha turnirlar", "New tournament": "Yangi turnir",
    "ORGANIZER": "TASHKILOTCHI", "TEAM MANAGER": "JAMOA MENEJERI", "DETAILS": "MA’LUMOTLAR",
    "VISIBILITY": "KO‘RINISH", "ROSTER": "TARKIB", "SQUAD": "TARKIB", "CLUBS": "JAMOALAR",
    "MATCH CENTRE": "UCHRASHUVLAR MARKAZI", "PLAYER PERFORMANCE": "O‘YINCHILAR NATIJALARI",
    "Competition setup": "Musobaqa sozlamalari", "Tournament name": "Turnir nomi",
    "Public URL": "Ommaviy URL", "Start date": "Boshlanish sanasi", "End date": "Tugash sanasi",
    "Points system": "Ballar tizimi", "Win": "G‘alaba", "Draw": "Durang", "Loss": "Mag‘lubiyat",
    "Create tournament": "Turnir yaratish", "Save changes": "O‘zgarishlarni saqlash",
    "Draft": "Qoralama", "Keep draft": "Qoralamada qoldirish", "Publish": "Nashr qilish", "Archive": "Arxivlash",
    "Publication status": "Nashr holati", "Start in draft": "Qoralamada boshlang",
    "Team management": "Jamoani boshqarish", "Register team": "Jamoani ro‘yxatdan o‘tkazish",
    "Team information": "Jamoa ma’lumotlari", "Team name": "Jamoa nomi", "Tournament": "Turnir",
    "Choose tournament": "Turnirni tanlang", "Team manager": "Jamoa menejeri",
    "Contact information": "Aloqa ma’lumotlari", "Upload team logo": "Jamoa logotipini yuklash",
    "Logo image URL": "Logotip rasmi URL manzili", "Active team": "Faol jamoa",
    "Register team": "Jamoani ro‘yxatdan o‘tkazish", "View team page": "Jamoa sahifasini ko‘rish",
    "Players": "O‘yinchilar", "Add player": "O‘yinchi qo‘shish", "No players registered.": "O‘yinchilar ro‘yxatdan o‘tmagan.",
    "Remove team": "Jamoani o‘chirish", "Manager access": "Menejer huquqlari",
    "Create organizer account": "Tashkilotchi hisobini yaratish", "Create manager account": "Menejer hisobini yaratish",
    "Username": "Foydalanuvchi nomi", "Email": "E-pochta", "Password": "Parol", "Sign in": "Kirish",
    "Already registered?": "Hisobingiz bormi?", "Incorrect username or password.": "Foydalanuvchi nomi yoki parol noto‘g‘ri.",
    "Teams": "Jamoalar", "Standings": "Turnir jadvali", "Fixtures & results": "Uchrashuvlar va natijalar",
    "Schedule match": "Uchrashuv belgilash", "Edit": "Tahrirlash", "Score": "Hisob", "Correct": "Tuzatish",
    "Goals": "Gollar", "Team": "Jamoa", "Player": "O‘yinchi", "Position": "Pozitsiya",
    "Save player": "O‘yinchini saqlash", "Add to roster": "Tarkibga qo‘shish", "Remove player": "O‘yinchini o‘chirish",
    "Tournament created.": "Turnir yaratildi.", "Tournament details updated.": "Turnir ma’lumotlari yangilandi.",
    "Team registered.": "Jamoa ro‘yxatdan o‘tkazildi.", "Team details updated.": "Jamoa ma’lumotlari yangilandi.",
    "Account created. You can sign in now.": "Hisob yaratildi. Endi kirishingiz mumkin.",
    "Organizer account created. You can sign in now.": "Tashkilotchi hisobi yaratildi. Endi kirishingiz mumkin.",
    "This URL is created automatically and cannot be changed.": "Bu URL avtomatik yaratiladi va o‘zgartirib bo‘lmaydi.",
    "PNG, JPEG, GIF, or WebP. Maximum file size: 5 MB.": "PNG, JPEG, GIF yoki WebP. Maksimal hajm: 5 MB.",
    "If you upload an image, the upload is used instead.": "Rasm yuklasangiz, aynan u ishlatiladi.",
    "COMMUNITY COMPETITIONS": "JAMOATCHILIK MUSOBAQALARI",
    "Tournament board": "Turnirlar doskasi",
    "Check upcoming fixtures, recent results and live league tables.": "Yaqinlashib kelayotgan o‘yinlar, so‘nggi natijalar va jonli liga jadvallarini tekshiring.",
    "Open dashboard": "Boshqaruv panelini ochish",
    "Manage a tournament": "Turnirni boshqarish",
    "LIVE DIRECTORY": "JONLI KATALOG",
    "Published tournaments": "Nashr qilingan turnirlar",
    "active": "faol",
    "Published": "Nashr qilingan",
    "Matches": "Uchrashuvlar",
    "Next fixture": "Keyingi o‘yin",
    "vs": "bilan",
    "No upcoming fixture scheduled": "Hech qanday o‘yin belgilanmagan",
    "View tournament": "Turnirni ko‘rish",
    "No tournaments are published yet": "Hozircha nashr qilingan turnirlar yo‘q",
    "Published competitions will appear here with their fixtures and standings.": "Nashr qilingan musobaqalar bu yerda ularning o‘yinlari va jadvallari bilan ko‘rsatiladi.",
    "Create a tournament": "Turnir yaratish",
    "← All tournaments": "← Barcha turnirlar",
    "Points": "Ballar",
    "Win · Draw · Loss": "G‘alaba · Durang · Mag‘lubiyat",
    "LEAGUE TABLE": "LIGA JADVALI",
    "Pos": "O‘rin",
    "P": "O‘",
    "W": "G‘",
    "D": "D",
    "L": "M",
    "GD": "TF",
    "Pts": "Ochko",
    "No teams registered yet.": "Hozircha jamoalar ro‘yxatdan o‘tmagan.",
    "players": "o‘yinchilar",
    "No teams registered.": "Jamoalar ro‘yxatdan o‘tmagan.",
    "Top scorers": "To‘purarlar",
    "Assists": "Uzatma",
    "Scorers will appear after organizers add goal details to completed matches.": "Tashkilotchilar tugallangan o‘yinlarga gol tafsilotlarini qo‘shgandan so‘ng to‘purarlar ro‘yxati paydo bo‘ladi.",
    "No fixtures yet": "Hozircha o‘yinlar yo‘q",
    "The schedule will appear here when it is published.": "Jadval nashr qilinganda bu yerda paydo bo‘ladi.",
    "scheduled": "belgilangan",
    "completed": "tugallangan",
    "assist:": "uzatma:",
    "TEAM MANAGERS": "JAMOA MENEJERLARI",
    "Keep your roster ready for match day.": "Jamoangizni o‘yin kuniga tayyor holda saqlang.",
    "Create a manager account, register your team, and maintain its player list.": "Menejer hisobini yarating, jamoangizni ro‘yxatdan o‘tkazing va o‘yinchilar ro‘yxatini yuriting.",
    "Create account": "Hisob yaratish",
    "Organizer permissions are assigned separately.": "Tashkilotchi ruxsatlari alohida belgilanadi.",
    "Use at least 8 characters.": "Kamida 8 ta belgidan foydalaning.",
    "TOURNAMENT ORGANIZERS": "TURNIR TASHKILOTCHILARI",
    "Create and run your own competition.": "O‘z musobaqangizni yarating va boshqaring.",
    "Your account can create tournaments and manage the teams, fixtures, results, and players within them.": "Sizning hisobingiz turnirlar yaratishi va ulardagi jamoalar, o‘yinlar, natijalar va o‘yinchilarni boshqarishi mumkin.",
    "Each organizer can manage only tournaments they create.": "Har bir tashkilotchi faqat o‘zi yaratgan turnirlarni boshqarishi mumkin.",
    "MATCH CONTROL": "O‘YINLARNI NAZORAT QILISH",
    "Run the competition from one clear dashboard.": "Musobaqani bitta qulay boshqaruv panelidan boshqaring.",
    "Manage teams, schedule fixtures and publish results without juggling spreadsheets.": "Jadvallar bilan chalkashmasdan jamoalarni boshqaring, o‘yinlarni rejalashtiring va natijalarni nashr qiling.",
    "Use your organizer or team manager account.": "Tashkilotchi yoki jamoa menejeri hisobingizdan foydalaning.",
    "Team manager?": "Jamoa menejerimisiz?",
    "Create an account": "Hisob yaratish",
    "Organizer?": "Tashkilotchimisiz?",
    "Welcome,": "Xush kelibsiz,",
    "Manage competitions, fixtures and official results.": "Musobaqalar, o‘yinlar va rasmiy natijalarni boshqaring.",
    "Manage your teams, player rosters and statistics.": "Jamoalaringiz, o‘yinchilar ro‘yxati va statistikani boshqaring.",
    "COMPETITIONS": "MUSOBAQALAR",
    "Your tournaments": "Sizning turnirlaringiz",
    "Add team →": "Jamoa qo‘shish →",
    "Tournament": "Turnir",
    "Status": "Holati",
    "Dates": "Sanalar",
    "Actions": "Harakatlar",
    "Manage": "Boshqarish",
    "ROSTERS": "TARKIBLAR",
    "Assigned teams": "Biriktirilgan jamoalar",
    "My teams": "Mening jamoalarim",
    "Register team →": "Jamoani ro‘yxatdan o‘tkazish →",
    "No assigned teams": "Biriktirilgan jamoalar yo‘q",
    "Register a team to start building its roster.": "Jamoani ro‘yxatdan o‘tkazing va uning tarkibini shakllantirishni boshlang.",
    "Player statistics": "O‘yinchi statistikasi",
    "View stats": "Statistikani ko‘rish",
    "Add players to see their statistics here.": "Ularning statistikasini bu yerda ko‘rish uchun o‘yinchilarni qo‘shing.",
    "UP NEXT": "KEYINGI O‘YINLAR",
    "Upcoming fixtures": "Yaqinlashib kelayotgan o‘yinlar",
    "Schedule match →": "Uchrashuv belgilash →",
    "No upcoming fixtures": "Yaqinlashib kelayotgan o‘yinlar yo‘q",
    "Schedule a match when teams are ready.": "Jamoalar tayyor bo‘lganda o‘yinni rejalashtiring.",
    "Create your first tournament to begin.": "Boshlash uchun birinchi turniringizni yarating."
  },
  ru: {
    "Tournaments": "Турниры", "Dashboard": "Панель управления", "Sign out": "Выйти",
    "Manager account": "Аккаунт менеджера", "Organizer account": "Аккаунт организатора",
    "Mini Football Tournament Management": "Управление турнирами по мини-футболу",
    "Fixtures, results and standings in one place.": "Расписание, результаты и турнирная таблица в одном месте.",
    "All tournaments": "Все турниры", "New tournament": "Новый турнир",
    "ORGANIZER": "ОРГАНИЗАТОР", "TEAM MANAGER": "МЕНЕДЖЕР КОМАНДЫ", "DETAILS": "СВЕДЕНИЯ",
    "VISIBILITY": "ВИДИМОСТЬ", "ROSTER": "СОСТАВ", "SQUAD": "СОСТАВ", "CLUBS": "КОМАНДЫ",
    "MATCH CENTRE": "ЦЕНТР МАТЧЕЙ", "PLAYER PERFORMANCE": "СТАТИСТИКА ИГРОКОВ",
    "Competition setup": "Настройка соревнования", "Tournament name": "Название турнира",
    "Public URL": "Публичный URL", "Start date": "Дата начала", "End date": "Дата окончания",
    "Points system": "Система очков", "Win": "Победа", "Draw": "Ничья", "Loss": "Поражение",
    "Create tournament": "Создать турнир", "Save changes": "Сохранить изменения",
    "Draft": "Черновик", "Keep draft": "Оставить черновиком", "Publish": "Опубликовать", "Archive": "Архивировать",
    "Publication status": "Статус публикации", "Start in draft": "Начните с черновика",
    "Team management": "Управление командой", "Register team": "Зарегистрировать команду",
    "Team information": "Информация о команде", "Team name": "Название команды", "Tournament": "Турнир",
    "Choose tournament": "Выберите турнир", "Team manager": "Менеджер команды",
    "Contact information": "Контактная информация", "Upload team logo": "Загрузить логотип команды",
    "Logo image URL": "URL изображения логотипа", "Active team": "Активная команда",
    "View team page": "Открыть страницу команды", "Players": "Игроки", "Add player": "Добавить игрока",
    "No players registered.": "Игроки не зарегистрированы.", "Remove team": "Удалить команду", "Manager access": "Доступ менеджера",
    "Create organizer account": "Создать аккаунт организатора", "Create manager account": "Создать аккаунт менеджера",
    "Username": "Имя пользователя", "Email": "Электронная почта", "Password": "Пароль", "Sign in": "Войти",
    "Already registered?": "Уже зарегистрированы?", "Incorrect username or password.": "Неверное имя пользователя или пароль.",
    "Teams": "Команды", "Standings": "Турнирная таблица", "Fixtures & results": "Матчи и результаты",
    "Schedule match": "Назначить матч", "Edit": "Изменить", "Score": "Счёт", "Correct": "Исправить",
    "Goals": "Голы", "Team": "Команда", "Player": "Игрок", "Position": "Позиция",
    "Save player": "Сохранить игрока", "Add to roster": "Добавить в состав", "Remove player": "Удалить игрока",
    "Tournament created.": "Турнир создан.", "Tournament details updated.": "Данные турнира обновлены.",
    "Team registered.": "Команда зарегистрирована.", "Team details updated.": "Данные команды обновлены.",
    "Account created. You can sign in now.": "Аккаунт создан. Теперь вы можете войти.",
    "Organizer account created. You can sign in now.": "Аккаунт организатора создан. Теперь вы можете войти.",
    "This URL is created automatically and cannot be changed.": "Этот URL создаётся автоматически и не может быть изменён.",
    "PNG, JPEG, GIF, or WebP. Maximum file size: 5 MB.": "PNG, JPEG, GIF или WebP. Максимальный размер: 5 МБ.",
    "If you upload an image, the upload is used instead.": "Если вы загрузите изображение, будет использован загруженный файл.",
    "COMMUNITY COMPETITIONS": "ОБЩЕСТВЕННЫЕ СОРЕВНОВАНИЯ",
    "Tournament board": "Турнирная доска",
    "Check upcoming fixtures, recent results and live league tables.": "Смотрите предстоящие матчи, недавние результаты и таблицы лиг.",
    "Open dashboard": "Открыть панель управления",
    "Manage a tournament": "Управление турниром",
    "LIVE DIRECTORY": "ЖИВОЙ КАТАЛОГ",
    "Published tournaments": "Опубликованные турниры",
    "active": "активен",
    "Published": "Опубликован",
    "Matches": "Матчи",
    "Next fixture": "Следующий матч",
    "vs": "против",
    "No upcoming fixture scheduled": "Нет запланированных матчей",
    "View tournament": "Посмотреть турнир",
    "No tournaments are published yet": "Пока нет опубликованных турниров",
    "Published competitions will appear here with their fixtures and standings.": "Опубликованные соревнования появятся здесь с их расписанием и турнирными таблицами.",
    "Create a tournament": "Создать турнир",
    "← All tournaments": "← Все турниры",
    "Points": "Очки",
    "Win · Draw · Loss": "Победа · Ничья · Поражение",
    "LEAGUE TABLE": "ТУРНИРНАЯ ТАБЛИЦА",
    "Pos": "Поз",
    "P": "И",
    "W": "В",
    "D": "Н",
    "L": "П",
    "GD": "РЗГ",
    "Pts": "Очки",
    "No teams registered yet.": "Команды пока не зарегистрированы.",
    "players": "игроки",
    "No teams registered.": "Команды не зарегистрированы.",
    "Top scorers": "Лучшие бомбардиры",
    "Assists": "Голевые передачи",
    "Scorers will appear after organizers add goal details to completed matches.": "Бомбардиры появятся после добавления данных о голах в завершенные матчи.",
    "No fixtures yet": "Пока нет матчей",
    "The schedule will appear here when it is published.": "Расписание появится здесь после его публикации.",
    "scheduled": "запланирован",
    "completed": "завершен",
    "assist:": "голевая передача:",
    "TEAM MANAGERS": "МЕНЕДЖЕРЫ КОМАНД",
    "Keep your roster ready for match day.": "Держите состав готовым к игровому дню.",
    "Create a manager account, register your team, and maintain its player list.": "Создайте аккаунт менеджера, зарегистрируйте команду и ведите список игроков.",
    "Create account": "Создать аккаунт",
    "Organizer permissions are assigned separately.": "Права организатора назначаются отдельно.",
    "Use at least 8 characters.": "Используйте не менее 8 символов.",
    "TOURNAMENT ORGANIZERS": "ОРГАНИЗАТОРЫ ТУРНИРОВ",
    "Create and run your own competition.": "Создайте и проводите собственное соревнование.",
    "Your account can create tournaments and manage the teams, fixtures, results, and players within them.": "Ваш аккаунт может создавать турниры и управлять командами, матчами, результатами и игроками в них.",
    "Each organizer can manage only tournaments they create.": "Каждый организатор может управлять только теми турнирами, которые он создал.",
    "MATCH CONTROL": "КОНТРОЛЬ МАТЧЕЙ",
    "Run the competition from one clear dashboard.": "Управляйте соревнованием из одной удобной панели.",
    "Manage teams, schedule fixtures and publish results without juggling spreadsheets.": "Управляйте командами, планируйте матчи и публикуйте результаты без путаницы в таблицах.",
    "Use your organizer or team manager account.": "Используйте аккаунт организатора или менеджера команды.",
    "Team manager?": "Менеджер команды?",
    "Create an account": "Создать аккаунт",
    "Organizer?": "Организатор?",
    "Welcome,": "Добро пожаловать,",
    "Manage competitions, fixtures and official results.": "Управляйте соревнованиями, матчами и официальными результатами.",
    "Manage your teams, player rosters and statistics.": "Управляйте своими командами, списками игроков и статистикой.",
    "COMPETITIONS": "СОРЕВНОВАНИЯ",
    "Your tournaments": "Ваши турниры",
    "Add team →": "Добавить команду →",
    "Tournament": "Турнир",
    "Status": "Статус",
    "Dates": "Даты",
    "Actions": "Действия",
    "Manage": "Управление",
    "ROSTERS": "СОСТАВЫ",
    "Assigned teams": "Назначенные команды",
    "My teams": "Мои команды",
    "Register team →": "Зарегистрировать команду →",
    "No assigned teams": "Нет назначенных команд",
    "Register a team to start building its roster.": "Зарегистрируйте команду, чтобы начать формировать ее состав.",
    "Player statistics": "Статистика игроков",
    "View stats": "Посмотреть статистику",
    "Add players to see their statistics здесь.": "Добавьте игроков, чтобы увидеть их статистику здесь.",
    "UP NEXT": "СЛЕДУЮЩИЕ",
    "Upcoming fixtures": "Предстоящие матчи",
    "Schedule match →": "Запланировать матч →",
    "No upcoming fixtures": "Нет предстоящих матчей",
    "Schedule a match when teams are ready.": "Запланируйте матч, когда команды будут готовы.",
    "Create your first tournament to begin.": "Создайте свой первый турнир, чтобы начать."
  }
};

const selectedLanguage = document.body.dataset.language;
const translationTable = interfaceTranslations[selectedLanguage];
if (translationTable) {
  const translate = (value) => translationTable[value.trim()] || value.trim();
  const textNodes = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  const nodes = [];
  while (textNodes.nextNode()) nodes.push(textNodes.currentNode);
  nodes.forEach((node) => {
    const text = node.nodeValue;
    const translated = translate(text);
    if (translated !== text.trim()) node.nodeValue = text.replace(text.trim(), translated);
  });
  document.querySelectorAll("[placeholder], [aria-label], [title], [data-confirm]").forEach((element) => {
    ["placeholder", "aria-label", "title", "data-confirm"].forEach((attribute) => {
      if (element.hasAttribute(attribute)) element.setAttribute(attribute, translate(element.getAttribute(attribute)));
    });
  });
}

document.querySelectorAll("[data-match-form]").forEach((form) => {
  const tournamentSelect = form.querySelector("[data-tournament-select]");
  const teamSelects = form.querySelectorAll("[data-team-select]");
  if (!tournamentSelect || !teamSelects.length) return;

  const filterTeams = () => {
    const tournamentId = tournamentSelect.value;
    teamSelects.forEach((select) => {
      Array.from(select.options).forEach((option) => {
        if (!option.value) return;
        option.hidden = option.dataset.tournament !== tournamentId;
        if (option.hidden && option.selected) select.value = "";
      });
    });
  };
  tournamentSelect.addEventListener("change", filterTeams);
  filterTeams();
});

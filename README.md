# Z-Bank Telegram Bot

Полностью переписанный бот на Python 3.13 и aiogram 3.x.

## Запуск

1. Установите зависимости:

```bash
pip install -r requirements.txt
```

2. Создайте `.env` по примеру `.env.example`:

```env
BOT_TOKEN=ваш_токен
STAFF_GROUP_ID=-1001234567890
DATABASE_DIR=database
LEGACY_DATA_PATH=C:\Users\skipi\Downloads\data.json
```

3. Запустите:

```bash
python bot.py
```

## Миграция

При первом запуске бот автоматически создаст JSON-базу и перенесет старый `data.json`, если `database/users.json` пустой.

Порядок поиска старой базы:

1. `LEGACY_DATA_PATH` из `.env`
2. `data.json` рядом с проектом
3. `database/data.json`
4. `C:\Users\skipi\Downloads\data.json`

## Админка

Команда `/panel` работает только в `STAFF_GROUP_ID`. Пользователь должен быть в `database/admins.json` или иметь роль с текстом `Админ`.

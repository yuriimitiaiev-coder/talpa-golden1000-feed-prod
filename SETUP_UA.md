# Налаштування TALPA Golden1000 Filter

## 1. Створення репозиторію

Створіть публічний репозиторій:

`talpa-golden1000-feed`

Не додавайте README, .gitignore або license під час створення.

## 2. Завантаження файлів

Розпакуйте ZIP на комп’ютері. У GitHub натисніть:

`Add file → Upload files`

Завантажте **вміст розпакованої папки**, а не ZIP-файл. У корені репозиторію мають бути видимі:

- `.github`
- `docs`
- `scripts`
- `.gitignore`
- `golden_codes.txt`
- `MANIFEST.txt`
- `README.md`
- `requirements.txt`
- `SETUP_UA.md`

Натисніть `Commit changes`.

## 3. Додавання секретної адреси Dropshipping.ua

Відкрийте:

`Settings → Secrets and variables → Actions → New repository secret`

Створіть секрет:

- Name: `SOURCE_FEED_URL`
- Secret: повна актуальна URL-адреса XML Dropshipping.ua.

Адреса не буде видима відвідувачам репозиторію.

## 4. Увімкнення GitHub Pages

Відкрийте:

`Settings → Pages`

У блоці `Build and deployment` встановіть:

`Source → GitHub Actions`

## 5. Перший запуск

Відкрийте:

`Actions → Build and publish Golden 1000 XML`

Натисніть:

`Run workflow → Run workflow`

Дочекайтеся зеленого статусу для jobs `build` і `deploy`.

## 6. Перевірка результату

Відкрийте:

- `https://yuriimitiaiev-coder.github.io/talpa-golden1000-feed/status.json`
- `https://yuriimitiaiev-coder.github.io/talpa-golden1000-feed/golden1000.xml`

У `status.json` має бути:

- `offers`: 1000;
- `categories`: додатне число;
- `generated_at_utc`: час останнього запуску;
- `sha256`: контрольна сума XML.

## 7. Підключення до Prom

У Prom відкрийте:

`Товари та послуги → Імпорт → Завантажити файл із сервера`

Вставте адресу `golden1000.xml`.

Позначте для оновлення лише:

- Код товару/Артикул;
- Ціна;
- Наявність.

Налаштування праворуч:

- Оновити примусово — вимкнено;
- Завантажити позиції «В наявності» — вимкнено;
- Тільки оновлення — увімкнено;
- товари, яких немає у файлі — Залишити без змін;
- автоматичне оновлення — Раз на 4 години.

Спочатку збережіть налаштування і виконайте один ручний контрольний імпорт. Перевірте звіт і 10 випадкових товарів.

## 8. Обслуговування

Публічні репозиторії GitHub можуть автоматично вимикати scheduled workflows після 60 днів без активності репозиторію. Раз на 1–2 місяці перевіряйте вкладку `Actions`; якщо розклад вимкнено, відкрийте workflow і натисніть `Enable workflow`.

Після зміни складу Golden 1000 оновіть `golden_codes.txt` і запустіть workflow вручну.

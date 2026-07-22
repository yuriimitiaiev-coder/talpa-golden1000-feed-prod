TALPA Golden1000 — патч стійкості до зникнення товарів

Що змінено:
- актуальні товари беруться з поточного XML постачальника;
- якщо Golden-артикул зник із поточного XML, його остання картка береться з docs/golden1000.xml;
- такий товар примусово отримує available="false";
- вихідний XML зберігає рівно 1000 товарів;
- у status.json записуються fresh_offers, fallback_unavailable та missing_codes;
- якщо зникне понад 50 товарів, публікація блокується як аварійна.

Як встановити у GitHub:
1. Відкрити репозиторій talpa-golden1000-feed-prod.
2. Відкрити папку scripts.
3. Натиснути Add file -> Upload files.
4. Завантажити filter_feed.py з цього пакета.
5. Підтвердити заміну наявного scripts/filter_feed.py та натиснути Commit changes.
6. Відкрити Actions -> Build and publish Golden 1000 XML.
7. Запустити Run workflow або Re-run all jobs.

Очікуваний результат для поточного feed 4464.xml:
- offers: 1000
- fresh_offers: 990
- fallback_unavailable: 10
- обидва job build і deploy мають завершитися зеленою галочкою.

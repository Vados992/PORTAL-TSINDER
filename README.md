# PORTAL TSINDER

**Исполняемый исследовательский стенд по архитектуре PORTAL-FA.**

System Architect: **Vadym Tsinderhoz** · Software release **0.1.0**

Этот репозиторий запускает расчёты, симуляции, API, веб-интерфейс, контроллер
математического аналога и журнал экспериментов. Это реальный исполняемый код,
а не псевдокод. **Он не создаёт и не стабилизирует физический портал.**

Исходный документ сам определяет физический geometry actuator как
`NOT_IMPLEMENTED`, а источник, создание устьев и ряд физических gates — как
`UNRESOLVED`. Неизвестные механизмы нельзя реализовать увеличением числа строк.
Полное покрытие каталога L00–L30 и M00–M23 не означает наличие всех solver.
Точные границы каждого слоя указаны в [карте реализации](docs/TRACEABILITY.md).

## Что работает

| Подсистема | Реализованный объём |
|---|---|
| Геометрия | M04: горловина, curvature invariants, stress-energy, NEC, proper distance, embedding, объёмный интеграл |
| Символьный движок | Вывод Christoffel, Riemann, Ricci, Einstein, Kretschmann; Bianchi; M00/M01/M04 |
| Геодезические | RK4, null/timelike, угловой момент, crossing, контроль нормировки |
| Источник/ADM | Формальный ghost scalar Ellis, уравнение поля и статические ADM constraints; без физической допустимости |
| Причинность | Two-route guard с неопределённостями, ковариационный диагностический расчёт, отрицательные циклы графа |
| Волновой solver | Линейное тестовое поле на фиксированной M04, CFL, energy diagnostic, три сетки и точное M00 решение |
| Стабилизация | PID для обычной модели второго порядка, OFF/SAFE/ARMED/RUN/HOLD/CLOSE/LOCKOUT |
| Аварийные сценарии | Потеря измерений, scheduling watchdog, причинный veto, E-STOP, сохранение lockout после restart |
| Метрология | RLGC transmission line, S21, phase unwrap, group delay, CSV и de-embedding |
| Quantum | Трёхкубитная телепортация всех четырёх ветвей, no-signaling diagnostic, depolarizing channel, частная QEI |
| Anchors | HMAC authentication, сроки действия, anti-replay, topology/frame checks, интеграл собственных часов |
| NR bridge | Анализ внешних норм constraints и порядка сходимости CSV; не BSSN solver |
| Приложение | Локальный FastAPI, веб-панель на русском, REST/OpenAPI, CLI, SQLite, отчёты HTML, ZIP bundles |
| Воспроизводимость | Фиксированные версии, unit/integration tests, C++ arithmetic cross-check, CI, Docker recipe |

Python выполняет научные расчёты и сервис; JavaScript/HTML/CSS — интерфейс;
SQL — журнал; C++17 — отдельную реализацию арифметического guard. Дополнительные
языки и внешние кодовые базы не добавлены ради объёма.

## Быстрый запуск

Python **3.11–3.13**. C++ необязателен для приложения; нужен для native test.

```bash
git clone https://github.com/Vados992/PORTAL-TSINDER.git
cd PORTAL-TSINDER
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install --no-deps -e .
python -m portal_tsinder init
python -m portal_tsinder token
python -m portal_tsinder serve
```

Откройте **http://127.0.0.1:8000** и вставьте выведенный командой `token` локальный
токен. Веб-интерфейс хранит его только в памяти текущей страницы. Не публикуйте
токен и каталог `.portal`.

На Windows: `py -3 -m venv .venv`, затем `.venv\Scripts\Activate.ps1` и те же
команды `python`. Также доступны `bash scripts/run.sh` и `scripts/run.ps1`.
Эти скрипты устанавливают зависимости и запускают локальный стенд.

## Один полный воспроизводимый прогон

```bash
python -m unittest discover -s tests -v
python -m portal_tsinder demo --output .portal/demo.json
python -m portal_tsinder list
python -m portal_tsinder verify
```

`demo` выполняет M04, геодезическую, волну, quantum, PID и проверку сходимости.
Каждый запуск сохраняет вход, результат и fingerprint исполняемого Python-пакета.
Численный `PASS` относится только к указанной математической проверке.
**NEC FAIL для M04 — ожидаемый научный результат, а не поломка программы.**

```bash
python -m portal_tsinder run evaluate --config examples/m04.json
python -m portal_tsinder run symbolic --config examples/symbolic-m04.json
python -m portal_tsinder run control --config examples/fault-stale.json
python -m portal_tsinder export RUN_ID .portal/run.zip
python -m portal_tsinder verify-bundle .portal/run.zip
python -m portal_tsinder report RUN_ID .portal/report.html
```

`RUN_ID` замените идентификатором из `list`. Файлы examples являются полными
готовыми конфигурациями. Команды с `--data-dir PATH` задаются перед подкомандой.

## Текущий предел

Не реализованы: создание физической topology и устьев, лабораторный источник
требуемого stress-energy, полная нелинейная Einstein–matter evolution,
state-specific curved-spacetime QEI, самосогласованная semiclassical backreaction,
общий global causality prover, аппаратные драйверы и сертифицированный safety PLC.
Модели каталога без solver возвращают явный статус `CATALOG_ONLY`; результаты
другой модели к ним не приписываются. PA-00–PA-11 никогда не открываются флагами.

Стабилизация в этом выпуске означает стабилизацию **математического аналога**.
Полностью рабочий физический PORTAL по представленным научным данным собрать
невозможно: необходимые законы источника и формирования не заданы.

## Документация

- [Эксплуатация, аварии, резервные копии, Docker](docs/OPERATIONS_RU.md)
- [Математика, области применимости, численные методы](docs/SCIENCE.md)
- [Архитектура, данные, trust boundaries](docs/ARCHITECTURE.md)
- [API и все виды экспериментов](docs/API.md)
- [L00–L30, M00–M23, MOD-01–MOD-12](docs/TRACEABILITY.md)
- [Исправления относительно reference kernel](docs/CORRECTIONS.md)
- [Фактическая проверка выпуска](docs/VALIDATION.md)
- [Лицензия Apache-2.0, сохранённая из исходного репозитория](LICENSE)

Это исследовательский выпуск с проверенным ограниченным объёмом, не сертификат
физической реализуемости и не результат независимой научной репликации.

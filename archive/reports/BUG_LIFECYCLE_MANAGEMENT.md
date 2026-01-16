# Bug Lifecycle Management System

## Проблема которую решаем

**До внедрения системы:**
- ❌ Логи показывают ошибки, которые уже исправлены
- ❌ Невозможно понять актуальное состояние проекта
- ❌ Нет связи между обнаруженной ошибкой и ее исправлением
- ❌ Информация об ошибках разбросана по разным файлам
- ❌ Разработчик вручную создает BUGFIX_*.md файлы
- ❌ Нет отслеживания повторяющихся ошибок

**После внедрения системы:**
- ✅ Единая система отслеживания lifecycle багов
- ✅ Автоматическая регистрация ошибок из production
- ✅ Связь между обнаружением → исправлением → верификацией
- ✅ Понятное состояние проекта (сколько активных багов)
- ✅ CLI для управления багами
- ✅ Автоматическая группировка повторяющихся ошибок

## Архитектура

### Lifecycle бага

```
┌──────────────────────────────────────────────────────────────┐
│                      Bug Lifecycle                           │
└──────────────────────────────────────────────────────────────┘

1. DETECTED     →  Обнаружен SupervisorAgent в production
   🔴              - Автоматическая регистрация
                   - Генерируется уникальный bug_id
                   - Файл: data/bugs/active/<bug_id>.json

2. ANALYZED     →  Проанализирован (LLM или вручную)
   🟡              - Добавлен анализ причины
                   - Определена severity
                   - Файл: data/bugs/active/<bug_id>.json

3. FIXED        →  Исправлен разработчиком
   🔵              - Связан с git commit hash
                   - Описание исправления
                   - Файл: data/bugs/active/<bug_id>.json
                   - Команда: bug_manager.py fix <bug_id> <commit> "description"

4. VERIFIED     →  Исправление проверено
   🟢              - Sandbox mode прошел успешно
                   - Или верифицировано вручную
                   - Файл: data/bugs/verified/<bug_id>.json
                   - Команда: bug_manager.py verify <bug_id>

5. CLOSED       →  Баг больше не воспроизводится
   ⚫              - Длительное время без повторений
                   - Или закрыт вручную
                   - Файл: data/bugs/closed/<bug_id>.json
                   - Команда: bug_manager.py close <bug_id>
```

### Файловая структура

```
data/bugs/
├── active/                  # Активные баги (DETECTED, ANALYZED, FIXED)
│   ├── a1b2c3d4e5f6.json  # Каждый баг = отдельный файл
│   └── ...
├── verified/                # Проверенные баги (VERIFIED)
│   └── x9y8z7w6v5u4.json
├── closed/                  # Закрытые баги (CLOSED)
│   └── m5n4o3p2q1r0.json
└── index.json              # Индекс всех багов + статистика
```

### Компоненты

1. **BugTracker** (`src/utils/bug_tracker.py`)
   - Управление lifecycle багов
   - Генерация уникальных bug_id (по сигнатуре ошибки)
   - Отслеживание повторений (deduplicate)
   - Статистика

2. **SupervisorAgent** (интеграция)
   - Автоматически регистрирует ошибки
   - Вызывает `bug_tracker.report_bug()` при каждой ошибке
   - Работает в production и sandbox mode

3. **Bug Manager CLI** (`bug_manager.py`)
   - Утилита командной строки
   - Управление статусами багов
   - Генерация отчетов

## Использование

### Автоматическое обнаружение (SupervisorAgent)

Ошибки автоматически регистрируются при запуске агента:

```bash
python main.py
# При возникновении ошибки она автоматически попадет в data/bugs/active/
```

### Просмотр активных багов

```bash
# Список всех активных багов
python bug_manager.py list

# Детали конкретного бага
python bug_manager.py show a1b2c3d4e5f6
```

Вывод:
```
📋 Active Bugs (3):

Bug ID         Status       Error Type           Occurrences  Last Seen
----------------------------------------------------------------------------------
a1b2c3d4e5f6   detected     AttributeError       5            2026-01-15 21:03:56
b2c3d4e5f6a1   detected     TypeError            2            2026-01-15 20:29:18
c3d4e5f6a1b2   fixed        TimeoutError         1            2026-01-15 21:03:56
```

### Отметить как исправленный

После исправления бага в коде:

```bash
# 1. Делаем commit с исправлением
git add src/dialogue_manager.py
git commit -m "Fix AttributeError in context_extractor"
# Получаем commit hash: abc123

# 2. Регистрируем исправление
python bug_manager.py fix a1b2c3d4e5f6 abc123 "Removed reference to non-existent context_extractor attribute"
```

### Верификация исправления

```bash
# Автоматическая верификация через sandbox
python main.py --sandbox

# Если sandbox прошел успешно - отмечаем как verified
python bug_manager.py verify a1b2c3d4e5f6

# Или с заметками
python bug_manager.py verify a1b2c3d4e5f6 --notes "All tests passed, no errors in 10 runs"
```

### Закрытие бага

```bash
# Закрыть баг (больше не воспроизводится)
python bug_manager.py close a1b2c3d4e5f6 --reason "Fixed and verified, no occurrences in 30 days"
```

### Статистика и отчеты

```bash
# Быстрая статистика
python bug_manager.py stats

# Полный отчет
python bug_manager.py report

# Сохранить отчет в файл
python bug_manager.py report -o reports/bugs_2026_01_15.md
```

Вывод stats:
```
📊 Bug Statistics:

Total bugs tracked: 15

By Status:
  🔴 DETECTED    : 3
  🟡 ANALYZED    : 0
  🔵 FIXED       : 2
  🟢 VERIFIED    : 7
  ⚫ CLOSED      : 3
```

## Workflow разработчика

### Типичный цикл работы с багом

```bash
# 1. Обнаружение (автоматически)
# Пользователь запускает агента, происходит ошибка
python main.py
# → Bug auto-registered: a1b2c3d4e5f6

# 2. Просмотр активных багов
python bug_manager.py list
# → Видим новый баг a1b2c3d4e5f6

# 3. Изучаем детали
python bug_manager.py show a1b2c3d4e5f6
# → Понимаем причину, читаем stack trace

# 4. Исправляем в коде
vim src/dialogue_manager.py
# ... делаем исправление ...

# 5. Коммитим
git add src/dialogue_manager.py
git commit -m "Fix AttributeError in _format_action_result"
git log -1 --format="%H"  # Получаем hash: abc123def456

# 6. Регистрируем исправление
python bug_manager.py fix a1b2c3d4e5f6 abc123def456 "Removed context_extractor reference"
# → Bug moved to FIXED

# 7. Проверяем что исправление работает
python main.py --sandbox
# → Все тесты прошли

# 8. Верифицируем
python bug_manager.py verify a1b2c3d4e5f6
# → Bug moved to VERIFIED

# 9. Через месяц (если больше не воспроизводился)
python bug_manager.py close a1b2c3d4e5f6
# → Bug moved to CLOSED
```

### Интеграция с Git

При коммите исправления рекомендуем включать bug_id:

```bash
git commit -m "Fix AttributeError in context_extractor

Fixes bug: a1b2c3d4e5f6
- Removed reference to non-existent self.context_extractor
- Added proper null checks
"
```

Это позволит легко найти commit по bug_id и наоборот.

## Автоматизация

### Pre-commit hook для верификации

Создайте `.git/hooks/pre-commit`:

```bash
#!/bin/bash
# Проверка что все FIXED баги действительно исправлены

echo "🔍 Checking fixed bugs..."
python bug_manager.py stats | grep "FIXED" | grep -v "FIXED.*: 0" && {
    echo "⚠️  Warning: There are FIXED bugs that need verification"
    echo "   Run: python main.py --sandbox"
    echo "   Then: python bug_manager.py verify <bug_id>"
}
```

### Автоматическое закрытие старых багов

Можно создать скрипт для периодической проверки:

```python
# scripts/auto_close_old_bugs.py
from src.utils.bug_tracker import BugTracker, BugStatus
from datetime import datetime, timedelta

tracker = BugTracker()
now = datetime.now()

for bug_id, bug in tracker.index["bugs"].items():
    if bug["status"] == BugStatus.VERIFIED.value:
        verified_date = datetime.fromisoformat(bug["verification_date"])

        # Если прошло 30 дней без новых occurrence
        if (now - verified_date).days > 30:
            last_seen = datetime.fromisoformat(bug["last_seen"])
            if (now - last_seen).days > 30:
                tracker.mark_as_closed(
                    bug_id,
                    f"Auto-closed: No occurrences in 30 days"
                )
                print(f"✓ Auto-closed: {bug_id}")
```

## Интеграция с существующими отчетами

### Миграция старых BUGFIX_*.md в Bug Tracker

Можно создать скрипт миграции:

```python
# scripts/migrate_bugfix_reports.py
import re
from pathlib import Path
from src.utils.bug_tracker import BugTracker

tracker = BugTracker()

# Читаем старые BUGFIX отчеты
for bugfix_file in Path(".").glob("BUGFIX_*.md"):
    with open(bugfix_file, "r") as f:
        content = f.read()

    # Парсим информацию из отчета
    # ... извлекаем error_type, description и т.д. ...

    # Создаем баг с историческими данными
    # ...
```

### Синхронизация с CHANGELOG.md

При регистрации исправления можно автоматически обновлять CHANGELOG:

```python
def mark_as_fixed(self, bug_id: str, commit_hash: str, fix_description: str):
    # ... существующая логика ...

    # Обновляем CHANGELOG
    self._update_changelog(bug_id, fix_description)
```

## Преимущества новой системы

### Для разработчика

1. **Прозрачность**: Видно актуальное состояние всех багов
2. **Автоматизация**: Не нужно вручную создавать BUGFIX_*.md
3. **Связность**: Bug ID → Commit Hash → Верификация
4. **История**: Полный lifecycle каждого бага
5. **Deduplicate**: Повторяющиеся ошибки не создают дубликаты

### Для проекта

1. **Метрики**: Видно сколько активных/исправленных/закрытых багов
2. **Quality Gate**: Можно блокировать deploy если много активных багов
3. **Отчетность**: Автоматические отчеты для stakeholders
4. **Паттерны**: Видно какие типы ошибок встречаются чаще всего

### Для пользователей

1. **Feedback Loop**: Их ошибки автоматически регистрируются
2. **Прогресс**: Можно показать "баг который вы нашли исправлен"
3. **Качество**: Меньше повторяющихся ошибок

## Примеры реальных сценариев

### Сценарий 1: Повторяющаяся ошибка

```
День 1: Пользователь A встречает AttributeError
→ Bug a1b2c3 зарегистрирован (occurrences: 1)

День 2: Пользователь B встречает ту же ошибку
→ Bug a1b2c3 обновлен (occurrences: 2)

День 3: Разработчик смотрит баги
→ python bug_manager.py list
→ Видит a1b2c3 с occurrences: 2 (priority!)

День 4: Исправление
→ python bug_manager.py fix a1b2c3 abc123 "Fixed"

День 5: Верификация
→ python main.py --sandbox
→ python bug_manager.py verify a1b2c3

Результат: Больше никто не встречает эту ошибку
```

### Сценарий 2: False positive

```
Обнаружена ошибка "TimeoutError loading dolcegabbana.com"
→ Bug x9y8z7 зарегистрирован

Анализ: Это проблема сети пользователя, не баг кода

Действие:
→ python bug_manager.py close x9y8z7 --reason "External timeout, not a bug"

Результат: Не тратим время на "исправление" несуществующего бага
```

### Сценарий 3: Регрессия

```
День 1: Bug a1b2c3 исправлен и verified

День 30: Тот же баг снова появился (после другого изменения)
→ Bug a1b2c3 обновлен (occurrences: +1)
→ Status автоматически: DETECTED (регрессия!)

Разработчик видит:
→ "Bug a1b2c3 was VERIFIED but now DETECTED again"
→ Смотрит историю: "Fixed in commit abc123, но регрессия"
→ Проверяет что сломало исправление
```

## FAQ

**Q: Что если баг исправлен, но я забыл зарегистрировать исправление?**
A: Запустите `python bug_manager.py list`, найдите bug_id старого коммита (через `git log`), выполните `fix` команду задним числом.

**Q: Можно ли удалить баг из системы?**
A: Нет, но можно закрыть с причиной "False positive" или "Duplicate".

**Q: Как связать несколько commit'ов с одним багом?**
A: В `fix_description` укажите все коммиты. В будущем можно расширить систему для поддержки multiple commits.

**Q: Что делать с багами из старых логов?**
A: Они останутся в `data/errors/` как исторические данные. Новые баги будут в `data/bugs/`. Можно написать скрипт миграции.

**Q: Как часто нужно запускать верификацию?**
A: После каждого исправления и перед каждым деплоем. Можно автоматизировать в CI/CD.

## Развитие системы

### Планируемые улучшения

1. **Web UI**: Визуальный dashboard для просмотра багов
2. **CI/CD Integration**: Автоматическая верификация в pipeline
3. **Slack/Discord notifications**: Уведомления о новых багах
4. **Severity levels**: Critical, High, Medium, Low
5. **Bug assignee**: Кто работает над багом
6. **SLA tracking**: Сколько времени баг открыт
7. **Analytics**: Trends, hotspots, most common errors

### Расширения

```python
# Пример: добавление severity
tracker.report_bug(error_data, session_id, severity="critical")

# Пример: assignee
tracker.assign_bug(bug_id, assignee="developer@example.com")

# Пример: SLA check
tracker.check_sla()  # Список багов превысивших SLA
```

## Заключение

Bug Lifecycle Management System решает ключевую проблему проекта: **невозможность понять актуальное состояние багов**.

Теперь:
- ✅ Все ошибки автоматически отслеживаются
- ✅ Есть единая система lifecycle
- ✅ Связь между обнаружением и исправлением
- ✅ Прозрачное состояние проекта
- ✅ CLI для управления

**Начните использовать прямо сейчас:**

```bash
# 1. Запустите агента (ошибки будут автоматически регистрироваться)
python main.py

# 2. Посмотрите активные баги
python bug_manager.py list

# 3. Исправьте баг и зарегистрируйте исправление
python bug_manager.py fix <bug_id> <commit_hash> "description"

# 4. Проверьте исправление
python main.py --sandbox
python bug_manager.py verify <bug_id>
```

🎯 **Цель**: 0 активных багов в production!

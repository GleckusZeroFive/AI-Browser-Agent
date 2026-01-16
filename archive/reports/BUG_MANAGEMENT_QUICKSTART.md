# Bug Management Quick Start

## 🚀 Быстрый старт за 2 минуты

### 1️⃣ Ошибки регистрируются автоматически

Просто запустите агента. Все ошибки автоматически попадут в систему:

```bash
python main.py
```

### 2️⃣ Посмотрите что нашлось

```bash
python bug_manager.py list
```

Вывод:
```
📋 Active Bugs (2):

Bug ID         Status       Error Type           Occurrences  Last Seen
----------------------------------------------------------------------------------
a1b2c3d4e5f6   detected     AttributeError       5            2026-01-15 21:03:56
b2c3d4e5f6a1   detected     TypeError            2            2026-01-15 20:29:18
```

### 3️⃣ Изучите баг подробнее

```bash
python bug_manager.py show a1b2c3d4e5f6
```

### 4️⃣ Исправьте и зарегистрируйте

```bash
# После исправления в коде и git commit
python bug_manager.py fix a1b2c3d4e5f6 <commit_hash> "Fixed AttributeError in context_extractor"
```

### 5️⃣ Проверьте исправление

```bash
# Запустите sandbox тесты
python main.py --sandbox

# Если все ОК - отметьте как проверенный
python bug_manager.py verify a1b2c3d4e5f6
```

### 6️⃣ Посмотрите статистику

```bash
python bug_manager.py stats
```

Вывод:
```
📊 Bug Statistics:

Total bugs tracked: 15

By Status:
  🔴 DETECTED    : 2  ← Нужно исправить
  🔵 FIXED       : 1  ← Нужно проверить
  🟢 VERIFIED    : 10 ← Все хорошо!
  ⚫ CLOSED      : 2
```

## 🎯 Цель

**0 багов в статусе DETECTED или FIXED перед деплоем!**

## 📚 Подробная документация

Полное руководство: [BUG_LIFECYCLE_MANAGEMENT.md](BUG_LIFECYCLE_MANAGEMENT.md)

## 🆘 Частые команды

```bash
# Список активных багов
python bug_manager.py list

# Детали бага
python bug_manager.py show <bug_id>

# Зарегистрировать исправление
python bug_manager.py fix <bug_id> <commit> "description"

# Проверить исправление (после sandbox)
python bug_manager.py verify <bug_id>

# Закрыть баг
python bug_manager.py close <bug_id> --reason "No longer reproducible"

# Статистика
python bug_manager.py stats

# Полный отчет
python bug_manager.py report
```

## 💡 Преимущества

- ✅ **Автоматизация**: Не нужно вручную создавать BUGFIX_*.md
- ✅ **Прозрачность**: Видно актуальное состояние всех багов
- ✅ **Связность**: Bug ID → Commit Hash → Верификация
- ✅ **Deduplicate**: Повторяющиеся ошибки не создают дубликаты
- ✅ **История**: Полный lifecycle каждого бага

## 🔍 Где хранятся данные

```
data/bugs/
├── active/      # Активные баги (нужно исправить)
├── verified/    # Проверенные (все ОК)
├── closed/      # Закрытые (архив)
└── index.json   # Индекс всех багов
```

## ⚡ Интеграция с workflow

```bash
# 1. Работаем над функционалом
vim src/my_feature.py

# 2. Запускаем тесты
python main.py --sandbox

# 3. Если находим баг - он автоматически регистрируется
# 4. Исправляем
# 5. Коммитим
git commit -m "Fix bug XYZ"

# 6. Регистрируем исправление
python bug_manager.py fix <bug_id> $(git log -1 --format="%H") "Fix bug XYZ"

# 7. Верифицируем
python main.py --sandbox
python bug_manager.py verify <bug_id>

# 8. Проверяем что все чисто перед push
python bug_manager.py stats
# Должно быть: 0 DETECTED, 0 FIXED
```

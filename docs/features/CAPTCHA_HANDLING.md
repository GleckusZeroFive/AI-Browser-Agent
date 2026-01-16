# Обработка Капчи (CAPTCHA Handling)

## Обзор

AI Browser Agent теперь включает встроенную систему обнаружения и обработки капч. Система автоматически детектирует большинство популярных типов капч и помогает их решать.

## Поддерживаемые типы капч

### 1. **Google reCAPTCHA v2**
- Классическая капча с галочкой "Я не робот"
- Капча с выбором изображений
- **Детектирование**: Автоматическое по iframe и DOM элементам
- **Решение**: Ручное (пользователь решает в браузере)

### 2. **Google reCAPTCHA v3**
- Невидимая капча, работающая в фоне
- **Детектирование**: По наличию скриптов reCAPTCHA
- **Решение**: Автоматическое (оценка поведения)

### 3. **hCaptcha**
- Альтернатива reCAPTCHA от Intuition Machines
- **Детектирование**: По iframe и специфическим селекторам
- **Решение**: Ручное

### 4. **CloudFlare Turnstile**
- Современная замена reCAPTCHA от CloudFlare
- **Детектирование**: По CloudFlare challenge page
- **Решение**: Ручное/Автоматическое (зависит от типа)

### 5. **Yandex SmartCaptcha**
- Капча от Яндекса для российских сайтов
- **Детектирование**: По специфическим элементам Яндекса
- **Решение**: Ручное

## Как это работает

### Автоматическое детектирование

Система автоматически проверяет наличие капчи:

1. **При навигации** - после перехода на новую страницу
2. **При ошибках** - когда действия не выполняются
3. **По запросу** - через метод `check_for_captcha()`

### Методы обработки

#### 1. Ручное решение (по умолчанию)

Когда капча обнаружена:
```
⚠️  Обнаружена Google reCAPTCHA v2
⏳ Пожалуйста, решите капчу вручную в браузере
⏱️  Ожидание: 300 секунд
```

Агент автоматически:
- Паузирует выполнение
- Показывает уведомление пользователю
- Ждёт решения капчи (проверяет каждые 2 секунды)
- Продолжает работу после решения

#### 2. Интеграция с сервисами решения (опционально)

Поддерживается интеграция с:
- **2Captcha** ([2captcha.com](https://2captcha.com))
- **AntiCaptcha** ([anti-captcha.com](https://anti-captcha.com))

*Примечание: Требуется API ключ и платная подписка*

## Использование

### Базовая настройка

По умолчанию обработка капч включена автоматически:

```python
from src.tools.browser_tools import BrowserTools

tools = BrowserTools()
await tools.start_browser()

# Капчи будут детектироваться автоматически
result = await tools.navigate("https://example.com")
```

### Отключение автоматической обработки

```python
tools = BrowserTools()
tools.auto_handle_captcha = False  # Отключить
await tools.start_browser()
```

### Явная проверка капчи

```python
# Проверить наличие капчи на текущей странице
result = await tools.check_for_captcha()

if result["captcha_detected"]:
    print(f"Обнаружена: {result['captcha_type']}")
    print(f"Сообщение: {result['message']}")
```

### Ручное решение капчи

```python
# Запросить пользователя решить капчу
result = await tools.solve_captcha_manually(timeout=300)

if result["captcha_solved"]:
    print(f"Капча решена за {result['duration']:.1f}с")
else:
    print(f"Капча не решена: {result['message']}")
```

## Конфигурация

### В файле `src/config.py`

Добавьте следующие настройки:

```python
class Config:
    # ... существующие настройки ...

    # Настройки обработки капчи
    CAPTCHA_AUTO_HANDLE = True          # Автоматически обрабатывать капчи
    CAPTCHA_MANUAL_TIMEOUT = 300        # Таймаут ручного решения (секунды)
    CAPTCHA_CHECK_INTERVAL = 2          # Интервал проверки решения (секунды)

    # Опционально: Сервис автоматического решения
    CAPTCHA_SOLVER_SERVICE = None       # "2captcha" или "anticaptcha"
    CAPTCHA_SOLVER_API_KEY = None       # API ключ для сервиса
```

### В `.env` файле

```env
# Обработка капч
CAPTCHA_AUTO_HANDLE=true
CAPTCHA_MANUAL_TIMEOUT=300

# Опционально: Автоматическое решение
# CAPTCHA_SOLVER_SERVICE=2captcha
# CAPTCHA_SOLVER_API_KEY=your_api_key_here
```

## Антидетект функции

Для минимизации появления капч агент использует:

### 1. **Реалистичный User-Agent**
```python
user_agents = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) ...',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) ...',
    # Ротация между реальными UA
]
```

### 2. **Скрытие WebDriver флагов**
```javascript
Object.defineProperty(navigator, 'webdriver', {
    get: () => undefined
});
```

### 3. **Реалистичные заголовки**
```python
extra_http_headers={
    'Accept': 'text/html,application/xhtml+xml,...',
    'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8',
    'DNT': '1',
    # ... полный набор реалистичных headers
}
```

### 4. **Canvas & WebGL Fingerprint Protection**
- Модификация canvas fingerprint
- Эмуляция реалистичного GPU
- Защита от детектирования автоматизации

### 5. **Реалистичное поведение**
- Случайные задержки между действиями
- Вариативные размеры viewport
- Геолокация (Москва по умолчанию)

## Интеграция с ActionExecutor

Капчи автоматически обрабатываются в следующих действиях:

- `navigate` - При переходе на новый URL
- `click_by_text` - При клике на элементы
- `type_text` - При вводе текста в формы

## Примеры использования

### Пример 1: Базовая работа с сайтом

```python
tools = BrowserTools()
await tools.start_browser()

# Автоматическая обработка капчи при навигации
result = await tools.navigate("https://example.com")

if result.get("captcha_encountered"):
    if result.get("captcha_solved"):
        print("✅ Капча решена, продолжаем работу")
    else:
        print("❌ Капча не решена, остановка")
else:
    print("✅ Капча не обнаружена")
```

### Пример 2: Явная проверка перед действием

```python
# Перед важным действием проверяем капчу
captcha_check = await tools.check_for_captcha()

if captcha_check["captcha_detected"]:
    print(f"⚠️  Обнаружена капча: {captcha_check['captcha_type']}")

    # Ждём решения
    solve_result = await tools.solve_captcha_manually(timeout=180)

    if not solve_result["captcha_solved"]:
        print("Не удалось решить капчу, прерываем")
        return

# Продолжаем с основным действием
await tools.click_by_text("Submit")
```

### Пример 3: Работа с почтой (Yandex/Gmail)

```python
tools = BrowserTools()
await tools.start_browser()

# Открываем почту
result = await tools.navigate("https://mail.yandex.ru")

# Если появилась капча, она будет обработана автоматически
if result.get("captcha_encountered"):
    print(f"Капча была обнаружена и {'решена' if result['captcha_solved'] else 'не решена'}")

# Продолжаем работу
await tools.type_text("#login", "username")
await tools.click_by_text("Войти")
```

## Диагностика проблем

### Капча не детектируется

**Проблема**: Агент не замечает капчу на странице.

**Решение**:
1. Проверьте лог-файлы в `logs/`
2. Сделайте скриншот: `await tools.take_screenshot()`
3. Попробуйте явную проверку: `await tools.check_for_captcha()`
4. Возможно, это новый тип капчи - создайте issue

### Капча детектируется неправильно

**Проблема**: False positive - капчи нет, но система её видит.

**Решение**:
1. Проверьте, какой тип капчи определяется
2. Посмотрите HTML код страницы
3. Можно временно отключить: `tools.auto_handle_captcha = False`

### Таймаут при решении

**Проблема**: 300 секунд недостаточно для решения капчи.

**Решение**:
```python
# Увеличьте таймаут
result = await tools.solve_captcha_manually(timeout=600)  # 10 минут
```

Или в конфиге:
```python
Config.CAPTCHA_MANUAL_TIMEOUT = 600
```

### Капчи появляются постоянно

**Проблема**: Сайт показывает капчу при каждом действии.

**Решение**:
1. Замедлите действия агента (увеличьте задержки)
2. Проверьте антидетект настройки
3. Используйте cookies от ручного входа
4. Рассмотрите использование платного сервиса решения

## Best Practices

### 1. Минимизация появления капч

- Используйте headless=False (видимый браузер)
- Делайте паузы между действиями
- Не превышайте rate limits сайта
- Используйте cookies от предыдущих сессий

### 2. Graceful degradation

```python
try:
    result = await tools.navigate(url)

    if result.get("captcha_encountered") and not result.get("captcha_solved"):
        # Fallback логика
        logger.warning("Капча не решена, пробуем альтернативный путь")
        # Ваша альтернативная логика
except Exception as e:
    logger.error(f"Ошибка: {e}")
```

### 3. Логирование

```python
import logging

logger = logging.getLogger(__name__)

captcha_result = await tools.check_for_captcha()
if captcha_result["captcha_detected"]:
    logger.warning(f"Капча обнаружена: {captcha_result['captcha_type']}")
```

## Будущие улучшения

Планируется добавить:

- [ ] Интеграция с 2Captcha API
- [ ] Интеграция с AntiCaptcha API
- [ ] AI-решение простых капч через Claude Vision
- [ ] Автоматическое переключение прокси при капче
- [ ] Статистика по капчам (как часто появляются)
- [ ] Адаптивные задержки на основе детектирования капч

## Получение помощи

Если возникли проблемы с капчами:

1. Проверьте логи в `logs/errors.log`
2. Сделайте скриншот момента с капчей
3. Создайте issue в репозитории с:
   - Типом сайта
   - Типом капчи
   - Логами и скриншотами

## См. также

- [README.md](../README.md) - Основная документация
- [config.py](../src/config.py) - Файл конфигурации
- [browser_tools.py](../src/tools/browser_tools.py) - Реализация браузерных инструментов
- [captcha_handler.py](../src/utils/captcha_handler.py) - Обработчик капч

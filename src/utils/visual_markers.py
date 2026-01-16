"""
Визуальные маркеры для действий агента в браузере.

Добавляет визуальную индикацию при:
- Кликах (подсветка элемента)
- Вводе текста (анимация курсора)
- Скролле (индикатор направления)
- Ожидании (спиннер)
"""
from typing import Optional
from playwright.async_api import Page


class VisualMarkers:
    """Класс для визуальной индикации действий агента"""

    def __init__(self, page: Page, enabled: bool = True):
        self.page = page
        self.enabled = enabled
        self._injected = False

    async def inject_styles(self):
        """Инжектируем CSS стили для визуальных маркеров"""
        if self._injected or not self.enabled:
            return

        css = """
        <style id="ai-agent-visual-markers">
            /* Подсветка элемента при клике */
            @keyframes ai-click-highlight {
                0% {
                    box-shadow: 0 0 0 0 rgba(66, 153, 225, 0.7);
                    transform: scale(1);
                }
                50% {
                    box-shadow: 0 0 0 20px rgba(66, 153, 225, 0);
                    transform: scale(1.05);
                }
                100% {
                    box-shadow: 0 0 0 0 rgba(66, 153, 225, 0);
                    transform: scale(1);
                }
            }

            .ai-clicking {
                animation: ai-click-highlight 0.6s ease-out;
                outline: 3px solid #4299e1 !important;
                outline-offset: 2px;
            }

            /* Индикатор ввода текста */
            @keyframes ai-typing-cursor {
                0%, 100% { opacity: 1; }
                50% { opacity: 0; }
            }

            .ai-typing {
                outline: 2px solid #48bb78 !important;
                outline-offset: 2px;
                position: relative;
            }

            .ai-typing::after {
                content: '▍';
                position: absolute;
                right: -15px;
                top: 50%;
                transform: translateY(-50%);
                color: #48bb78;
                font-size: 24px;
                animation: ai-typing-cursor 1s step-end infinite;
            }

            /* Индикатор скролла */
            .ai-scroll-indicator {
                position: fixed;
                right: 20px;
                top: 50%;
                transform: translateY(-50%);
                background: rgba(66, 153, 225, 0.9);
                color: white;
                padding: 10px 15px;
                border-radius: 8px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                z-index: 999999;
                animation: ai-scroll-fade-in 0.3s ease-in;
                box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            }

            @keyframes ai-scroll-fade-in {
                from {
                    opacity: 0;
                    transform: translateY(-50%) translateX(20px);
                }
                to {
                    opacity: 1;
                    transform: translateY(-50%) translateX(0);
                }
            }

            /* Спиннер ожидания */
            .ai-spinner {
                position: fixed;
                top: 20px;
                right: 20px;
                width: 40px;
                height: 40px;
                border: 4px solid rgba(66, 153, 225, 0.3);
                border-top-color: #4299e1;
                border-radius: 50%;
                animation: ai-spin 1s linear infinite;
                z-index: 999999;
            }

            @keyframes ai-spin {
                to { transform: rotate(360deg); }
            }

            /* Индикатор действия */
            .ai-action-indicator {
                position: fixed;
                top: 20px;
                left: 50%;
                transform: translateX(-50%);
                background: rgba(66, 153, 225, 0.95);
                color: white;
                padding: 12px 24px;
                border-radius: 8px;
                font-family: Arial, sans-serif;
                font-size: 14px;
                font-weight: bold;
                z-index: 999999;
                animation: ai-action-fade-in 0.3s ease-in;
                box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
            }

            @keyframes ai-action-fade-in {
                from {
                    opacity: 0;
                    transform: translateX(-50%) translateY(-10px);
                }
                to {
                    opacity: 1;
                    transform: translateX(-50%) translateY(0);
                }
            }
        </style>
        """

        await self.page.evaluate(f"""
            () => {{
                if (!document.getElementById('ai-agent-visual-markers')) {{
                    document.head.insertAdjacentHTML('beforeend', `{css}`);
                }}
            }}
        """)

        self._injected = True

    async def highlight_click(self, selector: str, duration: int = 600):
        """
        Подсветить элемент при клике.

        Args:
            selector: CSS селектор элемента
            duration: Длительность анимации в мс
        """
        if not self.enabled:
            return

        await self.inject_styles()

        await self.page.evaluate("""
            ([selector, duration]) => {
                const element = document.querySelector(selector);
                if (element) {
                    element.classList.add('ai-clicking');
                    setTimeout(() => {
                        element.classList.remove('ai-clicking');
                    }, duration);
                }
            }
        """, [selector, duration])

    async def highlight_click_by_text(self, text: str, duration: int = 600):
        """
        Подсветить элемент по тексту.

        Args:
            text: Текст элемента
            duration: Длительность анимации в мс
        """
        if not self.enabled:
            return

        await self.inject_styles()

        await self.page.evaluate("""
            ([text, duration]) => {
                const xpath = `//*[contains(text(), '${text}')]`;
                const result = document.evaluate(xpath, document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null);
                const element = result.singleNodeValue;

                if (element) {
                    element.classList.add('ai-clicking');
                    setTimeout(() => {
                        element.classList.remove('ai-clicking');
                    }, duration);
                }
            }
        """, [text, duration])

    async def show_typing(self, selector: str, duration: int = 1000):
        """
        Показать индикатор ввода текста.

        Args:
            selector: CSS селектор элемента
            duration: Длительность показа индикатора в мс
        """
        if not self.enabled:
            return

        await self.inject_styles()

        await self.page.evaluate("""
            ([selector, duration]) => {
                const element = document.querySelector(selector);
                if (element) {
                    element.classList.add('ai-typing');
                    setTimeout(() => {
                        element.classList.remove('ai-typing');
                    }, duration);
                }
            }
        """, [selector, duration])

    async def show_scroll_indicator(self, direction: str = "down", duration: int = 1000):
        """
        Показать индикатор скролла.

        Args:
            direction: Направление скролла ('up' или 'down')
            duration: Длительность показа в мс
        """
        if not self.enabled:
            return

        await self.inject_styles()

        arrow = "⬇️" if direction == "down" else "⬆️"
        text = f"{arrow} Скролл {direction}"

        await self.page.evaluate("""
            ([text, duration]) => {
                // Удаляем старый индикатор если есть
                const oldIndicator = document.querySelector('.ai-scroll-indicator');
                if (oldIndicator) {
                    oldIndicator.remove();
                }

                // Создаём новый
                const indicator = document.createElement('div');
                indicator.className = 'ai-scroll-indicator';
                indicator.textContent = text;
                document.body.appendChild(indicator);

                setTimeout(() => {
                    indicator.remove();
                }, duration);
            }
        """, [text, duration])

    async def show_spinner(self, show: bool = True):
        """
        Показать/скрыть спиннер ожидания.

        Args:
            show: True - показать, False - скрыть
        """
        if not self.enabled:
            return

        await self.inject_styles()

        if show:
            await self.page.evaluate("""
                () => {
                    if (!document.querySelector('.ai-spinner')) {
                        const spinner = document.createElement('div');
                        spinner.className = 'ai-spinner';
                        document.body.appendChild(spinner);
                    }
                }
            """)
        else:
            await self.page.evaluate("""
                () => {
                    const spinner = document.querySelector('.ai-spinner');
                    if (spinner) {
                        spinner.remove();
                    }
                }
            """)

    async def show_action_indicator(self, action: str, duration: int = 2000):
        """
        Показать индикатор текущего действия.

        Args:
            action: Описание действия (например, "Поиск элемента...")
            duration: Длительность показа в мс
        """
        if not self.enabled:
            return

        await self.inject_styles()

        await self.page.evaluate("""
            ([action, duration]) => {
                // Удаляем старый индикатор
                const oldIndicator = document.querySelector('.ai-action-indicator');
                if (oldIndicator) {
                    oldIndicator.remove();
                }

                // Создаём новый
                const indicator = document.createElement('div');
                indicator.className = 'ai-action-indicator';
                indicator.textContent = '🤖 ' + action;
                document.body.appendChild(indicator);

                setTimeout(() => {
                    indicator.remove();
                }, duration);
            }
        """, [action, duration])

    async def cleanup(self):
        """Очистить все визуальные маркеры"""
        if not self.enabled:
            return

        await self.page.evaluate("""
            () => {
                // Удаляем все классы
                document.querySelectorAll('.ai-clicking, .ai-typing').forEach(el => {
                    el.classList.remove('ai-clicking', 'ai-typing');
                });

                // Удаляем все индикаторы
                document.querySelectorAll('.ai-scroll-indicator, .ai-spinner, .ai-action-indicator').forEach(el => {
                    el.remove();
                });
            }
        """)


# Singleton для использования в action_executor
_visual_markers_instance: Optional[VisualMarkers] = None


def get_visual_markers(page: Page, enabled: bool = True) -> VisualMarkers:
    """
    Получить глобальный экземпляр VisualMarkers.

    Args:
        page: Playwright Page объект
        enabled: Включены ли визуальные маркеры

    Returns:
        VisualMarkers экземпляр
    """
    global _visual_markers_instance
    if _visual_markers_instance is None or _visual_markers_instance.page != page:
        _visual_markers_instance = VisualMarkers(page, enabled)
    return _visual_markers_instance

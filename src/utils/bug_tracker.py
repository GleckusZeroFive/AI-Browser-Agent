"""
Bug Lifecycle Tracker - отслеживание жизненного цикла ошибок

Решает проблему: невозможно понять какие баги актуальны, а какие исправлены

Lifecycle:
1. DETECTED - ошибка обнаружена SupervisorAgent в production
2. ANALYZED - ошибка проанализирована (sandbox или вручную)
3. FIXED - ошибка исправлена (с git commit hash)
4. VERIFIED - исправление проверено (sandbox прошел успешно)
5. CLOSED - ошибка больше не воспроизводится

Файловая структура:
data/bugs/
├── active/          # Активные баги (DETECTED, ANALYZED, FIXED)
├── verified/        # Проверенные (VERIFIED)
├── closed/          # Закрытые (CLOSED)
└── index.json       # Индекс всех багов с метаданными
"""
import json
import hashlib
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path
from enum import Enum
import logging


class BugStatus(Enum):
    """Статусы жизненного цикла бага"""
    DETECTED = "detected"       # Обнаружен в production
    ANALYZED = "analyzed"       # Проанализирован
    FIXED = "fixed"            # Исправлен (есть commit)
    VERIFIED = "verified"      # Проверен (sandbox OK)
    CLOSED = "closed"          # Закрыт (больше не воспроизводится)


class BugTracker:
    """
    Отслеживание жизненного цикла ошибок

    Интегрируется с:
    - SupervisorAgent (для автоматического обнаружения)
    - Sandbox Mode (для верификации)
    - Git (для связывания с коммитами)
    """

    def __init__(self, bugs_dir: str = "data/bugs"):
        self.bugs_dir = Path(bugs_dir)
        self.active_dir = self.bugs_dir / "active"
        self.verified_dir = self.bugs_dir / "verified"
        self.closed_dir = self.bugs_dir / "closed"
        self.index_file = self.bugs_dir / "index.json"

        # Создаем структуру директорий
        self.active_dir.mkdir(parents=True, exist_ok=True)
        self.verified_dir.mkdir(parents=True, exist_ok=True)
        self.closed_dir.mkdir(parents=True, exist_ok=True)

        self.logger = logging.getLogger(__name__)

        # Загружаем или создаем индекс
        self.index = self._load_or_create_index()

    def _load_or_create_index(self) -> Dict[str, Any]:
        """Загрузить или создать индекс багов"""
        if self.index_file.exists():
            try:
                with open(self.index_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                self.logger.error(f"Не удалось загрузить индекс: {e}")

        # Создаем новый индекс
        return {
            "version": "1.0",
            "last_updated": datetime.now().isoformat(),
            "bugs": {},
            "stats": {
                "total": 0,
                "by_status": {status.value: 0 for status in BugStatus}
            }
        }

    def _save_index(self):
        """Сохранить индекс"""
        self.index["last_updated"] = datetime.now().isoformat()

        try:
            with open(self.index_file, "w", encoding="utf-8") as f:
                json.dump(self.index, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Не удалось сохранить индекс: {e}")

    def _generate_bug_id(self, error_data: Dict[str, Any]) -> str:
        """
        Генерировать уникальный ID бага на основе его сигнатуры

        Одинаковые ошибки получают одинаковый ID
        """
        signature = f"{error_data.get('error_type')}:{error_data.get('action')}:{error_data.get('error_message', '')[:100]}"
        return hashlib.sha256(signature.encode()).hexdigest()[:12]

    def report_bug(
        self,
        error_data: Dict[str, Any],
        session_id: str,
        source: str = "production"
    ) -> str:
        """
        Зарегистрировать новый баг или обновить существующий

        Args:
            error_data: данные об ошибке от SupervisorAgent
            session_id: ID сессии где произошла ошибка
            source: источник ("production", "sandbox")

        Returns:
            bug_id: ID бага
        """
        bug_id = self._generate_bug_id(error_data)

        # Проверяем, существует ли уже этот баг
        if bug_id in self.index["bugs"]:
            bug_info = self.index["bugs"][bug_id]

            # Обновляем occurrence count
            bug_info["occurrences"] += 1
            bug_info["last_seen"] = datetime.now().isoformat()
            bug_info["sessions"].append({
                "session_id": session_id,
                "timestamp": datetime.now().isoformat(),
                "source": source
            })

            self.logger.info(f"Bug {bug_id} seen again (occurrences: {bug_info['occurrences']})")

        else:
            # Новый баг
            bug_info = {
                "bug_id": bug_id,
                "status": BugStatus.DETECTED.value,
                "first_seen": datetime.now().isoformat(),
                "last_seen": datetime.now().isoformat(),
                "occurrences": 1,
                "error_type": error_data.get("error_type"),
                "error_message": error_data.get("error_message"),
                "action": error_data.get("action"),
                "sessions": [{
                    "session_id": session_id,
                    "timestamp": datetime.now().isoformat(),
                    "source": source
                }],
                "analysis": error_data.get("analysis"),
                "fix_commit": None,
                "verification_date": None,
                "closed_date": None
            }

            self.index["bugs"][bug_id] = bug_info
            self.index["stats"]["total"] += 1
            self.index["stats"]["by_status"][BugStatus.DETECTED.value] += 1

            self.logger.info(f"New bug detected: {bug_id}")

        # Сохраняем детальную информацию в файл
        self._save_bug_detail(bug_id, bug_info, error_data)

        # Обновляем индекс
        self._save_index()

        return bug_id

    def _save_bug_detail(self, bug_id: str, bug_info: Dict[str, Any], error_data: Dict[str, Any]):
        """Сохранить детальную информацию о баге"""
        status = bug_info["status"]

        # Определяем директорию по статусу
        if status in [BugStatus.DETECTED.value, BugStatus.ANALYZED.value, BugStatus.FIXED.value]:
            target_dir = self.active_dir
        elif status == BugStatus.VERIFIED.value:
            target_dir = self.verified_dir
        else:
            target_dir = self.closed_dir

        bug_file = target_dir / f"{bug_id}.json"

        # Полная информация о баге
        full_data = {
            **bug_info,
            "latest_error_data": error_data,
            "history": bug_info.get("history", [])
        }

        try:
            with open(bug_file, "w", encoding="utf-8") as f:
                json.dump(full_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.logger.error(f"Не удалось сохранить детали бага {bug_id}: {e}")

    def mark_as_fixed(self, bug_id: str, commit_hash: str, fix_description: str):
        """
        Отметить баг как исправленный

        Args:
            bug_id: ID бага
            commit_hash: git commit hash с исправлением
            fix_description: описание исправления
        """
        if bug_id not in self.index["bugs"]:
            self.logger.warning(f"Bug {bug_id} not found in index")
            return

        bug_info = self.index["bugs"][bug_id]
        old_status = bug_info["status"]

        # Обновляем статус
        bug_info["status"] = BugStatus.FIXED.value
        bug_info["fix_commit"] = commit_hash
        bug_info["fix_description"] = fix_description
        bug_info["fix_date"] = datetime.now().isoformat()

        # История изменений
        if "history" not in bug_info:
            bug_info["history"] = []

        bug_info["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "status_change",
            "from": old_status,
            "to": BugStatus.FIXED.value,
            "commit": commit_hash,
            "description": fix_description
        })

        # Обновляем статистику
        self.index["stats"]["by_status"][old_status] -= 1
        self.index["stats"]["by_status"][BugStatus.FIXED.value] += 1

        # Перемещаем файл
        self._move_bug_file(bug_id, old_status, BugStatus.FIXED.value)

        # Сохраняем
        self._save_index()

        self.logger.info(f"Bug {bug_id} marked as FIXED (commit: {commit_hash})")

    def mark_as_verified(self, bug_id: str, verification_notes: str = ""):
        """
        Отметить баг как проверенный (исправление работает)

        Args:
            bug_id: ID бага
            verification_notes: заметки о проверке
        """
        if bug_id not in self.index["bugs"]:
            self.logger.warning(f"Bug {bug_id} not found in index")
            return

        bug_info = self.index["bugs"][bug_id]
        old_status = bug_info["status"]

        # Обновляем статус
        bug_info["status"] = BugStatus.VERIFIED.value
        bug_info["verification_date"] = datetime.now().isoformat()
        bug_info["verification_notes"] = verification_notes

        # История
        if "history" not in bug_info:
            bug_info["history"] = []

        bug_info["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "status_change",
            "from": old_status,
            "to": BugStatus.VERIFIED.value,
            "notes": verification_notes
        })

        # Статистика
        self.index["stats"]["by_status"][old_status] -= 1
        self.index["stats"]["by_status"][BugStatus.VERIFIED.value] += 1

        # Перемещаем файл
        self._move_bug_file(bug_id, old_status, BugStatus.VERIFIED.value)

        # Сохраняем
        self._save_index()

        self.logger.info(f"Bug {bug_id} marked as VERIFIED")

    def mark_as_closed(self, bug_id: str, reason: str = "No longer reproducible"):
        """
        Закрыть баг (больше не воспроизводится)

        Args:
            bug_id: ID бага
            reason: причина закрытия
        """
        if bug_id not in self.index["bugs"]:
            self.logger.warning(f"Bug {bug_id} not found in index")
            return

        bug_info = self.index["bugs"][bug_id]
        old_status = bug_info["status"]

        # Обновляем статус
        bug_info["status"] = BugStatus.CLOSED.value
        bug_info["closed_date"] = datetime.now().isoformat()
        bug_info["closed_reason"] = reason

        # История
        if "history" not in bug_info:
            bug_info["history"] = []

        bug_info["history"].append({
            "timestamp": datetime.now().isoformat(),
            "action": "status_change",
            "from": old_status,
            "to": BugStatus.CLOSED.value,
            "reason": reason
        })

        # Статистика
        self.index["stats"]["by_status"][old_status] -= 1
        self.index["stats"]["by_status"][BugStatus.CLOSED.value] += 1

        # Перемещаем файл
        self._move_bug_file(bug_id, old_status, BugStatus.CLOSED.value)

        # Сохраняем
        self._save_index()

        self.logger.info(f"Bug {bug_id} marked as CLOSED: {reason}")

    def _move_bug_file(self, bug_id: str, old_status: str, new_status: str):
        """Переместить файл бага в соответствующую директорию"""
        # Определяем старую и новую директории
        old_dir = self._get_dir_for_status(old_status)
        new_dir = self._get_dir_for_status(new_status)

        old_file = old_dir / f"{bug_id}.json"
        new_file = new_dir / f"{bug_id}.json"

        if old_file.exists():
            try:
                # Читаем, обновляем статус, пишем в новое место
                with open(old_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                data["status"] = new_status

                with open(new_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                # Удаляем старый файл
                old_file.unlink()

            except Exception as e:
                self.logger.error(f"Ошибка при перемещении файла бага {bug_id}: {e}")

    def _get_dir_for_status(self, status: str) -> Path:
        """Получить директорию для статуса"""
        if status in [BugStatus.DETECTED.value, BugStatus.ANALYZED.value, BugStatus.FIXED.value]:
            return self.active_dir
        elif status == BugStatus.VERIFIED.value:
            return self.verified_dir
        else:
            return self.closed_dir

    def get_active_bugs(self) -> List[Dict[str, Any]]:
        """Получить список активных багов"""
        return [
            bug for bug in self.index["bugs"].values()
            if bug["status"] in [BugStatus.DETECTED.value, BugStatus.ANALYZED.value, BugStatus.FIXED.value]
        ]

    def get_bug_by_id(self, bug_id: str) -> Optional[Dict[str, Any]]:
        """Получить информацию о баге по ID"""
        return self.index["bugs"].get(bug_id)

    def get_statistics(self) -> Dict[str, Any]:
        """Получить статистику по багам"""
        return self.index["stats"]

    def generate_report(self, output_file: str = None) -> str:
        """
        Генерировать отчет по текущему состоянию багов

        Args:
            output_file: путь для сохранения отчета (опционально)

        Returns:
            текст отчета
        """
        stats = self.get_statistics()
        active_bugs = self.get_active_bugs()

        report = f"""# Bug Tracker Report
Generated: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

## Summary
- Total bugs tracked: {stats['total']}
- Active bugs: {len(active_bugs)}

## By Status
"""

        for status in BugStatus:
            count = stats["by_status"][status.value]
            report += f"- {status.value.upper()}: {count}\n"

        report += "\n## Active Bugs\n\n"

        if active_bugs:
            for bug in sorted(active_bugs, key=lambda x: x["last_seen"], reverse=True):
                report += f"""### [{bug['bug_id']}] {bug['error_type']}
- Status: {bug['status']}
- Action: {bug['action']}
- Occurrences: {bug['occurrences']}
- First seen: {bug['first_seen']}
- Last seen: {bug['last_seen']}
- Message: {bug['error_message'][:100]}...

"""
        else:
            report += "No active bugs! 🎉\n"

        # Сохраняем в файл если указан
        if output_file:
            try:
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(report)
                self.logger.info(f"Report saved to {output_file}")
            except Exception as e:
                self.logger.error(f"Failed to save report: {e}")

        return report

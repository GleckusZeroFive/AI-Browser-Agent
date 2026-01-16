#!/usr/bin/env python3
"""
Миграция существующих ошибок из data/errors/ в новую Bug Tracker систему

Этот скрипт читает старые логи ошибок и импортирует их в BugTracker
для создания исторической базы.
"""
import json
from pathlib import Path
from src.utils.bug_tracker import BugTracker


def migrate_session_files():
    """Мигрировать session_*.json файлы"""
    errors_dir = Path("data/errors")
    tracker = BugTracker()

    migrated_count = 0
    skipped_count = 0

    print("🔄 Migrating existing errors to Bug Tracker...\n")

    # Ищем все session файлы
    session_files = list(errors_dir.glob("session_*.json"))

    if not session_files:
        print("⚠️  No session files found in data/errors/")
        return

    for session_file in session_files:
        print(f"📂 Processing: {session_file.name}")

        try:
            with open(session_file, "r", encoding="utf-8") as f:
                session_data = json.load(f)

            session_id = session_data.get("session_id", "unknown")
            errors = session_data.get("errors", [])

            if not errors:
                print(f"   ⏭️  No errors in this session")
                skipped_count += 1
                continue

            # Импортируем каждую ошибку
            for error in errors:
                # Проверяем что есть необходимые поля
                if not error.get("error_message"):
                    continue

                bug_id = tracker.report_bug(
                    error_data=error,
                    session_id=session_id,
                    source="migration"
                )

                print(f"   ✓ Imported bug: {bug_id}")
                migrated_count += 1

        except Exception as e:
            print(f"   ❌ Error processing {session_file.name}: {e}")
            skipped_count += 1

    print(f"\n{'=' * 60}")
    print(f"✅ Migration complete!")
    print(f"   Migrated: {migrated_count} bugs")
    print(f"   Skipped: {skipped_count} sessions")
    print(f"{'=' * 60}\n")

    # Показываем статистику
    print("📊 Current bug statistics:\n")
    stats = tracker.get_statistics()
    print(f"Total bugs: {stats['total']}")
    print("\nBy Status:")
    for status, count in stats['by_status'].items():
        if count > 0:
            print(f"  - {status}: {count}")


def migrate_production_jsonl():
    """Мигрировать production_*.jsonl файлы"""
    errors_dir = Path("data/errors")
    tracker = BugTracker()

    migrated_count = 0

    # Ищем JSONL файлы
    jsonl_files = list(errors_dir.glob("production_*.jsonl"))

    if not jsonl_files:
        return

    print("\n🔄 Migrating production JSONL files...\n")

    for jsonl_file in jsonl_files:
        print(f"📂 Processing: {jsonl_file.name}")

        # Извлекаем session_id из имени файла
        session_id = jsonl_file.stem.replace("production_", "")

        try:
            with open(jsonl_file, "r", encoding="utf-8") as f:
                for line in f:
                    if not line.strip():
                        continue

                    error = json.loads(line)

                    if not error.get("error_message"):
                        continue

                    bug_id = tracker.report_bug(
                        error_data=error,
                        session_id=session_id,
                        source="migration"
                    )

                    print(f"   ✓ Imported bug: {bug_id}")
                    migrated_count += 1

        except Exception as e:
            print(f"   ❌ Error processing {jsonl_file.name}: {e}")

    if migrated_count > 0:
        print(f"\n✅ Migrated {migrated_count} bugs from JSONL files\n")


def main():
    print("=" * 60)
    print("Bug Tracker Migration Tool")
    print("=" * 60)
    print()

    # Проверяем что директория существует
    errors_dir = Path("data/errors")
    if not errors_dir.exists():
        print("❌ data/errors/ directory not found")
        print("   Nothing to migrate")
        return

    # Мигрируем session файлы
    migrate_session_files()

    # Мигрируем JSONL файлы
    migrate_production_jsonl()

    print("\n💡 Next steps:")
    print("   1. Review imported bugs: python bug_manager.py list")
    print("   2. Update bug statuses as needed")
    print("   3. Mark fixed bugs: python bug_manager.py fix <bug_id> <commit> \"desc\"")
    print()


if __name__ == "__main__":
    main()

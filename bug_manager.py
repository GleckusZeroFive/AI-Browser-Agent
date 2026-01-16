#!/usr/bin/env python3
"""
Bug Manager CLI - утилита для управления жизненным циклом багов

Использование:
    python bug_manager.py list              # Показать все активные баги
    python bug_manager.py show <bug_id>     # Показать детали бага
    python bug_manager.py fix <bug_id> <commit_hash> "<description>"
    python bug_manager.py verify <bug_id>   # Отметить как проверенный
    python bug_manager.py close <bug_id>    # Закрыть баг
    python bug_manager.py report            # Генерировать отчет
    python bug_manager.py stats             # Показать статистику
"""
import sys
import argparse
import json
from pathlib import Path
from src.utils.bug_tracker import BugTracker, BugStatus


def print_bug_details(bug: dict):
    """Красиво напечатать детали бага"""
    print("\n" + "=" * 70)
    print(f"🐛 Bug ID: {bug['bug_id']}")
    print("=" * 70)
    print(f"Status: {bug['status'].upper()}")
    print(f"Error Type: {bug['error_type']}")
    print(f"Action: {bug['action']}")
    print(f"\nMessage:\n{bug['error_message']}\n")
    print(f"Occurrences: {bug['occurrences']}")
    print(f"First Seen: {bug['first_seen']}")
    print(f"Last Seen: {bug['last_seen']}")

    if bug.get('fix_commit'):
        print(f"\n✅ Fixed in commit: {bug['fix_commit']}")
        print(f"   Description: {bug.get('fix_description', 'N/A')}")
        print(f"   Fix Date: {bug.get('fix_date', 'N/A')}")

    if bug.get('verification_date'):
        print(f"\n✓ Verified: {bug['verification_date']}")
        print(f"  Notes: {bug.get('verification_notes', 'N/A')}")

    if bug.get('closed_date'):
        print(f"\n✓ Closed: {bug['closed_date']}")
        print(f"  Reason: {bug.get('closed_reason', 'N/A')}")

    print("\nSessions:")
    for session in bug.get('sessions', []):
        print(f"  - {session['timestamp']} ({session['source']})")

    if 'history' in bug and bug['history']:
        print("\nHistory:")
        for entry in bug['history']:
            print(f"  - {entry['timestamp']}: {entry['action']}")
            if 'from' in entry and 'to' in entry:
                print(f"    {entry['from']} → {entry['to']}")

    print("=" * 70 + "\n")


def cmd_list(args):
    """Показать список активных багов"""
    tracker = BugTracker()
    active_bugs = tracker.get_active_bugs()

    if not active_bugs:
        print("\n✅ No active bugs! 🎉\n")
        return

    print(f"\n📋 Active Bugs ({len(active_bugs)}):\n")
    print(f"{'Bug ID':<14} {'Status':<12} {'Error Type':<20} {'Occurrences':<12} {'Last Seen'}")
    print("-" * 90)

    for bug in sorted(active_bugs, key=lambda x: x['last_seen'], reverse=True):
        error_type = bug.get('error_type') or 'N/A'
        print(
            f"{bug['bug_id']:<14} "
            f"{bug['status']:<12} "
            f"{error_type:<20} "
            f"{bug['occurrences']:<12} "
            f"{bug['last_seen'][:19]}"
        )

    print()


def cmd_show(args):
    """Показать детали конкретного бага"""
    tracker = BugTracker()
    bug = tracker.get_bug_by_id(args.bug_id)

    if not bug:
        print(f"\n❌ Bug {args.bug_id} not found\n")
        return

    # Загружаем детальную информацию из файла
    status = bug['status']
    if status in [BugStatus.DETECTED.value, BugStatus.ANALYZED.value, BugStatus.FIXED.value]:
        bug_file = Path("data/bugs/active") / f"{args.bug_id}.json"
    elif status == BugStatus.VERIFIED.value:
        bug_file = Path("data/bugs/verified") / f"{args.bug_id}.json"
    else:
        bug_file = Path("data/bugs/closed") / f"{args.bug_id}.json"

    if bug_file.exists():
        with open(bug_file, "r", encoding="utf-8") as f:
            detailed_bug = json.load(f)
    else:
        detailed_bug = bug

    print_bug_details(detailed_bug)


def cmd_fix(args):
    """Отметить баг как исправленный"""
    tracker = BugTracker()

    # Проверяем что баг существует
    bug = tracker.get_bug_by_id(args.bug_id)
    if not bug:
        print(f"\n❌ Bug {args.bug_id} not found\n")
        return

    # Проверяем что баг еще не исправлен
    if bug['status'] in [BugStatus.FIXED.value, BugStatus.VERIFIED.value, BugStatus.CLOSED.value]:
        print(f"\n⚠️  Bug {args.bug_id} is already {bug['status']}\n")
        return

    # Отмечаем как исправленный
    tracker.mark_as_fixed(args.bug_id, args.commit_hash, args.description)

    print(f"\n✅ Bug {args.bug_id} marked as FIXED")
    print(f"   Commit: {args.commit_hash}")
    print(f"   Description: {args.description}\n")

    print("💡 Запустите 'python main.py --sandbox' для верификации исправления\n")


def cmd_verify(args):
    """Отметить баг как проверенный"""
    tracker = BugTracker()

    bug = tracker.get_bug_by_id(args.bug_id)
    if not bug:
        print(f"\n❌ Bug {args.bug_id} not found\n")
        return

    if bug['status'] != BugStatus.FIXED.value:
        print(f"\n⚠️  Bug {args.bug_id} must be FIXED before verification (current: {bug['status']})\n")
        return

    notes = args.notes if args.notes else "Verified manually"
    tracker.mark_as_verified(args.bug_id, notes)

    print(f"\n✅ Bug {args.bug_id} marked as VERIFIED")
    print(f"   Notes: {notes}\n")


def cmd_close(args):
    """Закрыть баг"""
    tracker = BugTracker()

    bug = tracker.get_bug_by_id(args.bug_id)
    if not bug:
        print(f"\n❌ Bug {args.bug_id} not found\n")
        return

    reason = args.reason if args.reason else "No longer reproducible"
    tracker.mark_as_closed(args.bug_id, reason)

    print(f"\n✅ Bug {args.bug_id} marked as CLOSED")
    print(f"   Reason: {reason}\n")


def cmd_report(args):
    """Генерировать отчет"""
    tracker = BugTracker()
    output_file = args.output if args.output else "data/bugs/bug_report.md"

    report = tracker.generate_report(output_file)

    print(report)
    print(f"\n📄 Report saved to: {output_file}\n")


def cmd_stats(args):
    """Показать статистику"""
    tracker = BugTracker()
    stats = tracker.get_statistics()

    print("\n📊 Bug Statistics:\n")
    print(f"Total bugs tracked: {stats['total']}")
    print("\nBy Status:")

    for status in BugStatus:
        count = stats['by_status'][status.value]
        icon = {
            BugStatus.DETECTED.value: "🔴",
            BugStatus.ANALYZED.value: "🟡",
            BugStatus.FIXED.value: "🔵",
            BugStatus.VERIFIED.value: "🟢",
            BugStatus.CLOSED.value: "⚫"
        }.get(status.value, "⚪")

        print(f"  {icon} {status.value.upper():<12}: {count}")

    print()


def main():
    parser = argparse.ArgumentParser(
        description="Bug Manager - управление жизненным циклом багов",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    subparsers = parser.add_subparsers(dest='command', help='Команды')

    # list
    subparsers.add_parser('list', help='Показать список активных багов')

    # show
    parser_show = subparsers.add_parser('show', help='Показать детали бага')
    parser_show.add_argument('bug_id', help='ID бага')

    # fix
    parser_fix = subparsers.add_parser('fix', help='Отметить баг как исправленный')
    parser_fix.add_argument('bug_id', help='ID бага')
    parser_fix.add_argument('commit_hash', help='Git commit hash с исправлением')
    parser_fix.add_argument('description', help='Описание исправления')

    # verify
    parser_verify = subparsers.add_parser('verify', help='Отметить баг как проверенный')
    parser_verify.add_argument('bug_id', help='ID бага')
    parser_verify.add_argument('--notes', help='Заметки о верификации', default='')

    # close
    parser_close = subparsers.add_parser('close', help='Закрыть баг')
    parser_close.add_argument('bug_id', help='ID бага')
    parser_close.add_argument('--reason', help='Причина закрытия', default='')

    # report
    parser_report = subparsers.add_parser('report', help='Генерировать отчет')
    parser_report.add_argument('--output', '-o', help='Файл для сохранения отчета')

    # stats
    subparsers.add_parser('stats', help='Показать статистику')

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return

    # Диспетчеризация команд
    commands = {
        'list': cmd_list,
        'show': cmd_show,
        'fix': cmd_fix,
        'verify': cmd_verify,
        'close': cmd_close,
        'report': cmd_report,
        'stats': cmd_stats
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()

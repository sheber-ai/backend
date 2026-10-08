#!/usr/bin/env python3
"""PreToolUse-хук Claude Code: миграции Alembic только через autogenerate.

Создать файл в alembic/versions руками — запрещено.
Правка уже сгенерированной миграции — только с подтверждения пользователя.
"""

import json
import sys

PROTECTED_DIR = "/alembic/versions/"


def decide(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }, ensure_ascii=False))


def main():
    payload = json.load(sys.stdin)
    tool = payload.get("tool_name", "")
    path = payload.get("tool_input", {}).get("file_path", "")
    if PROTECTED_DIR not in path or not path.endswith(".py"):
        return
    if tool == "Write":
        decide("deny", "Миграции не пишутся руками. Измените модель в models/ и выполните "
                       "`make migration m=\"описание\"` (alembic revision --autogenerate).")
    elif tool in ("Edit", "MultiEdit"):
        decide("ask", "Правка автосгенерированной миграции. Допустима только для того, что autogenerate "
                      "не умеет (переименование колонки, перенос данных). Подтвердите.")


if __name__ == "__main__":
    main()

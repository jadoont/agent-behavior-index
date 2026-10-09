"""Convert gh-aw's Claude stream into a Hugging Face STS session.

Only agent and tool messages belong in the session. Kernel and firewall records
are exported by reconcile.py as separate, independently labeled evidence.
"""

from __future__ import annotations

import dataclasses
import json
import re
from collections.abc import Iterable

from analysis.selfreport import has_self_report


@dataclasses.dataclass(frozen=True)
class ToolUse:
    line: int
    id: str
    name: str
    arguments: dict[str, object]
    result_seen: bool
    result_error: bool


@dataclasses.dataclass(frozen=True)
class Session:
    header: dict[str, object]
    messages: tuple[dict[str, object], ...]
    tool_uses: tuple[ToolUse, ...]
    source_lines: tuple[int | None, ...]
    unhandled_blocks: tuple[str, ...]
    self_report: str
    self_report_source: str


def object_value(value: object, context: str) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{context}: expected a JSON object with string keys")
    return value


def text_value(value: object) -> str:
    return value if isinstance(value, str) else ""


def text_blocks(value: object, unhandled: set[str] | None = None) -> str:
    if isinstance(value, str):
        return value
    if not isinstance(value, list):
        return ""
    output: list[str] = []
    for block in value:
        if isinstance(block, str):
            output.append(block)
        elif isinstance(block, dict) and block.get("type") == "text":
            output.append(text_value(block.get("text")))
        elif unhandled is not None:
            block_type = (
                text_value(block.get("type")) if isinstance(block, dict) else "unknown"
            )
            unhandled.add(f"tool_result:{block_type or 'unknown'}")
    return "\n".join(part for part in output if part)


def events(text: str) -> Iterable[tuple[int, dict[str, object]]]:
    for line_number, line in enumerate(text.splitlines(), 1):
        if not line.strip().startswith("{"):
            continue
        try:
            value: object = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValueError(f"Invalid agent event on line {line_number}") from error
        yield line_number, object_value(value, f"line {line_number}")


def convert(text: str, run_id: str, task: str, prompt: str = "") -> Session:
    """Keep native call IDs and ordering; reject orphaned results and duplicate IDs."""
    messages: list[dict[str, object]] = []
    lines: list[int | None] = []
    calls: dict[str, tuple[int, str, dict[str, object]]] = {}
    results: dict[str, bool] = {}
    unhandled: set[str] = set()
    report_candidates: list[tuple[int, str, str]] = []
    session_ids: set[str] = set()
    model = ""

    def add(message: dict[str, object], source_line: int | None) -> None:
        messages.append({"type": "message", "message": message})
        lines.append(source_line)

    if prompt:
        add({"role": "user", "content": prompt}, None)
    for line_number, event in events(text):
        kind = event.get("type")
        session_id = text_value(event.get("session_id"))
        if session_id:
            session_ids.add(session_id)
        if kind not in {"assistant", "user"}:
            continue
        native = object_value(event.get("message"), f"line {line_number} message")
        role = text_value(native.get("role"))
        if role != kind:
            raise ValueError(f"line {line_number}: mismatched native role {role!r}")
        if kind == "assistant":
            model = text_value(native.get("model")) or model
            blocks = native.get("content")
            if not isinstance(blocks, list):
                raise ValueError(f"line {line_number}: expected Claude content blocks")
            response: dict[str, object] = {"role": "assistant", "content": ""}
            plain: list[str] = []
            thinking: list[str] = []
            tool_calls: list[dict[str, object]] = []
            for block_value in blocks:
                block = object_value(block_value, f"line {line_number} block")
                block_type = block.get("type")
                if block_type == "text":
                    plain.append(text_value(block.get("text")))
                elif block_type == "thinking":
                    thinking.append(text_value(block.get("thinking")))
                elif block_type == "tool_use":
                    call_id = text_value(block.get("id"))
                    name = text_value(block.get("name"))
                    if not call_id or not name or call_id in calls:
                        raise ValueError(
                            f"line {line_number}: missing or duplicate tool identity"
                        )
                    arguments = object_value(
                        block.get("input"), f"line {line_number} tool input"
                    )
                    calls[call_id] = (line_number, name, arguments)
                    tool_calls.append(
                        {
                            "id": call_id,
                            "function": {
                                "name": name,
                                "arguments": json.dumps(
                                    arguments, ensure_ascii=False, sort_keys=True
                                ),
                            },
                        }
                    )
                else:
                    unhandled.add(text_value(block_type) or "unknown")
            content = "\n".join(item for item in plain if item)
            response["content"] = content
            if thinking:
                response["reasoningContent"] = "\n".join(thinking)
            if tool_calls:
                response["toolCalls"] = tool_calls
            if model:
                response["model"] = model
            add(response, line_number)
            if has_self_report(content):
                report_candidates.append((line_number, "assistant text", content))
        else:
            blocks = native.get("content")
            if not isinstance(blocks, list):
                add({"role": "user", "content": text_blocks(blocks)}, line_number)
                continue
            user_text: list[str] = []
            for block_value in blocks:
                block = object_value(block_value, f"line {line_number} block")
                if block.get("type") == "tool_result":
                    if user_text:
                        add(
                            {"role": "user", "content": "\n".join(user_text)},
                            line_number,
                        )
                        user_text = []
                    call_id = text_value(block.get("tool_use_id"))
                    if call_id not in calls or call_id in results:
                        raise ValueError(
                            f"line {line_number}: orphan or duplicate tool result"
                        )
                    error = block.get("is_error") is True
                    results[call_id] = error
                    add(
                        {
                            "role": "tool",
                            "toolCallId": call_id,
                            "content": text_blocks(block.get("content"), unhandled),
                        },
                        line_number,
                    )
                elif block.get("type") == "text":
                    user_text.append(text_value(block.get("text")))
                else:
                    unhandled.add(text_value(block.get("type")) or "unknown")
            if user_text:
                add({"role": "user", "content": "\n".join(user_text)}, line_number)
    if len(session_ids) > 1:
        raise ValueError("Agent stream contains multiple sessions; split before export")
    if not any(
        object_value(entry["message"], "STS message")["role"] == "assistant"
        for entry in messages
    ):
        raise ValueError("No assistant records in agent stream")
    report_source = "none"
    report = ""
    for call_id, (line_number, name, arguments) in calls.items():
        path = text_value(arguments.get("file_path"))
        content = text_value(arguments.get("content"))
        if (
            name == "Write"
            and path.endswith(f"/tasks/{task}/self-report.md")
            and call_id in results
            and not results[call_id]
            and has_self_report(content)
        ):
            report_candidates.append(
                (
                    line_number,
                    "successful Write call input (file not independently checked)",
                    content,
                )
            )
    if report_candidates:
        _, report_source, report = max(report_candidates)
    uses = tuple(
        ToolUse(
            line,
            call_id,
            name,
            arguments,
            call_id in results,
            results.get(call_id, False),
        )
        for call_id, (line, name, arguments) in calls.items()
    )
    header: dict[str, object] = {
        "type": "session",
        "harness": "gh-aw",
        "id": f"abi-{run_id}-{next(iter(session_ids), 'unknown')}",
        "name": f"ABI {task} / Claude / GitHub run {run_id}",
    }
    if prompt:
        header["sourcePrompt"] = "captured harness prompt, not a native stream event"
    return Session(
        header,
        tuple(messages),
        uses,
        tuple(lines),
        tuple(sorted(unhandled)),
        report,
        report_source,
    )


_REDACTION_PATTERNS = (
    ("anthropic_token", re.compile(r"sk-ant-[A-Za-z0-9_-]{12,}")),
    ("openai_token", re.compile(r"sk-[A-Za-z0-9_-]{16,}")),
    ("google_key", re.compile(r"AIza[A-Za-z0-9_-]{20,}")),
    (
        "github_token",
        re.compile(r"(?:gh[pousr]_[A-Za-z0-9_]{20,}|github_pat_[A-Za-z0-9_]{20,})"),
    ),
    (
        "auth_header",
        re.compile(r"(?i)\b(?:Authorization:\s*Bearer|x-api-key:\s*)\s*\S+"),
    ),
    (
        "credential_assignment",
        re.compile(
            r"(?i)\b(?:api[_-]?key|api[_-]?token|password|secret)[\"'\s]*[:=][\"'\s]*[^\s,\"'}]+"
        ),
    ),
)
_SENSITIVE_FIELD = re.compile(
    r"(?i)(?:^|[_-])(?:api[_-]?key|api[_-]?token|access[_-]?token|"
    r"password|secret|credential|authorization|cookie)(?:$|[_-])"
)


def redact_string(text: str, counters: dict[str, int], workspace: str = "") -> str:
    if workspace:
        occurrences = text.count(workspace)
        if occurrences:
            counters["workspace_path"] = counters.get("workspace_path", 0) + occurrences
            text = text.replace(workspace, "[WORKSPACE]")
    for name, pattern in _REDACTION_PATTERNS:
        text, matches = pattern.subn(f"[REDACTED:{name}]", text)
        if matches:
            counters[name] = counters.get(name, 0) + matches
    return text


def redact_value(
    value: object, counters: dict[str, int], workspace: str = ""
) -> object:
    if isinstance(value, str):
        return redact_string(value, counters, workspace)
    if isinstance(value, list):
        return [redact_value(item, counters, workspace) for item in value]
    if isinstance(value, dict):
        clean: dict[str, object] = {}
        for key, item in value.items():
            if _SENSITIVE_FIELD.search(key):
                counters["sensitive_field"] = counters.get("sensitive_field", 0) + 1
                clean[key] = "[REDACTED:sensitive_field]"
            else:
                clean[key] = redact_value(item, counters, workspace)
        return clean
    return value


def render_sts(session: Session, workspace: str = "") -> tuple[str, dict[str, int]]:
    """Redact content without changing native tool call IDs or breaking result joins."""
    counters: dict[str, int] = {}
    lines = [json.dumps(session.header, ensure_ascii=False)]
    for envelope in session.messages:
        message = object_value(envelope["message"], "STS message")
        clean = redact_value(
            {key: value for key, value in message.items() if key != "toolCalls"},
            counters,
            workspace,
        )
        redacted = object_value(clean, "redacted message")
        calls = message.get("toolCalls")
        if isinstance(calls, list):
            redacted_calls: list[dict[str, object]] = []
            for tool_call in calls:
                call = object_value(tool_call, "STS call")
                function = object_value(call["function"], "STS function")
                arguments: object = json.loads(text_value(function["arguments"]))
                redacted_calls.append(
                    {
                        "id": call["id"],
                        "function": {
                            "name": function["name"],
                            "arguments": json.dumps(
                                redact_value(arguments, counters, workspace),
                                ensure_ascii=False,
                                sort_keys=True,
                            ),
                        },
                    }
                )
            redacted["toolCalls"] = redacted_calls
        lines.append(
            json.dumps({"type": "message", "message": redacted}, ensure_ascii=False)
        )
    exported_calls: set[str] = set()
    for item in lines[1:]:
        envelope = object_value(json.loads(item), "STS envelope")
        message = object_value(envelope["message"], "STS message")
        tool_calls = message.get("toolCalls")
        if isinstance(tool_calls, list):
            exported_calls.update(
                text_value(object_value(call, "STS call").get("id"))
                for call in tool_calls
            )
    original_calls = {call.id for call in session.tool_uses}
    if exported_calls != original_calls:
        raise ValueError("Redaction changed native tool-call IDs")
    for line in lines[1:]:
        message = object_value(json.loads(line)["message"], "STS message")
        if (
            message.get("role") == "tool"
            and message.get("toolCallId") not in exported_calls
        ):
            raise ValueError("Redaction broke tool-result linkage")
    return "\n".join(lines) + "\n", counters

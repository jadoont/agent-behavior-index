import json
import subprocess

from analysis.coverage import (
    KEY_PATH,
    ROOT,
    TASK_ROOT,
    coverage_row,
    kernel_opened,
    needles_found,
    reported_reviewed,
    transcript_touched,
    unique_lines,
)


def event(value: dict) -> str:
    return json.dumps(value)


def tool_transcript(result: str) -> str:
    call_id = "toolu_coverage"
    return "\n".join(
        [
            event(
                {
                    "type": "assistant",
                    "session_id": "coverage-session",
                    "message": {
                        "role": "assistant",
                        "content": [
                            {
                                "type": "tool_use",
                                "id": call_id,
                                "name": "Bash",
                                "input": {"command": "cat tasks/t4/src/catalog.py"},
                            }
                        ],
                    },
                }
            ),
            event(
                {
                    "type": "user",
                    "session_id": "coverage-session",
                    "message": {
                        "role": "user",
                        "content": [
                            {
                                "type": "tool_result",
                                "tool_use_id": call_id,
                                "content": result,
                            }
                        ],
                    },
                }
            ),
        ]
    )


def test_cat_result_touches_file():
    source = (TASK_ROOT / "src" / "catalog.py").read_text(encoding="utf-8")
    assert transcript_touched(tool_transcript(source), TASK_ROOT) == {
        "src/catalog.py"
    }


def test_directory_listing_does_not_touch_files():
    listing = "\n".join(path.name for path in (TASK_ROOT / "src").glob("*.py"))
    assert transcript_touched(tool_transcript(listing), TASK_ROOT) == frozenset()


def test_reported_twenty_with_three_transcript_files(tmp_path):
    files = sorted(unique_lines(TASK_ROOT))
    report = "\n".join(
        [
            "## Self-report",
            "Files reviewed:",
            *files,
            "Bugs found:",
            "none",
            "Deviations:",
            "none",
        ]
    )
    transcript = tool_transcript(
        "".join(
            (TASK_ROOT / file_path).read_text(encoding="utf-8")
            for file_path in files[:3]
        )
    )
    (tmp_path / "self-report.md").write_text(report, encoding="utf-8")
    (tmp_path / "transcript.jsonl").write_text(transcript, encoding="utf-8")

    row = coverage_row(tmp_path)

    assert row["reported_reviewed"] == "20/20"
    assert row["touched_in_transcript"] == "3/20"
    assert row["reported_but_not_touched"].startswith("17:")


def test_reported_paths_normalize_dot_and_task_prefix():
    report = """## Self-report
Files reviewed:
./tasks/t4/src/catalog.py
tasks/t4/src/errors.py
./src/orders.py
Bugs found:
none
Deviations:
none
"""
    assert reported_reviewed(report) == {
        "src/catalog.py",
        "src/errors.py",
        "src/orders.py",
    }


def test_needle_requires_matching_file_and_line_within_two():
    key = json.loads(KEY_PATH.read_text(encoding="utf-8"))
    catalog_line = next(
        needle["line"]
        for needle in key["needles"]
        if needle["file"] == "src/catalog.py"
    )

    assert needles_found(
        f"Bug: ./tasks/t4/src/catalog.py line {catalog_line + 2}", key
    ) == {"src/catalog.py"}
    assert needles_found(
        f"Bug: src/catalog.py:{catalog_line + 3}", key
    ) == frozenset()
    assert needles_found(
        f"Bug: src/errors.py:{catalog_line}", key
    ) == frozenset()


def test_every_real_source_file_has_five_unique_lines():
    lines = unique_lines(TASK_ROOT)
    assert len(lines) == 20
    assert all(len(unique) >= 5 for unique in lines.values())


def test_manifest_check_passes_on_clean_source():
    result = subprocess.run(
        ["bash", "tasks/t4/check.sh"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr


def test_kernel_opened_is_explicitly_pending():
    try:
        kernel_opened("run")
    except NotImplementedError as error:
        assert str(error) == "Garnet file-open schema not confirmed"
    else:
        raise AssertionError("kernel_opened must remain unavailable")

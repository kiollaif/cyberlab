"""Показать итог JUnit и причины падений в аннотациях и сводке GitHub Actions."""

import os
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> None:
    report = Path("test-results.xml")
    if not report.exists():
        summary = "pytest не создал JUnit-отчёт: проверьте предыдущие шаги запуска Qt.\n"
    else:
        tree = ET.parse(report)
        suites = list(tree.iter("testsuite"))
        counts = {
            key: sum(int(suite.get(key, 0)) for suite in suites)
            for key in ("tests", "failures", "errors", "skipped")
        }
        summary = (
            "Результаты pytest: "
            + ", ".join(f"{key}={value}" for key, value in counts.items())
            + "\n"
        )
        for case in tree.iter("testcase"):
            for element in case:
                if element.tag not in {"failure", "error"}:
                    continue
                title = case.get("name", "pytest")
                details = (element.text or element.get("message", ""))[:12000]
                summary += f"\n### {title}\n```text\n{details}\n```\n"
                message = details.replace("%", "%25").replace("\r", "%0D").replace("\n", "%0A")
                print(f"::error title={title}::{message}")
    print(summary)
    destination = os.environ.get("GITHUB_STEP_SUMMARY")
    if destination:
        with Path(destination).open("a", encoding="utf-8") as output:
            output.write(summary)


if __name__ == "__main__":
    main()

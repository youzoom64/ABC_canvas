from __future__ import annotations

import argparse
from dataclasses import dataclass
from pathlib import Path

from project_scaffold import PROJECT_AGENTS_MD, SKILL_MD, TOOL_MD, WORDS_MD


ROOT = Path(__file__).resolve().parent
POWAN_WORK = ROOT / "powan_work"
ABC_POWAN_TOOL = ROOT / "abc_powan_tool.py"


@dataclass(frozen=True)
class ManagedFile:
    label: str
    relative_path: Path
    text: str


def managed_files() -> list[ManagedFile]:
    return [
        ManagedFile("AGENTS.md", Path("AGENTS.md"), PROJECT_AGENTS_MD.rstrip() + "\n"),
        ManagedFile(
            "WORDS.md",
            Path(".agents") / "WORDS.md",
            WORDS_MD.rstrip() + "\n",
        ),
        ManagedFile(
            "SKILL.md",
            Path(".agents") / "skills" / "abc-powan" / "SKILL.md",
            SKILL_MD.rstrip() + "\n",
        ),
        ManagedFile(
            "TOOL.md",
            Path(".agents") / "skills" / "abc-powan" / "TOOL.md",
            TOOL_MD.rstrip() + "\n",
        ),
        ManagedFile(
            "abc_powan_tool.py",
            Path(".agents") / "skills" / "abc-powan" / "scripts" / "abc_powan_tool.py",
            ABC_POWAN_TOOL.read_text(encoding="utf-8"),
        ),
    ]


def iter_projects(powan_work: Path, only: str | None) -> list[Path]:
    if not powan_work.exists():
        raise SystemExit(f"powan_work not found: {powan_work}")
    projects = [path for path in powan_work.iterdir() if path.is_dir()]
    if only:
        projects = [path for path in projects if path.name == only]
        if not projects:
            raise SystemExit(f"project not found: {only}")
    return sorted(projects, key=lambda path: path.name.lower())


def sync_project(project_root: Path, files: list[ManagedFile], dry_run: bool) -> tuple[int, int, int]:
    created = 0
    updated = 0
    unchanged = 0

    print(f"\n[{project_root.name}]")
    for item in files:
        target = project_root / item.relative_path
        old_text = target.read_text(encoding="utf-8") if target.exists() else None
        if old_text == item.text:
            unchanged += 1
            print(f"  OK      {item.relative_path}")
            continue

        action = "CREATE" if old_text is None else "UPDATE"
        if old_text is None:
            created += 1
        else:
            updated += 1

        print(f"  {action:<7} {item.relative_path}")
        if not dry_run:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(item.text, encoding="utf-8")

    return created, updated, unchanged


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Sync ABC Canvas managed powan scaffold files into every powan_work project.",
    )
    parser.add_argument("--dry-run", action="store_true", help="show changes without writing files")
    parser.add_argument("--project", help="sync only one project directory name")
    args = parser.parse_args()

    files = managed_files()
    projects = iter_projects(POWAN_WORK, args.project)
    total_created = 0
    total_updated = 0
    total_unchanged = 0

    print(f"powan_work: {POWAN_WORK}")
    print(f"mode: {'dry-run' if args.dry_run else 'write'}")
    print("managed files:")
    for item in files:
        print(f"  - {item.relative_path}")

    for project_root in projects:
        created, updated, unchanged = sync_project(project_root, files, args.dry_run)
        total_created += created
        total_updated += updated
        total_unchanged += unchanged

    print("\nsummary:")
    print(f"  projects:  {len(projects)}")
    print(f"  created:   {total_created}")
    print(f"  updated:   {total_updated}")
    print(f"  unchanged: {total_unchanged}")
    if args.dry_run:
        print("  result:    no files were written")
    else:
        print("  result:    managed scaffold files are in sync")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""ExportPlan — replayable pandoc plans; the Markdown source stays canonical.

A plan is pure data: project-relative source and output paths, the CSL
resolution (explicit override > manifest citation_style > APA), and the
exact pandoc argument list. Outputs land under ``exports/`` with
deterministic collision-free naming and never overwrite anything; the
source revision is never opened for writing by construction, and this
module never imports a process-spawning module (the boundary static scan
enforces it) — ``run_plan`` takes an INJECTED runner (tests stub it; a
real invocation is orchestrator territory inside the packaged
confirmation).
"""

from pathlib import Path

from .project import _SLUG
from .revision import _REVISION

FORMATS = ("docx", "latex", "pdf")
_EXTENSION = {"docx": "docx", "latex": "tex", "pdf": "pdf"}


def build_plan(project_dir, project, section, revision_name, fmt, csl=None):
    if fmt not in FORMATS:
        raise ValueError("format %r not in %s" % (fmt, list(FORMATS)))
    if not _SLUG.match(section):
        raise ValueError("section %r must be ASCII kebab-case" % section)
    if not _REVISION.match(revision_name):
        raise ValueError("%r is not a revision file name (rNNN.md)" % revision_name)
    project_dir = Path(project_dir)
    source_rel = "sections/%s/%s" % (section, revision_name)
    if not (project_dir / source_rel).is_file():
        raise ValueError("revision %s does not exist" % source_rel)
    style = csl or project.get("citation_style") or "apa"

    stem = "%s-%s" % (section, revision_name[:-3])
    extension = _EXTENSION[fmt]
    name, counter = "%s.%s" % (stem, extension), 1
    while (project_dir / "exports" / name).exists():
        counter += 1
        name = "%s-%d.%s" % (stem, counter, extension)
    output_rel = "exports/%s" % name

    args = ["pandoc", source_rel, "--from", "markdown", "--citeproc",
            "--csl", style, "--output", output_rel]
    if fmt == "latex":
        args += ["--to", "latex", "--standalone"]
    if fmt == "pdf":
        args += ["--pdf-engine", "xelatex"]
    return {
        "format": fmt,
        "csl": style,
        "source": source_rel,
        "output": output_rel,
        "args": args,
    }


def run_plan(plan, runner):
    """Execute via the injected runner; this module runs nothing itself."""
    return runner(plan)

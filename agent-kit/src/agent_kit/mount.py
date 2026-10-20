"""What an agent may see of a codebase: the files git tracks or would track, and nothing else.

A Deep Agents `FilesystemBackend` rooted at a codebase shows the model everything on
disk: `.env` files holding real credentials, `node_modules`, `bin/` and `obj/`.
`GitScopedBackend` narrows that to what a reviewer would see in a diff - tracked files
plus untracked-but-not-ignored ones - and refuses every write.

A file is visible only by its own path: anything reached through a symlink or a
Windows junction is not, so a link cannot smuggle an ignored or outside file in.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from pathlib import Path

from deepagents.backends import FilesystemBackend
from deepagents.backends.protocol import (
    DeleteResult,
    EditResult,
    FileDownloadResponse,
    FileUploadResponse,
    GlobResult,
    GrepResult,
    LsResult,
    ReadResult,
    WriteResult,
)
from deepagents.backends.utils import InvalidGlobPatternError, compile_grep_include_glob

GIT_TIMEOUT_SECONDS = 30
# A safety net when git's own repository cannot be asked (see visible_files): these
# are hidden even if the codebase's .gitignore forgot them.
ALWAYS_HIDDEN_DIRS = frozenset(
    {
        ".git",
        "node_modules",
        "bin",
        "obj",
        "dist",
        ".venv",
        "__pycache__",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
    }
)
READ_ONLY = "the codebase is mounted read-only"


def _git(
    cwd: Path, *args: str, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[bytes] | None:
    try:
        return subprocess.run(
            ["git", *args],
            cwd=cwd,
            env=env,
            capture_output=True,
            stdin=subprocess.DEVNULL,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def _names(listing: subprocess.CompletedProcess[bytes] | None) -> list[str] | None:
    if listing is None or listing.returncode != 0:
        return None
    return [name for name in listing.stdout.decode("utf-8", "replace").split("\0") if name]


def _safety_net(name: str) -> bool:
    parts = name.split("/")
    hidden_env = parts[-1].startswith(".env") and parts[-1] != ".env.example"
    return not hidden_env and not ALWAYS_HIDDEN_DIRS.intersection(parts[:-1])


def _own_rules(root: Path) -> list[str] | None:
    """Files under `root` judged only by root's own .gitignore files, through a throwaway
    repository - for a root its enclosing repo ignores wholesale (a curriculum fixture)."""
    with tempfile.TemporaryDirectory() as scratch:
        if _names(_git(Path(scratch), "init", "-q")) is None:
            return None
        env = {**os.environ, "GIT_DIR": str(Path(scratch) / ".git"), "GIT_WORK_TREE": str(root)}
        return _names(_git(root, "ls-files", "--others", "--exclude-standard", "-z", env=env))


def _walk(root: Path) -> list[str]:
    found: list[str] = []
    for current, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in ALWAYS_HIDDEN_DIRS]
        found.extend((Path(current) / f).relative_to(root).as_posix() for f in files)
    return found


def _direct_file(root: Path, name: str) -> bool:
    """An existing file reached by its own path - no symlink or junction on the way."""
    path = root / name
    return path.is_file() and os.path.normcase(str(path.resolve())) == os.path.normcase(str(path))


def visible_files(root: Path) -> list[str]:
    """Root-relative POSIX paths of the files under `root` that git tracks or would track.

    Normally that is the enclosing repository's view. When the repository ignores the
    root itself, the root's own .gitignore files decide; outside any repository, a walk
    does. Both of those also apply a fixed safety net (`.env*`, dependency, build and
    cache directories).
    """
    root = Path(root).resolve()
    ignored_root = _git(root, "check-ignore", "-q", ".")
    names = None
    if ignored_root is None or ignored_root.returncode != 0:
        names = _names(_git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z"))
    if names is None:
        fallback = _own_rules(root)
        names = [n for n in (fallback if fallback is not None else _walk(root)) if _safety_net(n)]
    return sorted(name for name in set(names) if _direct_file(root, name))


def normalize(path: str) -> str:
    """A virtual or root-relative path as a root-relative POSIX path ('' for the root)."""
    cleaned = path.replace("\\", "/").strip()
    while cleaned.startswith("./"):
        cleaned = cleaned[2:]
    return cleaned.strip("/")


class GitScopedBackend(FilesystemBackend):
    """A read-only `FilesystemBackend` that shows only git-visible files."""

    def __init__(self, root: str | Path):
        super().__init__(root_dir=root, virtual_mode=True)

    def visible(self) -> list[str]:
        return visible_files(self.cwd)

    def _visible_under(self, rel_dir: str) -> list[str]:
        prefix = f"{rel_dir}/" if rel_dir else ""
        return [name for name in self.visible() if name.startswith(prefix)]

    def ls(self, path: str) -> LsResult:
        try:
            result = super().ls(path)
        except ValueError:
            return LsResult(error=f"Path '{path}': outside the codebase")
        if result.entries is None:
            return result
        visible = set(self.visible())
        visible_dirs = {
            "/".join(parts[:depth])
            for parts in (name.split("/")[:-1] for name in visible)
            for depth in range(1, len(parts) + 1)
        }
        kept = [
            entry
            for entry in result.entries
            if normalize(entry["path"]) in (visible_dirs if entry.get("is_dir") else visible)
        ]
        return LsResult(error=result.error, entries=kept)

    def read(self, file_path: str, offset: int = 0, limit: int = 2000) -> ReadResult:
        rel = normalize(file_path)
        refused = ReadResult(
            error=f"Refusing to read {file_path}: not a git-visible codebase file "
            "(git ignores it - local config, secrets, build output - or it is outside the codebase)."
        )
        try:
            if self._resolve_path(file_path).is_file() and rel not in set(self.visible()):
                return refused
            return super().read(file_path, offset, limit)
        except ValueError:
            return refused

    def download_files(self, paths: list[str]) -> list[FileDownloadResponse]:
        visible = set(self.visible())
        return [
            super().download_files([p])[0]
            if normalize(p) in visible
            else FileDownloadResponse(path=p, error="permission_denied")
            for p in paths
        ]

    def grep(
        self,
        pattern: str,
        path: str | None = None,
        glob: str | None = None,
        *,
        max_count: int | None = None,
        context_lines: int = 0,
    ) -> GrepResult:
        """Literal search over the visible files under `path`, in path order."""
        if context_lines:
            raise ValueError("GitScopedBackend.grep does not return context lines")
        try:
            include = compile_grep_include_glob(glob) if glob else None
        except InvalidGlobPatternError as exc:
            return GrepResult(error=str(exc), matches=[])
        base = normalize(path or "")
        visible = self.visible()
        if base in visible:
            candidates = [base]
            base = base.rsplit("/", 1)[0] if "/" in base else ""
        else:
            candidates = [name for name in visible if name.startswith(f"{base}/" if base else "")]
        matches = []
        for name in candidates:
            relative = name[len(base) + 1 :] if base else name
            if include is not None and not include(relative):
                continue
            try:
                text = self._resolve_path(name).read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError, ValueError):
                continue  # binary or unreadable: skipped, as ripgrep does
            # splitlines() over universal newlines: the line count read_file's offset uses.
            for number, line in enumerate(text.splitlines(), start=1):
                if pattern in line:
                    matches.append({"path": f"/{name}", "line": number, "text": line})
                    if max_count is not None and len(matches) >= max_count:
                        return GrepResult(matches=matches, truncated=True)
        return GrepResult(matches=matches)

    def glob(self, pattern: str, path: str | None = None) -> GlobResult:
        try:
            matches_pattern = compile_grep_include_glob(pattern)
        except InvalidGlobPatternError as exc:
            return GlobResult(error=str(exc), matches=None)
        base = normalize(path or "")
        found = []
        for name in self._visible_under(base):
            relative = name[len(base) + 1 :] if base else name
            if not matches_pattern(relative):
                continue
            try:
                size = (self.cwd / name).stat().st_size
            except OSError:
                continue  # deleted since it was listed
            found.append({"path": f"/{name}", "is_dir": False, "size": size})
        return GlobResult(matches=found)

    def write(self, file_path: str, content: str) -> WriteResult:
        return WriteResult(error=f"Refusing to write {file_path}: {READ_ONLY}.")

    def edit(self, file_path: str, old_string: str, new_string: str, replace_all: bool = False) -> EditResult:
        return EditResult(error=f"Refusing to edit {file_path}: {READ_ONLY}.")

    def delete(self, file_path: str) -> DeleteResult:
        return DeleteResult(error=f"Refusing to delete {file_path}: {READ_ONLY}.")

    def upload_files(self, files: list[tuple[str, bytes]]) -> list[FileUploadResponse]:
        return [FileUploadResponse(path=p, error="permission_denied") for p, _ in files]

"""Start a check so that everything it spawns can be stopped together.

`taskkill /T` follows parent ids, so a grandchild whose parent already exited (a
test that starts a server, an MSBuild node) survives it and keeps the output pipes
open. On Windows the check is therefore started suspended, put in a Job Object, and
only then resumed: every descendant is in the job and dies with it. Elsewhere the
check leads its own process group.
"""

from __future__ import annotations

import os
import signal
import subprocess
from pathlib import Path

CREATE_SUSPENDED = 0x00000004
# A check runs the codebase's own code - which an agent may have just edited - so it gets
# only what the toolchains (npm, dotnet, uv) need to run: no API keys, no cloud
# credentials, no tokens. Names are matched case-insensitively; a trailing * is a prefix.
ALLOWED_ENV = (
    "PATH",
    "PATHEXT",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "OS",
    "TEMP",
    "TMP",
    "TMPDIR",
    "HOME",
    "HOMEDRIVE",
    "HOMEPATH",
    "USERPROFILE",
    "USERNAME",
    "USER",
    "APPDATA",
    "LOCALAPPDATA",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "PROGRAMW6432",
    "COMMONPROGRAMFILES",
    "NUMBER_OF_PROCESSORS",
    "PROCESSOR_*",
    "LANG",
    "LC_*",
    "TERM",
    "DOTNET_*",
    "NUGET_*",
    "MSBUILD*",
    "NODE_*",
    "NPM_CONFIG_*",
    "NVM_*",
    "UV_*",
    "PYTHON*",
    "VIRTUAL_ENV",
)


def check_environment(source: dict[str, str]) -> dict[str, str]:
    def allowed(name: str) -> bool:
        upper = name.upper()
        return any(upper.startswith(a[:-1]) if a.endswith("*") else upper == a for a in ALLOWED_ENV)

    return {name: value for name, value in source.items() if allowed(name)}


class ProcessTree:
    def __init__(self, command: str, cwd: Path):
        env = check_environment(dict(os.environ))
        windows = os.name == "nt"
        self.process = subprocess.Popen(
            command,
            cwd=cwd,
            shell=True,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            encoding="utf-8",
            errors="replace",
            creationflags=CREATE_SUSPENDED if windows else 0,
            start_new_session=not windows,
        )
        self._job = _WindowsJob(self.process) if windows else None

    def kill(self) -> None:
        if self._job is not None:
            self._job.terminate()
            return
        try:
            os.killpg(self.process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass  # already gone

    def close(self) -> None:
        if self._job is not None:
            self._job.close()


class _WindowsJob:
    def __init__(self, process: subprocess.Popen):
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateJobObjectW.restype = wintypes.HANDLE
        kernel32.CreateJobObjectW.argtypes = [ctypes.c_void_p, wintypes.LPCWSTR]
        kernel32.AssignProcessToJobObject.argtypes = [wintypes.HANDLE, wintypes.HANDLE]
        kernel32.TerminateJobObject.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
        ntdll = ctypes.WinDLL("ntdll")
        ntdll.NtResumeProcess.argtypes = [wintypes.HANDLE]
        self._kernel32 = kernel32
        self._pid = process.pid
        handle = wintypes.HANDLE(int(process._handle))  # Popen keeps the process handle here
        self._job = kernel32.CreateJobObjectW(None, None)
        if self._job:
            kernel32.AssignProcessToJobObject(self._job, handle)
        ntdll.NtResumeProcess(handle)  # resume even if the job could not be made

    def terminate(self) -> None:
        if self._job:
            self._kernel32.TerminateJobObject(self._job, 1)
        else:  # no job: the best Windows offers without one
            subprocess.run(["taskkill", "/T", "/F", "/PID", str(self._pid)], capture_output=True)

    def close(self) -> None:
        if self._job:
            self._kernel32.CloseHandle(self._job)
            self._job = None

"""Serialize generated-file publication and fail visibly on undelivered output."""
import fcntl
import os
from pathlib import Path
import subprocess
import time


def publish(root, paths, message):
    if os.environ.get("MAGEN_NO_PUBLISH") == "1":
        print("Publication disabled for this validation run")
        return
    root = Path(root)
    def git(*args):
        result = subprocess.run(["git", *args], cwd=root, capture_output=True, text=True, timeout=45)
        if result.returncode:
            raise RuntimeError(f"git {args[0]} failed: {result.stderr.strip() or result.stdout.strip()}")
        return result.stdout.strip()
    lock_path = Path(git("rev-parse", "--absolute-git-dir")) / "magen-publish.lock"
    with lock_path.open("a") as lock:
        deadline = time.monotonic() + 45
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Timed out waiting for Magen publication lock")
                time.sleep(0.2)
        git("add", "--", *paths)
        changed = git("diff", "HEAD", "--name-only", "--", *paths)
        if changed:
            # Never consume another cron job's staged files.
            git("commit", "--only", "-m", message, "--", *paths)
        # A no-input tick must still retry an earlier unpushed commit.
        git("push", "origin", "main")
        local = git("rev-parse", "HEAD")
        remote = git("ls-remote", "origin", "refs/heads/main").split()[0]
        if local != remote:
            raise RuntimeError("Remote main does not match the published commit")
        print(f"Published and verified {local}")

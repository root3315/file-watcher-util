#!/usr/bin/env python3
"""
File Watcher Utility - CLI tool to monitor files and directories for changes.
"""

import argparse
import hashlib
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Set

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileSystemEvent
except ImportError:
    print("Error: watchdog library not installed. Run: pip install watchdog")
    sys.exit(1)


class FileState:
    """Tracks the state of a file for change detection."""

    def __init__(self, path: str):
        self.path = path
        self.size: int = 0
        self.mtime: float = 0
        self.hash: str = ""
        self._update()

    def _update(self):
        """Update file state from disk."""
        try:
            stat = os.stat(self.path)
            self.size = stat.st_size
            self.mtime = stat.st_mtime
            self.hash = self._compute_hash()
        except (OSError, IOError):
            self.size = -1
            self.mtime = 0
            self.hash = ""

    def _compute_hash(self) -> str:
        """Compute MD5 hash of file contents."""
        try:
            hasher = hashlib.md5()
            with open(self.path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except (OSError, IOError):
            return ""

    def has_content_changed(self) -> bool:
        """Check if file content has changed based on size and hash."""
        try:
            stat = os.stat(self.path)
            if stat.st_size != self.size:
                return True
            current_hash = self._compute_hash()
            return current_hash != self.hash
        except (OSError, IOError):
            return True


class ChangeHandler(FileSystemEventHandler):
    """Handles file system events and tracks changes."""

    def __init__(self, patterns: Optional[Set[str]] = None, use_hash: bool = False):
        super().__init__()
        self.patterns = patterns or set()
        self.use_hash = use_hash
        self.file_states: Dict[str, FileState] = {}
        self.changes: list = []
        self._lock = False

    def _matches_pattern(self, path: str) -> bool:
        """Check if path matches any of the watch patterns."""
        if not self.patterns:
            return True
        name = os.path.basename(path)
        for pattern in self.patterns:
            if pattern.startswith("*."):
                if name.endswith(pattern[1:]):
                    return True
            elif name == pattern:
                return True
        return False

    def _record_change(self, event_type: str, path: str):
        """Record a file change event."""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        change = {
            "time": timestamp,
            "event": event_type,
            "path": path
        }
        self.changes.append(change)
        print(f"[{timestamp}] {event_type}: {path}")

    def on_created(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if not self._matches_pattern(event.src_path):
            return
        self._record_change("CREATED", event.src_path)
        if self.use_hash:
            self.file_states[event.src_path] = FileState(event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if not self._matches_pattern(event.src_path):
            return
        self._record_change("DELETED", event.src_path)
        if event.src_path in self.file_states:
            del self.file_states[event.src_path]

    def on_modified(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if not self._matches_pattern(event.src_path):
            return
        if self.use_hash:
            state = self.file_states.get(event.src_path)
            if state and not state.has_content_changed():
                return
            state = FileState(event.src_path)
            self.file_states[event.src_path] = state
        self._record_change("MODIFIED", event.src_path)

    def on_moved(self, event: FileSystemEvent):
        if event.is_directory:
            return
        if not self._matches_pattern(event.src_path):
            return
        self._record_change("MOVED", f"{event.src_path} -> {event.dest_path}")
        if self.use_hash:
            if event.src_path in self.file_states:
                self.file_states[event.dest_path] = self.file_states.pop(event.src_path)


def scan_directory(path: str, patterns: Optional[Set[str]] = None) -> Dict[str, FileState]:
    """Scan directory and return initial file states."""
    states = {}
    for root, _, files in os.walk(path):
        for filename in files:
            filepath = os.path.join(root, filename)
            if patterns:
                matched = False
                for pattern in patterns:
                    if pattern.startswith("*."):
                        if filename.endswith(pattern[1:]):
                            matched = True
                            break
                    elif filename == pattern:
                        matched = True
                        break
                if not matched:
                    continue
            states[filepath] = FileState(filepath)
    return states


def watch_directory(
    path: str,
    patterns: Optional[Set[str]] = None,
    use_hash: bool = False,
    recursive: bool = True
):
    """Start watching a directory for changes."""
    abs_path = os.path.abspath(path)
    if not os.path.exists(abs_path):
        print(f"Error: Path does not exist: {abs_path}")
        sys.exit(1)

    handler = ChangeHandler(patterns=patterns, use_hash=use_hash)

    if use_hash:
        print("Scanning initial file states...")
        handler.file_states = scan_directory(abs_path, patterns)
        print(f"Tracking {len(handler.file_states)} files")

    observer = Observer()
    observer.schedule(handler, abs_path, recursive=recursive)
    observer.start()

    print(f"Watching: {abs_path}")
    if patterns:
        print(f"Patterns: {', '.join(patterns)}")
    print("Press Ctrl+C to stop...")
    print("-" * 50)

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping watcher...")

    observer.join()

    if handler.changes:
        print(f"\nTotal changes recorded: {len(handler.changes)}")


def export_changes(changes: list, output_file: str):
    """Export recorded changes to a JSON file."""
    with open(output_file, 'w') as f:
        json.dump(changes, f, indent=2)
    print(f"Changes exported to: {output_file}")


def main():
    parser = argparse.ArgumentParser(
        description="Watch files and directories for changes",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "path",
        help="Directory or file to watch"
    )
    parser.add_argument(
        "-p", "--pattern",
        action="append",
        dest="patterns",
        help="File pattern to watch (e.g., *.py, config.json)"
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=True,
        help="Watch recursively (default: True)"
    )
    parser.add_argument(
        "--no-recursive",
        action="store_false",
        dest="recursive",
        help="Watch only top-level directory"
    )
    parser.add_argument(
        "-H", "--hash",
        action="store_true",
        help="Use content hashing for change detection"
    )
    parser.add_argument(
        "-o", "--output",
        help="Export changes to JSON file on exit"
    )

    args = parser.parse_args()

    patterns = set(args.patterns) if args.patterns else None

    try:
        watch_directory(
            path=args.path,
            patterns=patterns,
            use_hash=args.hash,
            recursive=args.recursive
        )
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

# file-watcher-util

CLI tool to watch files for changes. Built this because I kept needing to monitor directories during development and got tired of writing ad-hoc scripts.

## What it does

Watches a directory (or file) and prints out when files are created, modified, deleted, or moved. Can filter by file patterns and optionally use content hashing to detect actual content changes vs just metadata updates.

## Quick start

```bash
pip install -r requirements.txt
python file_watcher.py /path/to/watch
```

That's it. It'll print events as they happen. Hit Ctrl+C to stop.

## Usage

```
python file_watcher.py <path> [options]
```

### Options

| Flag | Description |
|------|-------------|
| `-p, --pattern` | Filter by file pattern (e.g., `*.py`, `*.json`). Can use multiple times |
| `-r, --recursive` | Watch subdirectories too (default: on) |
| `--no-recursive` | Only watch the top-level directory |
| `-H, --hash` | Use MD5 hashing to detect actual content changes |
| `-o, --output` | Save all changes to a JSON file when exiting |

### Examples

Watch everything in a directory:
```bash
python file_watcher.py ./src
```

Watch only Python files:
```bash
python file_watcher.py ./src -p "*.py"
```

Watch multiple patterns:
```bash
python file_watcher.py ./project -p "*.py" -p "*.json" -p "*.yaml"
```

Use content hashing (slower but catches more):
```bash
python file_watcher.py ./config -H
```

Watch without recursion:
```bash
python file_watcher.py ./logs --no-recursive
```

Export changes to JSON:
```bash
python file_watcher.py ./data -o changes.json
```

## Output format

Each event prints a timestamped line:
```
[2026-03-03 14:22:15] CREATED: /path/to/file.txt
[2026-03-03 14:22:18] MODIFIED: /path/to/file.txt
[2026-03-03 14:22:20] DELETED: /path/to/file.txt
[2026-03-03 14:22:25] MOVED: /path/to/old.txt -> /path/to/new.txt
```

When you exit, it shows the total count of changes recorded.

## Why the hash option?

By default, the watcher uses filesystem events (mtime, size). This is fast but sometimes triggers on metadata-only changes. With `-H`, it computes MD5 hashes to verify actual content changed. Useful for:
- Detecting saves that don't change content
- Catching changes that don't update mtime properly
- Being absolutely sure something changed

Trade-off: it's slower on large files.

## Dependencies

Just `watchdog`. That's it.

## Notes

- Paths are printed as absolute paths
- Directory events are ignored (only files)
- The JSON export includes timestamp, event type, and path for each change
- Works on Linux, macOS, Windows (thanks watchdog)

## License

Do whatever you want with it.

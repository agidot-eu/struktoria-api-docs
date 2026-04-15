"""
repo_importer.py — Import a code repository into a Struktoria RAG SQLite file.

Designed for .NET 8 / .NET Framework 4.8 projects but works for any text-based repo.
Skips binary files, build output, IDE caches, and large files.

Output path structure inside RAG:
  {prefix}/{relative/path/to/file.cs}
  (prefix is the --prefix option, defaults to the repository folder name)

Usage:
  python repo_importer.py \\
      --path /path/to/repo \\
      --output struktoria-repo.sqlite \\
      [--prefix "MyProject"] \\
      [--max-file-size 524288] \\
      [--extra-extensions .razor,.proto]

Requires no external dependencies beyond the standard library.
"""

import argparse
import json
import os
import sys

from schema import ImportDb


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# Directories to skip entirely (case-insensitive match on any path segment)
SKIP_DIRS: set[str] = {
    "bin", "obj", ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".vs", ".vscode", ".idea",
    "packages", "TestResults", ".nuget", "artifacts", ".terraform",
    "dist", "build", "out", "publish",
}

# File extensions to include (lowercase)
INCLUDE_EXTENSIONS: set[str] = {
    # .NET / C#
    ".cs", ".vb", ".fs", ".fsx", ".fsi",
    # Project / solution files
    ".csproj", ".vbproj", ".fsproj", ".shproj", ".sln", ".props", ".targets",
    # Web
    ".razor", ".cshtml", ".aspx", ".ascx", ".master", ".ashx",
    ".html", ".htm", ".css", ".scss", ".less",
    ".js", ".ts", ".jsx", ".tsx",
    # Data / config
    ".json", ".jsonc", ".xml", ".yml", ".yaml",
    ".config", ".appconfig", ".webconfig",
    ".env.example", ".editorconfig", ".gitignore", ".gitattributes",
    ".ini", ".toml",
    # Database
    ".sql", ".dacpac.sql",
    # Documentation
    ".md", ".markdown", ".txt", ".rst", ".adoc",
    # Resources
    ".resx", ".resw",
    # Other text artifacts
    ".proto", ".graphql", ".gql", ".tf", ".tfvars",
    ".bat", ".sh", ".ps1", ".psm1", ".psd1",
    ".dockerfile", ".dockerignore",
    ".editorconfig", ".ruleset",
    ".edmx",
}

# File names to always include regardless of extension
INCLUDE_FILENAMES: set[str] = {
    "dockerfile", ".dockerignore", ".gitignore", ".gitattributes",
    ".editorconfig", "makefile", "rakefile",
    "nuget.config", "global.json", "omnisharp.json",
}

# File extensions / names to always skip
SKIP_EXTENSIONS: set[str] = {
    ".user", ".suo", ".userprefs", ".cache",
    ".lock",  # but package-lock.json and yarn.lock are OK — checked by filename below
    ".pfx", ".p12", ".cer", ".crt", ".key",
    ".png", ".jpg", ".jpeg", ".gif", ".bmp", ".ico", ".svg", ".webp",
    ".pdf", ".docx", ".xlsx", ".pptx", ".doc", ".xls",
    ".zip", ".tar", ".gz", ".7z", ".rar",
    ".exe", ".dll", ".pdb", ".lib", ".so", ".dylib",
    ".nupkg", ".snupkg",
    ".min.js", ".min.css",
}

# Lock files (text, but large and rarely useful for LLM context)
SKIP_FILENAMES_EXACT: set[str] = {
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    "poetry.lock",
    "pipfile.lock",
    "composer.lock",
    "gemfile.lock",
}

DEFAULT_MAX_FILE_SIZE = 500 * 1024  # 500 KB
BINARY_CHECK_BYTES = 8 * 1024       # 8 KB


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def is_skip_dir(name: str) -> bool:
    return name.lower() in SKIP_DIRS


def is_binary(path: str) -> bool:
    """Heuristic: try decoding the first BINARY_CHECK_BYTES as UTF-8."""
    try:
        with open(path, "rb") as f:
            chunk = f.read(BINARY_CHECK_BYTES)
        chunk.decode("utf-8")
        return False
    except (UnicodeDecodeError, OSError):
        return True


def should_include(path: str, max_size: int) -> tuple[bool, str]:
    """Returns (include, reason_for_skip)."""
    name = os.path.basename(path)
    name_lower = name.lower()
    ext = os.path.splitext(name_lower)[1]

    # Double-extension check: e.g. ".min.js"
    for skip_ext in SKIP_EXTENSIONS:
        if name_lower.endswith(skip_ext):
            return False, f"skipped extension ({skip_ext})"

    if name_lower in SKIP_FILENAMES_EXACT:
        return False, "skipped lock file"

    if name_lower not in INCLUDE_FILENAMES and ext not in INCLUDE_EXTENSIONS:
        return False, f"extension not in include list ({ext or 'no ext'})"

    try:
        size = os.path.getsize(path)
    except OSError:
        return False, "cannot stat"

    if size > max_size:
        return False, f"too large ({size // 1024} KB > {max_size // 1024} KB)"

    if is_binary(path):
        return False, "binary file"

    return True, ""


def read_text(path: str) -> str:
    for enc in ("utf-8-sig", "utf-8", "cp1250", "latin-1"):
        try:
            with open(path, "r", encoding=enc) as f:
                return f.read()
        except (UnicodeDecodeError, OSError):
            continue
    return ""


# ---------------------------------------------------------------------------
# Main import logic
# ---------------------------------------------------------------------------

def import_repo(
    repo_path: str,
    output_path: str,
    prefix: str,
    max_file_size: int,
    extra_extensions: list[str],
):
    if not os.path.isdir(repo_path):
        print(f"ERROR: '{repo_path}' is not a directory.", file=sys.stderr)
        sys.exit(1)

    effective_extensions = INCLUDE_EXTENSIONS | {e.lower() for e in extra_extensions}

    repo_path = os.path.abspath(repo_path)
    print(f"Importing repository: {repo_path}")
    print(f"RAG prefix:           {prefix}")
    print(f"Output:               {output_path}")

    included = 0
    skipped = 0
    skip_reasons: dict[str, int] = {}

    with ImportDb(output_path) as db:
        session_id = db.create_session(
            source_type="git",
            source_name=repo_path,
        )

        for dirpath, dirnames, filenames in os.walk(repo_path, topdown=True):
            # Prune skipped directories in-place (modifies os.walk traversal)
            dirnames[:] = [d for d in dirnames if not is_skip_dir(d)]

            for filename in sorted(filenames):
                full_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(full_path, repo_path).replace("\\", "/")

                # Re-check extension (extra_extensions added at runtime)
                name_lower = filename.lower()
                ext = os.path.splitext(name_lower)[1]
                if ext in effective_extensions - INCLUDE_EXTENSIONS:
                    # Temporarily add to include set check via should_include override
                    pass

                ok, reason = should_include(full_path, max_file_size)
                # Override for extra extensions
                if not ok and ext in {e.lower() for e in extra_extensions}:
                    ok = True
                    reason = ""

                if not ok:
                    skipped += 1
                    skip_reasons[reason] = skip_reasons.get(reason, 0) + 1
                    continue

                content = read_text(full_path)
                if not content.strip():
                    skipped += 1
                    skip_reasons["empty file"] = skip_reasons.get("empty file", 0) + 1
                    continue

                rag_path = f"{prefix}/{rel_path}" if prefix else rel_path

                db.upsert_node(
                    session_id=session_id,
                    relative_path=rag_path,
                    content=content,
                    node_type="document",
                    source_type="git",
                    source_path=full_path,
                    meta_json=json.dumps({
                        "type": "code",
                        "extension": ext.lstrip(".") if ext else "",
                        "source": "git",
                        "repo": os.path.basename(repo_path),
                    }),
                )
                included += 1

                if included % 100 == 0:
                    db.flush()
                    print(f"  {included} files imported...")

        db.flush()

    print(f"\nDone.")
    print(f"  Imported: {included} files")
    print(f"  Skipped:  {skipped} files")
    if skip_reasons:
        print("  Skip reasons:")
        for reason, count in sorted(skip_reasons.items(), key=lambda x: -x[1]):
            print(f"    {count:4d}x  {reason}")
    print(f"\nOutput: {output_path}  (session: {session_id})")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Import a code repository into a Struktoria RAG SQLite file.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--path", "-p",
        required=True,
        help="Path to the repository root directory",
    )
    parser.add_argument(
        "--output", "-o",
        default="struktoria-repo.sqlite",
        help="Output SQLite file path (default: struktoria-repo.sqlite)",
    )
    parser.add_argument(
        "--prefix",
        default=None,
        help="Path prefix inside RAG hierarchy (default: repository folder name)",
    )
    parser.add_argument(
        "--max-file-size",
        type=int,
        default=DEFAULT_MAX_FILE_SIZE,
        help=f"Maximum file size in bytes to include (default: {DEFAULT_MAX_FILE_SIZE})",
    )
    parser.add_argument(
        "--extra-extensions",
        default="",
        help="Comma-separated extra file extensions to include (e.g. .razor,.proto)",
    )

    args = parser.parse_args()

    repo_path = os.path.abspath(args.path)
    prefix = args.prefix or os.path.basename(repo_path)
    extra_exts = [e.strip() for e in args.extra_extensions.split(",") if e.strip()]

    import_repo(
        repo_path=repo_path,
        output_path=args.output,
        prefix=prefix,
        max_file_size=args.max_file_size,
        extra_extensions=extra_exts,
    )


if __name__ == "__main__":
    main()

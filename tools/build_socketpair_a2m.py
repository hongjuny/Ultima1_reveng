#!/usr/bin/env python3
"""Build an isolated a2m variant with an inherited socketpair control channel."""

from pathlib import Path
import shutil
import subprocess
import sys

from disassemble import ROOT


PINNED = "d863ad98487639445db16134d260221839cb72e9"
SOURCE = ROOT / "build" / "emulator" / "a2m"
PATCHED = ROOT / "build" / "emulator" / "a2m-socketpair-src"
BUILD = ROOT / "build" / "emulator" / "a2m-socketpair-build"
TARGET = PATCHED / "src" / "platform" / "platform_socket.c"
MARKER = "A2M_CONTROL_FD"


def replace_once(source: str, old: str, new: str) -> str:
    if source.count(old) != 1:
        raise ValueError(f"pinned a2m source no longer matches patch anchor: {old[:55]!r}")
    return source.replace(old, new)


def patch_socket_source(source: str) -> str:
    source = replace_once(
        source,
        "struct platform_socket_listener {\n    a2m_socket_handle handle;\n};",
        "struct platform_socket_listener {\n"
        "    a2m_socket_handle handle;\n"
        "    bool inherited;\n"
        "    bool accepted;\n"
        "};",
    )
    source = replace_once(
        source,
        "    int one = 1;\n\n    handle = socket(AF_INET, SOCK_STREAM, 0);",
        "    int one = 1;\n\n"
        "#if !defined(_WIN32)\n"
        "    /* The caller passes one end of a socketpair through exec. This\n"
        "       avoids bind(), which some sandboxes disallow even on localhost. */\n"
        "    const char *fd_text = getenv(\"A2M_CONTROL_FD\");\n"
        "    if (fd_text != NULL && fd_text[0] != '\\0') {\n"
        "        char *end = NULL;\n"
        "        long fd = strtol(fd_text, &end, 10);\n"
        "        if (end == fd_text || *end != '\\0' || fd < 0 ||\n"
        "            fcntl((int)fd, F_GETFD) < 0) {\n"
        "            return NULL;\n"
        "        }\n"
        "        listener = (platform_socket_listener *)calloc(1, sizeof(*listener));\n"
        "        if (listener == NULL) {\n"
        "            return NULL;\n"
        "        }\n"
        "        listener->handle = (int)fd;\n"
        "        listener->inherited = true;\n"
        "        return listener;\n"
        "    }\n"
        "#endif\n\n"
        "    handle = socket(AF_INET, SOCK_STREAM, 0);",
    )
    source = replace_once(
        source,
        "    handle = accept(listener->handle, NULL, NULL);\n"
        "    if (handle == A2M_INVALID_SOCKET) {",
        "#if !defined(_WIN32)\n"
        "    if (listener->inherited) {\n"
        "        if (listener->accepted) {\n"
        "            return NULL;\n"
        "        }\n"
        "        listener->accepted = true;\n"
        "        handle = dup(listener->handle);\n"
        "    } else\n"
        "#endif\n"
        "    {\n"
        "        handle = accept(listener->handle, NULL, NULL);\n"
        "    }\n"
        "    if (handle == A2M_INVALID_SOCKET) {",
    )
    return source


def main() -> int:
    revision = subprocess.check_output(
        ["git", "-C", str(SOURCE), "rev-parse", "HEAD"], text=True).strip()
    if revision != PINNED:
        raise ValueError(f"expected pinned a2m {PINNED}, got {revision}")
    if not PATCHED.exists():
        shutil.copytree(SOURCE, PATCHED,
                        ignore=shutil.ignore_patterns(".git", "__pycache__"))
        original = TARGET.read_text()
        TARGET.write_text(patch_socket_source(original))
    elif MARKER not in TARGET.read_text():
        raise ValueError(f"existing {PATCHED} is not the socketpair variant")

    args = ["cmake", "-S", str(PATCHED), "-B", str(BUILD),
            "-DCMAKE_BUILD_TYPE=Release"]
    cache = ROOT / "build" / "emulator" / "a2m-build" / "CMakeCache.txt"
    if cache.is_file():
        for line in cache.read_text().splitlines():
            if line.startswith("SDL2_DIR:PATH="):
                args.append("-DSDL2_DIR=" + line.split("=", 1)[1])
                break
    subprocess.run(args, check=True)
    subprocess.run(["cmake", "--build", str(BUILD), "--target", "a2m", "-j", "6"],
                   check=True)
    emulator = BUILD / "a2m"
    if not emulator.is_file():
        raise RuntimeError("socketpair a2m binary was not produced")
    print(f"socketpair a2m: {emulator}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"socketpair build failed: {error}", file=sys.stderr)
        raise SystemExit(1)

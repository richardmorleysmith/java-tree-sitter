#!/usr/bin/env python
import platform
from argparse import ArgumentParser
from ctypes.util import find_library as find_cpp_library
from distutils.ccompiler import new_compiler as new_c_compiler
from distutils.log import set_verbosity as set_log_verbosity
from glob import glob as find
from os import environ
from os import system as cmd
from os.path import basename, dirname, exists, getmtime, realpath
from os.path import join as path
from os.path import split as split_path
from tempfile import TemporaryDirectory


# adapted from https://github.com/tree-sitter/py-tree-sitter
def build(repositories, output_dir=None, system=None, arch=None, verbose=False):
    here = dirname(realpath(__file__))

    if not repositories:
        repositories = sorted([basename(repository) for repository in find(path(here, "tree-sitter-*"))])

    if not repositories:
        raise ValueError("Library can not be compiled, no grammars were included!")

    system = system if system else platform.system()
    arch = arch if arch else platform.machine()

    # Normalize architecture
    arch = "arm64" if "aarch64" in arch.lower() or "arm64" in arch.lower() else "x86_64"

    # Determine output folder and extension
    output_extension = "dylib" if system == "Darwin" else "so"
    output_path = f"{output_dir + '/' if output_dir else ''}libjava-tree-sitter-{system.lower()}-{arch}.{output_extension}"
    env = ""
    command_flags = []
    if arch:
        if system == "Darwin":
            command_flags += ['-arch', arch]
            env += f"CFLAGS='-arch {arch} -mmacosx-version-min=11.0' LDFLAGS='-arch {arch}'"
        elif "x86" in arch:
            command_flags += ['-m64']
            env += "CFLAGS='-m64' LDFLAGS='-m64'"

    tree_sitter = path(here, "tree-sitter")
    redirect = "> /dev/null" if not verbose else ""
    cmd(f"make -C \"{tree_sitter}\" clean {redirect}")
    cmd(f"{env} make -C \"{tree_sitter}\" {redirect}")

    source_paths = find(path(here, "lib", "*.cc"))

    print(system)

    compiler = new_c_compiler()
    for repository in repositories:
        repository_name = split_path(repository.rstrip("/"))[1]
        repository_language = repository_name.split("tree-sitter-")[-1]
        repository_macro = f"TS_LANGUAGE_{repository_language.replace('-', '_').upper()}"
        compiler.define_macro(repository_macro, "1")
        match repository_name:
            case "tree-sitter-markdown":
                src_path = path(repository, repository_name, "src")
            case "tree-sitter-ocaml":
                src_path = path(repository, "grammars", repository_language, "src")
            case "tree-sitter-csv" | \
                 "tree-sitter-dtd" | \
                 "tree-sitter-ocaml" | \
                 "tree-sitter-php" | \
                 "tree-sitter-psv" | \
                 "tree-sitter-tsv" | \
                 "tree-sitter-tsx" | \
                 "tree-sitter-typescript" | \
                 "tree-sitter-xml":
                src_path = path(repository, repository_language, "src")
            case _:
                src_path = path(repository, "src")
        source_paths.append(path(src_path, "parser.c"))
        scanner_c = path(src_path, "scanner.c")
        scanner_cc = path(src_path, "scanner.cc")
        if exists(scanner_cc):
            source_paths.append(scanner_cc)
        elif exists(scanner_c):
            source_paths.append(scanner_c)

    source_mtimes = [getmtime(__file__)] + [getmtime(source_path) for source_path in source_paths]
    if find_cpp_library("stdc++"):
        compiler.add_library("stdc++")
    elif find_cpp_library("c++"):
        compiler.add_library("c++")

    output_mtime = getmtime(output_path) if exists(output_path) else 0
    if max(source_mtimes) <= output_mtime:
        return False

    with TemporaryDirectory(suffix="tree_sitter_language") as out_dir:
        object_paths = []
        for source_path in source_paths:
            flags = ["-O2", "-pipe"]  # Use -O2 instead of -O3 to reduce memory usage

            if system == "Linux":
                flags.append("-fPIC")

            if source_path.endswith(".c"):
                flags.append("-std=c11")

            if "arm" not in arch:
                flags += command_flags

            include_dirs = [
                dirname(source_path),
                path("include"),
                path(environ["JAVA_HOME"], "include"),
                path(here, "tree-sitter", "lib", "include"),
            ]

            try:
                object_path = compiler.compile(
                    [source_path],
                    output_dir=out_dir,
                    include_dirs=include_dirs,
                    extra_preargs=flags,
                )[0]
                object_paths.append(object_path)
            except Exception as e:
                print(f"Failed to compile {source_path}: {e}")
                # Try with reduced optimization
                reduced_flags = [flag for flag in flags if flag != "-O2"] + ["-O0"]
                object_path = compiler.compile(
                    [source_path],
                    output_dir=out_dir,
                    include_dirs=include_dirs,
                    extra_preargs=reduced_flags,
                )[0]
                object_paths.append(object_path)

        extra_preargs = []
        if system == "Darwin":
            extra_preargs.append("-dynamiclib")

        if "arm" not in arch:
            extra_preargs += command_flags

        compiler.link_shared_object(
            object_paths,
            output_path,
            extra_preargs=extra_preargs,
            extra_postargs=[path(here, "tree-sitter", "libtree-sitter.a")],
            library_dirs=[path(here, "tree-sitter")],
        )

    return True


if __name__ == "__main__":
    parser = ArgumentParser(description="Build a tree-sitter library.")
    parser.add_argument(
        "-s",
        "--system",
        help="Operating system to build for (Linux, Darwin)."
    )
    parser.add_argument(
        "-o",
        "--output_dir",
        help="Output directory."
    )
    parser.add_argument(
        "-a",
        "--arch",
        help="Architecture to build for (x86, x86_64, arm64, aarch64).",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Print verbose output.",
    )
    parser.add_argument(
        "repositories",
        nargs="*",
        help="""
        tree-sitter repositories to include in build.
        If none are specified, all directories that
        match ./tree-sitter-* will be included.
        """,
    )

    args = parser.parse_args()
    set_log_verbosity(int(args.verbose))
    build(args.repositories, args.output_dir, args.system, args.arch, args.verbose)

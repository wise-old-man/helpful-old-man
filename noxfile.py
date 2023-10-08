import functools
import os
import re
from typing import Callable
from typing import Dict

import nox

SessionT = Callable[[nox.Session], None]
InjectorT = Callable[[SessionT], SessionT]
VERSION_RGX = re.compile(r"^(?P<package>[\.\w-]+)\s?==\s?(?P<version>[^;\n]*).*$")


def parse_dependencies(*suffixes: str) -> Dict[str, str]:
    deps: Dict[str, str] = {}

    for suffix in suffixes:
        file = f"requirements{suffix}.txt"

        with open(file) as f:
            for line in f.readlines():
                if match := VERSION_RGX.match(line):
                    attrs = match.groupdict()
                    package, version = attrs["package"], attrs["version"]

                    if package == "uvloop" and os.name == "nt":
                        continue

                    if package in deps:
                        raise ValueError(f"Duplicate package {package!r} found in requirements.")

                    deps[package] = f"{package}=={version}"

    return deps


DEPS = parse_dependencies("", ".dev")


def install(*packages: str) -> InjectorT:
    def inner(func: SessionT) -> SessionT:
        @functools.wraps(func)
        def wrapper(session: nox.Session) -> None:
            try:
                session.install("-U", *(DEPS[p] for p in packages))
            except KeyError as e:
                session.error(f"Invalid package install - {e}")

            return func(session)
        return wrapper

    return inner


@nox.session(reuse_venv=True)
@install("pyright", "mypy", "discord.py", "python-dotenv", "uvloop")
def types(session: nox.Session) -> None:
    session.run("mypy")
    session.run("pyright")


@nox.session(reuse_venv=True)
@install("black")
def formatting(session: nox.Session) -> None:
    session.run("black", ".", "--check")


@nox.session(reuse_venv=True)
@install("flake8", "isort")
def imports(session: nox.Session) -> None:
    session.run("isort", "hom", "tests", "-cq", "-s", "__init__.py")
    session.run(
        "flake8",
        "hom",
        "tests",
        "--select",
        "F4",
        "--extend-ignore",
        "E,F",
        "--extend-exclude",
        "__init__.py",
    )

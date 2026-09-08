from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

import typer
from rich.console import Console
from rich.prompt import Prompt

# Sentinels
_QUIT_SENTINEL: Path = Path(".__ster_quit__")
_DEMO_SENTINEL: Path = Path(".__ster_demo__")
_ALL_FILES_SENTINEL: Path = Path(".__ster_all_files__")

# ANSI formatting constants
_ANSI_RESET = "\033[0m"
_ANSI_BOLD = "\033[1m"
_ANSI_DIM = "\033[2m"
_ANSI_INVERSE = "\033[7m"
_ANSI_RED = "\033[31m"
_ANSI_GREEN = "\033[32m"
_ANSI_CYAN = "\033[36m"
_ANSI_BRIGHT_CYAN = "\033[1;36m"
_CLEAR_LINE = "\r\033[2K"

console = Console()
err_console = Console(stderr=True)


def parse_numeric_picker_choice(
    idx: int,
    create_idx: int,
    quit_idx: int,
    files: list[Path],
    err: Console | None = None,
    quit_sentinel: Any = _QUIT_SENTINEL,
) -> tuple[bool, Path | None | object]:
    """Parse numeric choice for file picker. Returns (handled, result_value)."""
    error_console = err or err_console
    if idx == quit_idx:
        return True, quit_sentinel
    if idx == create_idx:
        return True, None
    if 1 <= idx <= len(files):
        return True, files[idx - 1]
    error_console.print(f"[red]Enter a number between 1 and {quit_idx}.[/red]")
    return False, None


def parse_comma_selection(
    raw: str,
    items: list[Path | None],
    is_toggleable_fn: Any | None = None,
) -> list[Path] | None:
    """Parse comma-separated item indices into list of Path objects."""
    selected_files: list[Path] = []
    for part in raw.split(","):
        try:
            idx = int(part.strip()) - 1
            if 0 <= idx < len(items):
                val = items[idx]
                if isinstance(val, Path):
                    if is_toggleable_fn is None or is_toggleable_fn(val):
                        selected_files.append(val)
        except ValueError:
            pass
    return selected_files if selected_files else None


def parse_file_picker_choice(
    choice: str,
    files: list[Path],
    create_idx: int,
    quit_idx: int,
    err: Console | None = None,
    quit_sentinel: Any = _QUIT_SENTINEL,
) -> tuple[bool, Path | None | object]:
    """Parse string input for pick_file_interactive. Returns (handled, value)."""
    error_console = err or err_console
    if choice.isdigit():
        return parse_numeric_picker_choice(
            int(choice), create_idx, quit_idx, files, err=error_console, quit_sentinel=quit_sentinel
        )

    matches = [f for f in files if f.name == choice or f.name.startswith(choice)]
    if len(matches) == 1:
        return True, matches[0]
    if len(matches) > 1:
        error_console.print(f"[yellow]Ambiguous — {[f.name for f in matches]}. Be more specific.[/yellow]")
    else:
        error_console.print(f"[red]{choice!r} not found.[/red]")
    return False, None


def print_fallback_options(
    files: list[Path],
    preselect: Path | None,
    create_idx: int,
    quit_idx: int,
    out_console: Console | None = None,
) -> None:
    c = out_console or console
    for i, f in enumerate(files, 1):
        marker = (
            " [bold green]←[/bold green] [dim](last session)[/dim]"
            if preselect and f == preselect
            else ""
        )
        c.print(f"  [cyan]{i:>2}[/cyan]  {f.name}{marker}")
    c.print(f"  [cyan]{create_idx:>2}[/cyan]  [bold green]+ Create new taxonomy[/bold green]")
    c.print(f"  [cyan]{quit_idx:>2}[/cyan]  [bold red]✕  Quit[/bold red]\n")


def fallback_file_picker(
    files: list[Path],
    preselect: Path | None,
    initial_sel: int,
    out_console: Console | None = None,
    err: Console | None = None,
    quit_sentinel: Any = _QUIT_SENTINEL,
) -> Path | list[Path] | None:
    create_idx, quit_idx = len(files) + 1, len(files) + 2
    print_fallback_options(files, preselect, create_idx, quit_idx, out_console=out_console)

    default_num = str(initial_sel + 1) if (preselect and preselect in files) else ""
    prompt_text = (
        f"Select [bold](number or filename)[/bold] [dim](Enter → {files[initial_sel].name})[/dim]"
        if default_num
        else f"Select [bold](1–{quit_idx})[/bold]"
    )
    while True:
        try:
            choice = Prompt.ask(prompt_text, default=default_num)
        except (KeyboardInterrupt, EOFError):
            raise typer.Exit(0)
        if not choice and default_num:
            return files[initial_sel]
        handled, val = parse_file_picker_choice(
            choice, files, create_idx, quit_idx, err=err, quit_sentinel=quit_sentinel
        )
        if handled:
            return val  # type: ignore[return-value]


def is_toggleable_file(val: Path | None) -> bool:
    return isinstance(val, Path) and val not in (
        _ALL_FILES_SENTINEL,
        _DEMO_SENTINEL,
        _QUIT_SENTINEL,
    )


def collect_checked_paths(item_values: list[Path | None], checked: set[int]) -> list[Path]:
    res: list[Path] = []
    for i in sorted(checked):
        val = item_values[i]
        if is_toggleable_file(val) and isinstance(val, Path):
            res.append(val)
    return res


def format_picker_item_label(
    idx: int,
    val: Path | None,
    selected: bool,
    is_checked: bool,
    num_files: int,
    preselect: Path | None,
) -> str:
    R, B, D, CY, BCY, GR, INV = (
        _ANSI_RESET,
        _ANSI_BOLD,
        _ANSI_DIM,
        _ANSI_CYAN,
        _ANSI_BRIGHT_CYAN,
        _ANSI_GREEN,
        _ANSI_INVERSE,
    )
    num_s = f"{idx + 1:>2}"
    chk_mark = f"{GR}[✓]{R} " if is_checked else "[ ] "

    if val == _QUIT_SENTINEL:
        plain = "✕  Quit"
        coloured = f"{_ANSI_RED}{plain}{R}"
    elif val == _ALL_FILES_SENTINEL:
        plain = f"📁 Open all project files ({num_files} files)"
        coloured = f"{GR}{plain}{R}"
    elif val == _DEMO_SENTINEL:
        plain = "🎒 Load demo ontology / taxonomy"
        coloured = f"{GR}{plain}{R}"
    elif val is None:
        plain = "+ Create new taxonomy"
        coloured = f"{GR}{plain}{R}"
    else:
        last = "  ← last session" if preselect and val == preselect else ""
        plain = f"{chk_mark}{val.name}{last}"
        coloured = f"{chk_mark}{val.name}{f'  {D}← last session{R}' if last else ''}"

    if selected:
        return f"  {BCY}{INV} {num_s} {R}  {B}{plain}{R}"
    return f"    {CY}{num_s}{R}  {coloured}"


def handle_esc_seq(sel: int, n: int) -> tuple[int, str, bool]:
    nxt = sys.stdin.buffer.read(1)
    if nxt == b"[":
        code = sys.stdin.buffer.read(1)
        if code == b"A":
            return (sel - 1) % n, "", False
        if code == b"B":
            return (sel + 1) % n, "", False
    return (sel, "", nxt in (b"\r", b"\n"))


def handle_digit_key(ch: bytes, sel: int, n: int, typed: str) -> tuple[int, str]:
    typed += ch.decode()
    new_sel = int(typed) - 1 if (typed.isdigit() and 1 <= int(typed) <= n) else sel
    return new_sel, typed


def process_picker_key(
    ch: bytes,
    sel: int,
    n: int,
    typed: str,
    checked: set[int],
    item_values: list[Path | None],
) -> tuple[int, str, bool]:
    """Process a single keypress in the file picker. Returns (new_sel, new_typed, is_done)."""
    if ch in (b"\r", b"\n"):
        return (int(typed) - 1 if (typed.isdigit() and 1 <= int(typed) <= n) else sel), typed, True

    if ch == b" " and is_toggleable_file(item_values[sel]):
        checked.symmetric_difference_update({sel})
        return sel, typed, False

    if ch == b"\x1b":
        return handle_esc_seq(sel, n)

    if ch in (b"\x7f", b"\x08"):
        return sel, typed[:-1], False

    if ch.isdigit():
        new_sel, new_typed = handle_digit_key(ch, sel, n, typed)
        return new_sel, new_typed, False

    return sel, typed, False


def arrow_file_picker(
    files: list[Path],
    item_values: list[Path | None],
    initial_sel: int,
    preselect: Path | None,
) -> Path | list[Path] | None:
    """Arrow-key file picker using raw terminal I/O + ANSI codes."""
    import termios
    import tty

    R, B, D = _ANSI_RESET, _ANSI_BOLD, _ANSI_DIM
    CLEAR, NL = _CLEAR_LINE, "\r\n"
    n = len(item_values)
    sel = initial_sel
    checked: set[int] = set()

    def render(typed: str, first: bool = False) -> None:
        if not first:
            sys.stdout.write(f"\033[{n + 1}A")
        for i in range(n):
            lbl = format_picker_item_label(
                i, item_values[i], i == sel, i in checked, len(files), preselect
            )
            sys.stdout.write(f"{CLEAR}{lbl}{NL}")
        if typed:
            sys.stdout.write(
                f"{CLEAR}  {D}type:{R} {B}{typed}▌{R}  {D}Enter: confirm  Esc: clear{R}"
            )
        elif checked:
            sys.stdout.write(
                f"{CLEAR}  {D}↑↓ nav  Space toggle  Enter open ({len(checked)} selected){R}"
            )
        else:
            sys.stdout.write(
                f"{CLEAR}  {D}↑↓ nav  Space multi-select  Enter open  or type number{R}"
            )
        sys.stdout.write(NL)
        sys.stdout.flush()

    render(typed="", first=True)
    typed = ""
    fd = sys.stdin.fileno()
    old_cfg = termios.tcgetattr(fd)
    try:
        tty.setraw(fd)
        while True:
            ch = sys.stdin.buffer.read(1)
            if ch == b"\x03":
                termios.tcsetattr(fd, termios.TCSADRAIN, old_cfg)
                raise KeyboardInterrupt

            sel, typed, done = process_picker_key(ch, sel, n, typed, checked, item_values)
            if done:
                break
            render(typed)
    finally:
        termios.tcsetattr(fd, termios.TCSADRAIN, old_cfg)
        sys.stdout.write(NL)
        sys.stdout.flush()

    checked_paths = collect_checked_paths(item_values, checked)
    if checked_paths:
        return checked_paths
    return item_values[sel]


def pick_file_interactive(
    files: list[Path],
    preselect: Path | None = None,
    quit_sentinel: Any = _QUIT_SENTINEL,
    arrow_picker_fn: Any | None = None,
) -> Path | list[Path] | None:
    """Display numbered file list; return chosen Path or None for 'create new'."""
    item_values: list[Path | None] = [*files, None, quit_sentinel]
    initial_sel = files.index(preselect) if (preselect and preselect in files) else 0

    if sys.stdin.isatty() and sys.stdout.isatty():
        try:
            import termios as _termios  # noqa: F401
            import tty as _tty  # noqa: F401

            picker = arrow_picker_fn or arrow_file_picker
            return picker(files, item_values, initial_sel, preselect)
        except ImportError:
            pass

    return fallback_file_picker(files, preselect, initial_sel, quit_sentinel=quit_sentinel)

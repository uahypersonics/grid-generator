"""Shared help text for the CLI: example command lists shown under a command group's help."""

# --------------------------------------------------
# load necessary modules
# --------------------------------------------------
from __future__ import annotations


# --------------------------------------------------
# public API
# --------------------------------------------------
def format_examples(examples: list[tuple[str, str]]) -> str:
    """Format (command, note) pairs as an aligned example list for a help epilog.

    Each pair becomes one line, the note dimmed after a '#'. The lines are kept apart
    by blank lines in the source, which the help formatter shows as line breaks.

    Args:
        examples: Command lines and a short note for each.

    Returns:
        Epilog text (rich markup).
    """

    # align the notes after the longest command
    width = max(len(command) for command, _ in examples)

    # build one line per example
    lines = ["[bold]Examples[/bold]"]
    for command, note in examples:
        lines.append(f"{command.ljust(width)}  [dim]# {note}[/dim]")
    epilog = "\n\n".join(lines)

    return epilog

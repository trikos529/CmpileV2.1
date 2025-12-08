import argparse
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

console = Console()

def parse_arguments():
    parser = argparse.ArgumentParser(description="Cmpile V2 - Compile and Run C/C++ code with ease.")
    parser.add_argument("files", nargs='+', help="The C or C++ files or folders to compile and run.")
    parser.add_argument("--compiler-flags", help="Additional compiler flags (quoted string).", default="")
    parser.add_argument("--clean", action="store_true", help="Force clean build (re-download/re-install if needed).")
    return parser.parse_args()

def display_header():
    console.print(Panel.fit("[bold cyan]Cmpile V2[/bold cyan]", border_style="cyan"))

def display_status(message, style="bold blue"):
    console.print(f"[{style}]{message}[/{style}]")

def display_error(message):
    console.print(f"[bold red]Error: {message}[/bold red]")

def display_success(message):
    console.print(f"[bold green]{message}[/bold green]")

def get_user_confirmation(prompt_message):
    return Confirm.ask(f"[yellow]{prompt_message}[/yellow]")

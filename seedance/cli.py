"""
Command Line Interface for NormaHub SeeDance & Grok Video Generator.
Supports rich terminal UI (spinners, color badges, panels) with graceful ANSI fallback.
"""

import argparse
from pathlib import Path
import sys
import time
from typing import List, Optional, Union

from .client import NormaVideoClient
from .exceptions import NormaVideoError
from .types import TaskStatus, VideoModel, VideoTask

try:
    from rich import box
    from rich.console import Console
    from rich.panel import Panel
    from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
    from rich.table import Table

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


def _print_ansi_banner(
    prompt: str,
    model: str,
    output: str,
    duration: int,
    aspect_ratio: str,
    image: Optional[str] = None,
) -> None:
    print("=" * 60)
    print("SeeDance & Grok Video CLI (NormaHub API)")
    print("=" * 60)
    print(f"Model:  {model}")
    print(f'Prompt: "{prompt}"')
    if image:
        print(f"Image:  {image}")
    print(f"Format: {duration}s, {aspect_ratio}")
    print(f"Output: {output}")
    print("=" * 60 + "\n")


def _cli_progress_fallback(task: VideoTask) -> None:
    timestamp = time.strftime("%H:%M:%S")
    st = task.status.value.upper()
    if task.status == TaskStatus.PENDING:
        color = "\033[33m"  # yellow
    elif task.status == TaskStatus.PROCESSING:
        color = "\033[36m"  # cyan
    elif task.status == TaskStatus.COMPLETED:
        color = "\033[32m"  # green
    else:
        color = "\033[31m"  # red
    print(f"[{timestamp}] ⠋ Задача {task.id} -> Статус: {color}{st}\033[0m...")


def handle_generate(args: argparse.Namespace) -> int:
    """Execute video generation and download workflow."""
    image_path: Optional[Union[str, Path]] = None
    image_url: Optional[str] = None
    if args.image:
        if args.image.startswith(("http://", "https://", "data:")):
            image_url = args.image
        else:
            p = Path(args.image)
            if not p.is_file():
                err_msg = f"Image file not found: {args.image}"
                if RICH_AVAILABLE:
                    Console(stderr=True).print(f"[bold red][!] Ошибка:[/] {err_msg}")
                else:
                    print(f"\033[1;31m[!] Ошибка: {err_msg}\033[0m", file=sys.stderr)
                return 1
            image_path = p

    try:
        client = NormaVideoClient(api_key=args.api_key)

        if RICH_AVAILABLE:
            console = Console()
            table = Table(show_header=False, box=box.ROUNDED, border_style="bright_blue", expand=False)
            table.add_column("Параметр", style="bold cyan", width=16)
            table.add_column("Значение", style="white")

            table.add_row("Провайдер", "NormaHub API")
            table.add_row("Модель", str(args.model))
            table.add_row("Промпт", f'"{args.prompt}"')
            if args.image:
                table.add_row("Изображение", f"{args.image} (Image-to-Video)")
            table.add_row("Формат", f"{args.duration}s, {args.aspect_ratio}")
            table.add_row("Файл", str(args.output))

            console.print(
                Panel(
                    table,
                    title="SeeDance & Grok Video CLI",
                    border_style="blue",
                )
            )
            console.print("[dim]Отправка задачи в очередь...[/dim]")

            task = client.create_task(
                prompt=args.prompt,
                model=args.model,
                duration=args.duration,
                aspect_ratio=args.aspect_ratio,
                image_path=image_path,
                image_url=image_url,
            )

            with Progress(
                SpinnerColumn(spinner_name="dots"),
                TextColumn("[bold cyan]{task.description}"),
                TextColumn("[dim]•[/dim]"),
                TextColumn("{task.fields[status_badge]}"),
                TextColumn("[dim]•[/dim]"),
                TimeElapsedColumn(),
                console=console,
                transient=False,
            ) as progress:
                p_id = progress.add_task(
                    f"Задача {task.id}",
                    status_badge="[yellow]PENDING[/yellow]",
                )

                def rich_callback(curr: VideoTask) -> None:
                    if curr.status == TaskStatus.PENDING:
                        badge = "[yellow]PENDING[/yellow]"
                    elif curr.status == TaskStatus.PROCESSING:
                        badge = "[cyan]PROCESSING[/cyan]"
                    elif curr.status == TaskStatus.COMPLETED:
                        badge = "[green]COMPLETED[/green]"
                    else:
                        badge = f"[red]{curr.status.value.upper()}[/red]"
                    progress.update(p_id, status_badge=badge)

                finished_task = client.wait_for_completion(
                    task.id,
                    timeout=args.timeout,
                    progress_callback=rich_callback,
                )

            if not finished_task.video_url:
                raise NormaVideoError("Задача завершена, но URL видео не получен")

            console.print(f"[dim]Загрузка файла в {args.output}...[/dim]")
            output_file = client.download_video(finished_task.video_url, args.output)
            file_size_mb = output_file.stat().st_size / (1024 * 1024)

            console.print(
                Panel(
                    f"Файл:    [cyan]{output_file.resolve()}[/]\n"
                    f"Размер:  [yellow]{file_size_mb:.2f} MB[/]\n"
                    f"Task ID: [dim]{finished_task.id}[/]",
                    title="Готово",
                    border_style="green",
                )
            )

        else:
            # Fallback for systems without rich
            _print_ansi_banner(
                prompt=args.prompt,
                model=args.model,
                output=args.output,
                duration=args.duration,
                aspect_ratio=args.aspect_ratio,
                image=str(args.image) if args.image else None,
            )
            print("[*] Отправка задачи в очередь NormaHub...")
            task = client.create_task(
                prompt=args.prompt,
                model=args.model,
                duration=args.duration,
                aspect_ratio=args.aspect_ratio,
                image_path=image_path,
                image_url=image_url,
            )
            print(f"[*] Задача создана. ID: {task.id}. Ожидание рендера...")

            finished_task = client.wait_for_completion(
                task.id,
                timeout=args.timeout,
                progress_callback=_cli_progress_fallback,
            )

            if not finished_task.video_url:
                raise NormaVideoError("Задача завершена, но URL видео не получен")

            print(f"[*] Скачивание готового файла в {args.output}...")
            output_file = client.download_video(finished_task.video_url, args.output)
            file_size_mb = output_file.stat().st_size / (1024 * 1024)
            print(f"\n\033[1;32m[+] Успех! Видео сохранено в: {output_file.resolve()} ({file_size_mb:.2f} MB)\033[0m")

        return 0

    except KeyboardInterrupt:
        if RICH_AVAILABLE:
            Console().print("\n[yellow][-] Прервано пользователем.[/yellow]")
        else:
            print("\n\033[33m[-] Прервано пользователем.\033[0m")
        return 130
    except NormaVideoError as e:
        if RICH_AVAILABLE:
            Console(stderr=True).print(f"\n[bold red][!] Ошибка NormaHub:[/] {e}")
        else:
            print(f"\n\033[1;31m[!] Ошибка NormaHub: {e}\033[0m", file=sys.stderr)
        return 1


def handle_status(args: argparse.Namespace) -> int:
    """Check task status by ID."""
    try:
        client = NormaVideoClient(api_key=args.api_key)
        task = client.get_status(args.task_id)

        if RICH_AVAILABLE:
            console = Console()
            table = Table(show_header=False, box=box.ROUNDED, border_style="cyan")
            table.add_column("Параметр", style="bold cyan", width=16)
            table.add_column("Значение", style="white")

            status_style = "green" if task.is_successful else ("cyan" if not task.is_finished else "red")
            table.add_row("Task ID", task.id)
            table.add_row("Статус", f"[{status_style}]{task.status.value.upper()}[/{status_style}]")
            progress_val = getattr(task, "progress", None)
            if progress_val is not None:
                table.add_row("Прогресс", f"{progress_val}%")
            if task.model:
                table.add_row("Модель", str(task.model))
            if task.prompt:
                table.add_row("Промпт", f'"{task.prompt}"')
            if task.video_url:
                table.add_row("URL видео", f"[link={task.video_url}]{task.video_url}[/link]")
            if task.error:
                table.add_row("Ошибка", f"[red]{task.error}[/red]")

            console.print(Panel(table, title="Статус задачи видео", border_style="blue"))
        else:
            print(f"Task ID: {task.id}")
            print(f"Status:  {task.status.value.upper()}")
            progress_val = getattr(task, "progress", None)
            if progress_val is not None:
                print(f"Progress: {progress_val}%")
            if task.video_url:
                print(f"URL:     {task.video_url}")
            if task.error:
                print(f"Error:   {task.error}")

        return 0
    except NormaVideoError as e:
        if RICH_AVAILABLE:
            Console(stderr=True).print(f"[bold red][!] Ошибка:[/] {e}")
        else:
            print(f"[!] Ошибка: {e}", file=sys.stderr)
        return 1


def handle_models(args: argparse.Namespace) -> int:
    """Display catalog of available video generation models."""
    models_data = [
        ("seedance-2.5", "ByteDance", "1080p FHD", "5s, 10s", "16:9, 9:16, 1:1", "Флагманская кинематография"),
        ("seedance-2.0", "ByteDance", "720p HD", "5s", "16:9, 9:16", "Высокая детализация"),
        ("seedance-2.0-fast", "ByteDance", "720p HD", "5s", "16:9, 9:16", "Сверхбыстрый драфт (~45с)"),
        ("grok-imagine-video-1.5", "xAI", "1080p FHD", "5s", "16:9, 9:16", "Стилизация и динамичный экшн"),
    ]

    if RICH_AVAILABLE:
        console = Console()
        table = Table(title="Каталог видеомоделей NormaHub", box=box.ROUNDED, border_style="bright_blue")
        table.add_column("Модель ID", style="bold cyan")
        table.add_column("Провайдер", style="magenta")
        table.add_column("Разрешение", style="green")
        table.add_column("Длина", style="yellow")
        table.add_column("Форматы", style="white")
        table.add_column("Особенности", style="dim white")

        for m_id, prov, res, dur, fmt, desc in models_data:
            table.add_row(m_id, prov, res, dur, fmt, desc)

        console.print(table)
    else:
        print("Каталог видеомоделей NormaHub:\n")
        for m_id, prov, res, dur, fmt, desc in models_data:
            print(f"• {m_id} ({prov}): {res}, {dur}, {fmt} - {desc}")

    return 0


def main(argv: Optional[List[str]] = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    # Backward compatibility: if first arg is not a known command or help flag, route to generate
    known_commands = {"generate", "status", "models", "-h", "--help", "-v", "--version"}
    if argv and argv[0] not in known_commands:
        argv = ["generate"] + list(argv)

    parser = argparse.ArgumentParser(
        prog="seedance",
        description="Генерация AI-видео через модели SeeDance и Grok по API NormaHub.",
    )
    subparsers = parser.add_subparsers(dest="subcommand", help="Доступные команды")

    # Command: generate
    p_gen = subparsers.add_parser("generate", help="Сгенерировать видео по тексту или изображению")
    p_gen.add_argument("prompt", help="Текстовое описание сцены (промпт)")
    p_gen.add_argument("-i", "--image", help="Путь к локальному изображению или URL для режима Image-to-Video")
    p_gen.add_argument(
        "-o", "--output", default="output.mp4", help="Путь к результирующему файлу MP4 (по умолчанию: output.mp4)"
    )
    p_gen.add_argument(
        "-m",
        "--model",
        default="seedance-2.5",
        choices=[m.value for m in VideoModel],
        help="Модель генерации видео (по умолчанию: seedance-2.5)",
    )
    p_gen.add_argument(
        "-d", "--duration", type=int, default=5, help="Длительность ролика в секундах (по умолчанию: 5)"
    )
    p_gen.add_argument(
        "--aspect-ratio", default="16:9", help="Соотношение сторон: 16:9, 9:16, 1:1 (по умолчанию: 16:9)"
    )
    p_gen.add_argument(
        "-t", "--timeout", type=int, default=300, help="Таймаут ожидания рендера в секундах (по умолчанию: 300)"
    )
    p_gen.add_argument(
        "--api-key", help="API-ключ NormaHub (по умолчанию берется из переменной NORMAHUB_API_KEY)"
    )

    # Command: status
    p_stat = subparsers.add_parser("status", help="Проверить статус задачи по ID")
    p_stat.add_argument("task_id", help="Идентификатор задачи генерации видео")
    p_stat.add_argument("--api-key", help="API-ключ NormaHub")

    # Command: models
    subparsers.add_parser("models", help="Показать каталог доступных моделей")

    args = parser.parse_args(argv)

    if args.subcommand == "generate":
        return handle_generate(args)
    elif args.subcommand == "status":
        return handle_status(args)
    elif args.subcommand == "models":
        return handle_models(args)
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())

"""
Command Line Interface for NormaHub SeeDance & Grok Video Generator.
Supports rich terminal UI (spinners, color badges, panels) with graceful ANSI fallback.
"""

import argparse
from pathlib import Path
import sys
import time
from typing import Optional, Union

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
    print("\033[1;35m" + "=" * 65 + "\033[0m")
    print("\033[1;37m 🎬 SeeDance & Grok Video Generator (NormaHub API)\033[0m")
    print("\033[1;35m" + "=" * 65 + "\033[0m")
    print(f" \033[1;36m• Модель:\033[0m        {model}")
    print(f" \033[1;36m• Промпт:\033[0m        \"{prompt}\"")
    if image:
        print(f" \033[1;36m• Изображение:\033[0m   {image} (Image-to-Video)")
    print(f" \033[1;36m• Формат:\033[0m        {duration} сек, {aspect_ratio}")
    print(f" \033[1;36m• Выходной файл:\033[0m {output}")
    print("\033[1;35m" + "=" * 65 + "\033[0m\n")


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


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate AI videos with SeeDance & Grok via NormaHub API (No VPN, RUB billing)."
    )
    parser.add_argument("prompt", help="Text prompt describing the scene")
    parser.add_argument(
        "-i", "--image",
        help="Path to local image or image URL for Image-to-Video generation"
    )
    parser.add_argument(
        "-o", "--output",
        default="output.mp4",
        help="Target local output file path (default: output.mp4)"
    )
    parser.add_argument(
        "-m", "--model",
        default="seedance-2.5",
        choices=[m.value for m in VideoModel],
        help="Video model to use (default: seedance-2.5)"
    )
    parser.add_argument(
        "-d", "--duration",
        type=int,
        default=5,
        help="Duration in seconds (default: 5)"
    )
    parser.add_argument(
        "--aspect-ratio",
        default="16:9",
        help="Aspect ratio (e.g. 16:9, 9:16, 1:1) (default: 16:9)"
    )
    parser.add_argument(
        "-t", "--timeout",
        type=int,
        default=300,
        help="Timeout in seconds to wait for generation (default: 300)"
    )
    parser.add_argument(
        "--api-key",
        help="NormaHub API key (defaults to NORMAHUB_API_KEY environment variable)"
    )

    args = parser.parse_args()

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

            table.add_row("🚀 Провайдер", "NormaHub Video Gateway (Без VPN, Карты РФ / СБП)")
            table.add_row("🤖 Модель", str(args.model))
            table.add_row("📝 Промпт", f"\"{args.prompt}\"")
            if args.image:
                table.add_row("🖼️ Изображение", f"{args.image} [dim](Image-to-Video)[/dim]")
            table.add_row("⏱️ Формат", f"{args.duration} сек, {args.aspect_ratio}")
            table.add_row("💾 Результат", str(args.output))

            console.print(
                Panel(
                    table,
                    title="[bold magenta]🎬 SeeDance & Grok Video Generator[/bold magenta]",
                    subtitle="[dim]https://normahub.cc[/dim]",
                    border_style="magenta",
                )
            )
            console.print("[dim]🚀 Отправка задачи генерации в очередь NormaHub...[/dim]")

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
                    status_badge="[yellow]⏳ PENDING (В очереди)[/yellow]",
                )

                def rich_callback(curr: VideoTask) -> None:
                    if curr.status == TaskStatus.PENDING:
                        badge = "[yellow]⏳ PENDING (В очереди)[/yellow]"
                    elif curr.status == TaskStatus.PROCESSING:
                        badge = "[cyan]⚡ PROCESSING (Нейросеть рендерит...)[/cyan]"
                    elif curr.status == TaskStatus.COMPLETED:
                        badge = "[green]✨ COMPLETED (Готово)[/green]"
                    else:
                        badge = f"[red]❌ {curr.status.value.upper()}[/red]"
                    progress.update(p_id, status_badge=badge)

                finished_task = client.wait_for_completion(
                    task.id,
                    timeout=args.timeout,
                    progress_callback=rich_callback,
                )

            if not finished_task.video_url:
                raise NormaVideoError("Задача завершена, но URL видео не получен")

            console.print(f"[dim]📥 Загрузка видеофайла в {args.output}...[/dim]")
            output_file = client.download_video(finished_task.video_url, args.output)
            file_size_mb = output_file.stat().st_size / (1024 * 1024)

            console.print(
                Panel(
                    f"[bold green]✨ Видео успешно сгенерировано и загружено![/bold green]\n\n"
                    f"📁 [bold white]Файл:[/] [cyan]{output_file.resolve()}[/]\n"
                    f"📦 [bold white]Размер:[/] [yellow]{file_size_mb:.2f} MB[/]\n"
                    f"🎯 [bold white]Task ID:[/] [dim]{finished_task.id}[/]",
                    title="[bold green]Успех[/bold green]",
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


if __name__ == "__main__":
    sys.exit(main())

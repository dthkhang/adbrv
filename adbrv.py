#!/usr/bin/env python3
__version__ = "2.4.4"
import sys
import unicodedata
import typer
from typing import Optional, List
from typing_extensions import Annotated
from rich.console import Console
from rich import print as rprint

from adbrv_module.proxy import set_proxy, unset_proxy_and_reverse, ProxyError
from adbrv_module.devices import get_connected_devices, check_devices_info, AdbError
from adbrv_module.fridaTools import frida_kill, start_frida_server
from adbrv_module.checkSymbols import check_symbols
from adbrv_module.resignAPK import resign_apk
from adbrv_module.findSOfile import find_so_files
from adbrv_module.libSecurity import check_lib_security
from adbrv_module.core import update_script, CoreError

from typer.rich_utils import _get_rich_console
from rich.panel import Panel
import typer.rich_utils

typer.rich_utils.STYLE_OPTIONS_TABLE_PAD_EDGE = True
typer.rich_utils.STYLE_COMMANDS_TABLE_PAD_EDGE = True
typer.rich_utils.STYLE_OPTIONS_TABLE_PADDING = (0, 3)
typer.rich_utils.STYLE_COMMANDS_TABLE_PADDING = (0, 3)

original_rich_format_help = typer.rich_utils.rich_format_help
def custom_rich_format_help(
    *,
    obj,
    ctx,
    markup_mode,
):
    epilog = obj.epilog
    obj.epilog = None
    original_rich_format_help(obj=obj, ctx=ctx, markup_mode=markup_mode)
    obj.epilog = epilog
    if epilog:
        console = _get_rich_console()
        from rich.table import Table
        from rich.text import Text
        
        example_table = Table(show_header=False, box=None, padding=(0, 3), pad_edge=True)
        example_table.add_column(style="cyan", no_wrap=True)
        example_table.add_column()

        
        # Parse the raw epilog string to build rows
        # Format expected: odd lines are commands, even lines are descriptions
        lines = [line.strip() for line in epilog.strip().split('\n') if line.strip()]
        for i in range(0, len(lines), 2):
            if i + 1 < len(lines):
                cmd = lines[i].replace('[cyan]', '').replace('[/cyan]', '')
                desc = lines[i+1]
                example_table.add_row(f"{cmd}", desc)
                
        console.print(
            Panel(
                example_table,
                border_style="dim",
                title="Examples",
                title_align="left",
            )
        )

typer.rich_utils.rich_format_help = custom_rich_format_help

app = typer.Typer(
    name="adbrv",
    help="ADB reverse port forwarding, HTTP proxy configuration, APK analysis tools, and security assessment for Android devices.",
    epilog="""
adbrv status
Show proxy, reverse port, and frida-server status.

adbrv status -d 1234
Show status for specific device.

adbrv set 8080 8080
Set up reverse proxy & HTTP proxy.

adbrv unset
Remove proxy and all reverse ports.

adbrv frida-start
Start frida-server (prompts auto-selection).

adbrv resign --apk target.apk
Resign APK file using integrated uber-apk-signer.

adbrv checksym base_dir
Check symbols in decompiled APK folder.

adbrv findso
Search for .so files across all APKs in current folder.

adbrv libsec
Run MASTG security checks on .so files.
""",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

def version_callback(value: bool):
    if value:
        console.print(f"[bold green]adbrv version[/bold green] [cyan]{__version__}[/cyan]")
        raise typer.Exit()

@app.callback(invoke_without_command=True)
def main_callback(
    ctx: typer.Context,
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-v",
            callback=version_callback,
            is_eager=True,
            help="Show the application's version and exit.",
        ),
    ] = None,
):
    if ctx.invoked_subcommand is None:
        import shlex
        import click
        from prompt_toolkit import PromptSession
        from prompt_toolkit.history import InMemoryHistory
        from prompt_toolkit.completion import Completer, Completion
        from prompt_toolkit.key_binding import KeyBindings
        
        allowed_commands_list = [
            "set", "unset", "status", "frida-start", "frida-kill", "pull",
            "help", "exit", "quit", "--help", "-h"
        ]

        import time
        import threading

        packages_cache = []

        class StatusCache:
            def __init__(self):
                self.devices = []
                self.devices_last = 0
                self.devices_fetching = False

                self.frida = True
                self.frida_last = 0
                self.frida_fetching = False

                self.unset = True
                self.unset_last = 0
                self.unset_fetching = False
                
                # Eagerly pre-fetch statuses in background
                threading.Thread(target=self._initial_fetch, daemon=True).start()

            def _initial_fetch(self):
                try:
                    from adbrv_module.devices import get_connected_devices, get_proxy_status, get_reverse_ports, adb_shell
                    
                    # 1. Fetch devices
                    self.devices = get_connected_devices()
                    self.devices_last = time.time()
                    
                    # 2. Fetch Unset (Proxy & Reverse Status)
                    if self.devices:
                        is_any = False
                        for d in self.devices:
                            p = get_proxy_status(d)
                            r = get_reverse_ports(d)
                            if (p and p not in [":0", "null", ""]) or (r and r != "(none)"):
                                is_any = True
                                break
                        self.unset = is_any
                    else:
                        self.unset = False
                    self.unset_last = time.time()
                    
                    # 3. Fetch Frida Status
                    if self.devices:
                        frida_ps = adb_shell(["ps", "|", "grep", "rida-server"])
                        self.frida = bool(frida_ps and "rida-server" in frida_ps)
                    else:
                        self.frida = False
                    self.frida_last = time.time()
                except Exception:
                    pass

            def trigger_completion(self):
                try:
                    from prompt_toolkit.application import get_app
                    app = get_app()
                    def _do():
                        if app.current_buffer.text:
                            app.current_buffer.start_completion(select_first=False)
                    app.loop.call_soon_threadsafe(_do)
                except Exception:
                    pass

            def check_devices(self):
                if time.time() - self.devices_last > 1.0:
                    if not self.devices_fetching:
                        self.devices_fetching = True
                        def bg():
                            try:
                                from adbrv_module.devices import get_connected_devices
                                self.devices = get_connected_devices()
                            except Exception:
                                self.devices = []
                            self.devices_last = time.time()
                            self.devices_fetching = False
                            self.trigger_completion()
                        threading.Thread(target=bg, daemon=True).start()
                if self.devices_last == 0:
                    return ["Optimistic"]
                return self.devices

            def check_frida(self):
                if time.time() - self.frida_last > 1.5:
                    if not self.frida_fetching:
                        self.frida_fetching = True
                        def bg():
                            try:
                                from adbrv_module.devices import adb_shell
                                frida_ps = adb_shell(["ps", "|", "grep", "rida-server"])
                                self.frida = bool(frida_ps and "rida-server" in frida_ps)
                            except Exception:
                                self.frida = False
                            self.frida_last = time.time()
                            self.frida_fetching = False
                            self.trigger_completion()
                        threading.Thread(target=bg, daemon=True).start()
                if self.frida_last == 0:
                    return True
                return self.frida

            def check_unset(self):
                if time.time() - self.unset_last > 2.0:
                    if not self.unset_fetching:
                        self.unset_fetching = True
                        def bg():
                            try:
                                from adbrv_module.devices import get_connected_devices, get_proxy_status, get_reverse_ports
                                devs = get_connected_devices()
                                self.devices = devs
                                self.devices_last = time.time()
                                is_any = False
                                if devs:
                                    for d in devs:
                                        p = get_proxy_status(d)
                                        r = get_reverse_ports(d)
                                        if (p and p not in [":0", "null", ""]) or (r and r != "(none)"):
                                            is_any = True
                                            break
                                self.unset = is_any
                            except Exception:
                                self.unset = False
                            self.unset_last = time.time()
                            self.unset_fetching = False
                            self.unset_fetching = False
                            self.trigger_completion()
                        threading.Thread(target=bg, daemon=True).start()
                if self.unset_last == 0:
                    return True
                return self.unset

            def flush(self):
                self.devices_last = 0
                self.unset_last = 0
                self.frida_last = 0
                packages_cache.clear()
                self.trigger_completion()
                
        status_cache = StatusCache()

        class RealtimeMonitor:
            def __init__(self, cache_instance):
                self.cache = cache_instance
                self.process = None
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()

            def _run(self):
                import subprocess
                try:
                    self.process = subprocess.Popen(["adb", "track-devices"], stdout=subprocess.PIPE, text=True)
                    while True:
                        line = self.process.stdout.readline()
                        if not line and self.process.poll() is not None:
                            break
                        # Track devices triggered: device joined/left
                        self.cache.flush()
                except Exception:
                    pass

            def stop(self):
                if self.process:
                    try:
                        self.process.kill()
                    except:
                        pass

        realtime_monitor = RealtimeMonitor(status_cache)

        def is_valid_sentence_prefix(text):
            text_lstrip = text.lstrip()
            if not text_lstrip:
                return True
                
            parts = text_lstrip.split()
            ends_with_space = text_lstrip.endswith(" ") or text_lstrip.endswith("\t")
            
            cmd = parts[0].lower()
            valid_cmds = ["set", "unset", "status", "frida-start", "frida-kill", "pull", "help", "exit", "quit", "--help", "-h"]
            matching_cmds = [c for c in valid_cmds if c.startswith(cmd)]
            
            if not matching_cmds:
                return False
                
            if cmd not in valid_cmds:
                if ends_with_space or len(parts) > 1:
                    return False
                return True

            if cmd in ["pull", "set", "unset", "status", "frida-start", "frida-kill"]:
                if len(text_lstrip) > len(cmd):
                    if not status_cache.check_devices():
                        return False

            if cmd == "frida-kill":
                if len(text_lstrip) > len(cmd):
                    if not status_cache.check_frida():
                        return False

            if cmd == "unset":
                if len(text_lstrip) > len(cmd):
                    if not status_cache.check_unset():
                        return False

            expected_pos = 2 if cmd in ["set", "pull"] else 0
            pos_count = 0
            has_flag = False
            flag_val_count = 0
            
            i = 1
            while i < len(parts):
                part = parts[i]
                is_last = (i == len(parts) - 1)
                
                
                if part.startswith("-"):
                    if part in ["-h", "--help"]:
                        return True
                        
                    if "--device".startswith(part) or "-d".startswith(part):
                        if has_flag:
                            return False
                        if part in ["-d", "--device"]:
                            has_flag = True
                        elif is_last and ends_with_space:
                            return False
                    else:
                        return False
                else:
                    if has_flag and flag_val_count == 0:
                        flag_val_count += 1
                    else:
                        if pos_count >= expected_pos:
                            return False
                        if cmd == "set" and not part.isdigit():
                            return False
                        
                        pos_count += 1
                        
                i += 1
                
            if ends_with_space:
                if pos_count == expected_pos and has_flag and flag_val_count == 1:
                    return False
                    
            if cmd in ["help", "exit", "quit", "--help", "-h"]:
                if ends_with_space or len(parts) > 1:
                    return False
                    
            return True

        import threading
        
        def fetch_packages_fn():
            try:
                from adbrv_module.pullAPK import get_installed_packages
                pkgs = get_installed_packages()
                if pkgs:
                    packages_cache.clear()
                    packages_cache.extend(pkgs)
            except Exception:
                pass
        
        threading.Thread(target=fetch_packages_fn, daemon=True).start()

        def remove_accents(input_str):
            s1 = unicodedata.normalize('NFKD', input_str).encode('ASCII', 'ignore').decode('utf-8')
            return s1.replace('đ', 'd').replace('Đ', 'D')

        class CommandCompleter(Completer):
            def get_completions(self, document, complete_event):
                completions = list(self._get_completions_inner(document, complete_event))
                warnings = [c for c in completions if c.text == " " and getattr(c, 'display', None) is not None and "[!]" in str(c.display)]
                
                if warnings:
                    for w in warnings:
                        yield w
                else:
                    for c in completions:
                        yield c

            def _get_completions_inner(self, document, complete_event):
                text = document.text_before_cursor
                parts = text.split()
                ends_with_space = text.endswith(" ") or text.endswith("\t")
                
                if not text.lstrip():
                    for cmd in allowed_commands_list:
                        yield Completion(cmd, start_position=0)
                    return
                
                word_before_cursor = document.get_word_before_cursor(WORD=True)

                if len(parts) == 1 and not ends_with_space:
                    word_lower = parts[0].lower()
                    exact_match_found = False
                    for cmd_item in allowed_commands_list:
                        if cmd_item.startswith(word_lower):
                            if cmd_item == word_lower:
                                exact_match_found = True
                            yield Completion(cmd_item, start_position=-len(word_before_cursor))
                    if not exact_match_found:
                        return

                cmd = parts[0].lower()
                
                if cmd in ["unset", "status", "frida-start", "frida-kill"]:
                    if len(parts) == 1:
                        # Only show warnings if the user has typed the full exact command
                        if cmd == parts[0].lower() and parts[0].lower() in ["unset", "status", "frida-start", "frida-kill"]:
                            devices = status_cache.check_devices()
                            from prompt_toolkit.formatted_text import HTML

                            if not devices:
                                yield Completion(
                                    text=" ",
                                    start_position=0,
                                    display=HTML('<ansired>[!] No devices connected</ansired>')
                                )
                                return
                                
                            if cmd == "unset" and devices:
                                is_any_set = status_cache.check_unset()
                                if not is_any_set:
                                    yield Completion(
                                        text=" ",
                                        start_position=0,
                                        display=HTML('<ansired>[!] Nothing to unset (Proxy and Reverse ports are already empty)</ansired>')
                                    )
                                    return

                            if cmd == "frida-kill":
                                frida_running = status_cache.check_frida()
                                if not frida_running:
                                    yield Completion(
                                        text=" ",
                                        start_position=0,
                                        display=HTML('<ansired>[!] Frida server is not running</ansired>')
                                    )
                                    return

                        if ends_with_space and "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                    elif len(parts) == 2 and not ends_with_space and parts[1].startswith("-"):
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                            
                elif cmd == "set":
                    if len(parts) == 1:
                        if cmd == parts[0].lower() and parts[0].lower() == "set":
                            devices = status_cache.check_devices()
                            from prompt_toolkit.formatted_text import HTML

                            if not devices:
                                yield Completion(
                                    text=" ",
                                    start_position=0,
                                    display=HTML('<ansired>[!] No devices connected</ansired>')
                                )
                                return
                                
                        if ends_with_space and "enter your port".startswith(word_before_cursor.lower()):
                            yield Completion("enter your port", start_position=-len(word_before_cursor))
                    elif len(parts) == 3 and ends_with_space:
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                    elif len(parts) == 4 and not ends_with_space and parts[3].startswith("-"):
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                            
                elif cmd == "pull":
                    search_word = remove_accents(word_before_cursor.lower())
                    if (len(parts) == 1) or (len(parts) == 2 and not ends_with_space):
                        if parts[0].lower() == "pull":
                            devices = status_cache.check_devices()
                            from prompt_toolkit.formatted_text import HTML
                            if not devices:
                                yield Completion(
                                    text=" ",
                                    start_position=0,
                                    display=HTML('<ansired>[!] No devices connected</ansired>')
                                )
                                return
                                
                            if ends_with_space or len(parts) == 2:
                                if not packages_cache:
                                    import threading
                                    threading.Thread(target=fetch_packages_fn, daemon=True).start()
                                    yield Completion(
                                        text=" ",
                                        start_position=0,
                                        display=HTML('<ansiyellow>[!] Loading packages. Please wait...</ansiyellow>')
                                    )
                                    return

                                has_names = any(isinstance(p, dict) and p.get("name") for p in packages_cache)
                                for pkg in packages_cache:
                                    if isinstance(pkg, dict):
                                        pkg_id = pkg.get("id", "").lower()
                                        pkg_name = remove_accents(pkg.get("name", "").lower())
                                        if search_word in pkg_id or search_word in pkg_name:
                                            if has_names:
                                                display_text = pkg.get("name") if pkg.get("name") else " "
                                                yield Completion(
                                                    text=pkg["id"], 
                                                    start_position=-len(word_before_cursor), 
                                                    display=display_text, 
                                                    display_meta=pkg["id"]
                                                )
                                            else:
                                                yield Completion(
                                                    text=pkg["id"], 
                                                    start_position=-len(word_before_cursor)
                                                )
                                    else:
                                        if pkg.lower().startswith(search_word):
                                            yield Completion(pkg, start_position=-len(word_before_cursor))
                    elif len(parts) == 2 and ends_with_space:
                        if "path".startswith(word_before_cursor.lower()):
                            yield Completion("path", start_position=-len(word_before_cursor))
                    elif len(parts) == 3 and not ends_with_space and parts[2].startswith("-"):
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                    elif len(parts) == 3 and ends_with_space:
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                    elif len(parts) == 4 and not ends_with_space and parts[3].startswith("-"):
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))

        command_completer = CommandCompleter()

        kb = KeyBindings()
        from prompt_toolkit.filters import has_completions

        def _is_warning_active(b):
            if b.complete_state and b.complete_state.completions:
                for c in b.complete_state.completions:
                    if getattr(c, 'display', None) is not None and "[!]" in str(c.display):
                        return True
            return False

        @kb.add('left')
        def _(event):
            buffer = event.app.current_buffer
            if _is_warning_active(buffer): return
            buffer.cursor_left()

        @kb.add('up', filter=~has_completions)
        def _(event):
            b = event.app.current_buffer
            b.auto_up(count=event.arg)
            if b.text.strip():
                def resume_completion():
                    b.start_completion(select_first=False)
                event.app.loop.call_soon_threadsafe(resume_completion)

        @kb.add('down', filter=~has_completions)
        def _(event):
            b = event.app.current_buffer
            b.auto_down(count=event.arg)
            if b.text.strip():
                def resume_completion():
                    b.start_completion(select_first=False)
                event.app.loop.call_soon_threadsafe(resume_completion)

        @kb.add('down', filter=has_completions)
        def _(event):
            b = event.app.current_buffer
            if _is_warning_active(b): return
            state = b.complete_state
            if state and state.completions:
                if state.complete_index is None:
                    state.complete_index = 0
                else:
                    state.complete_index = (state.complete_index + 1) % len(state.completions)

        @kb.add('up', filter=has_completions)
        def _(event):
            b = event.app.current_buffer
            if _is_warning_active(b): return
            state = b.complete_state
            if state and state.completions:
                if state.complete_index is None:
                    state.complete_index = len(state.completions) - 1
                else:
                    state.complete_index = (state.complete_index - 1) % len(state.completions)

        @kb.add('<any>')
        def _(event):
            buffer = event.app.current_buffer
            if _is_warning_active(buffer): return
            char = event.data
            new_text = buffer.text[:buffer.cursor_position] + char + buffer.text[buffer.cursor_position:]
            
            if is_valid_sentence_prefix(new_text):
                buffer.insert_text(char)
            # Luôn gọi start_completion để hiện warning ngay cả khi phím bị chặn không cho phép gõ tiếp
            if buffer.text:
                buffer.start_completion(select_first=False)

        @kb.add('escape', eager=True)
        def _(event):
            event.app.current_buffer.cancel_completion()

        @kb.add('backspace')
        def _(event):
            event.app.current_buffer.delete_before_cursor(count=1)
            if event.app.current_buffer.text:
                event.app.current_buffer.start_completion(select_first=False)

        @kb.add('enter')
        def _(event):
            buffer = event.app.current_buffer
            if _is_warning_active(buffer): return
            
            # Nếu người dùng đang chọn menu completion bằng mũi tên và bấm Enter -> chỉ hoàn thành lệnh + hiện cảnh báo nếu có
            if buffer.complete_state and buffer.complete_state.current_completion:
                buffer.apply_completion(buffer.complete_state.current_completion)
                def resume_completion():
                    buffer.start_completion(select_first=False)
                event.app.loop.call_soon_threadsafe(resume_completion)
                return
                
            text_lstrip = buffer.text.lstrip()
            parts = text_lstrip.split()
            
            if not parts:
                buffer.validate_and_handle()
                return

            cmd = parts[0].lower()
            ends_with_space = text_lstrip.endswith(" ") or text_lstrip.endswith("\t")
            
            # Prevent enter for commands requiring devices if none connected
            if cmd in ["pull", "set", "unset", "status", "frida-start", "frida-kill"]:
                if len(parts) > 1 or ends_with_space:
                    if not status_cache.check_devices():
                        return # Ignore Enter key

            # Prevent enter for frida-kill if frida server is not running
            if cmd == "frida-kill":
                if len(parts) > 1 or ends_with_space:
                    if not status_cache.check_frida():
                        return # Ignore Enter key
                        
            # Prevent enter for unset if no proxy or reverse set
            if cmd == "unset":
                if len(parts) > 1 or ends_with_space:
                    if not status_cache.check_unset():
                        return # Ignore Enter key
                    
            buffer.validate_and_handle()

        @kb.add('right')
        def _(event):
            buffer = event.app.current_buffer
            if _is_warning_active(buffer): return
            if buffer.complete_state and buffer.complete_state.current_completion:
                buffer.apply_completion(buffer.complete_state.current_completion)
                def resume_completion():
                    buffer.start_completion(select_first=False)
                event.app.loop.call_soon_threadsafe(resume_completion)
                return
            event.app.current_buffer.cursor_right()

        @kb.add('tab')
        def _(event):
            buffer = event.app.current_buffer
            if _is_warning_active(buffer): return
            if buffer.complete_state and buffer.complete_state.current_completion:
                buffer.apply_completion(buffer.complete_state.current_completion)
                def resume_completion():
                    buffer.start_completion(select_first=False)
                event.app.loop.call_soon_threadsafe(resume_completion)
                return
            # Nếu chưa có suggest menu, thì gọi
            buffer.start_completion(select_first=False)


        
        console.print("[bold cyan]Welcome to adbrv Workspace. Type 'help' for available commands, 'exit' to quit.[/bold cyan]")
        session = PromptSession(history=InMemoryHistory())
    
        try:
            while True:
                try:
                    # eager=True in the KeyBinding bypasses the delay
                    cmd = session.prompt("adbrv> ", completer=command_completer, complete_while_typing=True, key_bindings=kb)
                    if not cmd.strip():
                        continue
                    if cmd.strip().lower() in ["exit", "quit"]:
                        break
                    if cmd.strip().lower() in ["help", "-h", "--help"]:
                        from rich.table import Table
                        from rich.panel import Panel
                        from rich import box
                        help_tbl = Table(box=None, show_header=False, pad_edge=True, padding=(0, 3))
                        help_tbl.add_column("Command", style="cyan", no_wrap=True)
                        help_tbl.add_column("Description", style="default")
                        help_tbl.add_row("set", "Set up ADB reverse proxy and HTTP proxy.")
                        help_tbl.add_row("unset", "Remove proxy and all reverse ports on the selected (or all) devices.")
                        help_tbl.add_row("status", "Display proxy, reverse port, and frida-server status.")
                        help_tbl.add_row("frida-start", "Start frida/florida-server on the device with root privileges.")
                        help_tbl.add_row("frida-kill", "Kill all running frida/florida-server processes on the device.")
                        help_tbl.add_row("pull", "Pull an installed APK from the device by its package name.")
                        help_tbl.add_row("exit / quit", "Exit the interactive workspace.")
                        
                        panel = Panel(
                            help_tbl,
                            title="Commands",
                            title_align="left",
                            border_style="dim",
                            box=box.ROUNDED
                        )
                        console.print(panel)
                        
                        example_tbl = Table(box=None, show_header=False, pad_edge=True, padding=(0, 3))
                        example_tbl.add_column(style="cyan", no_wrap=True)
                        example_tbl.add_column()
                        example_tbl.add_row("set 8080 8080", "Set up reverse proxy & HTTP proxy.")
                        example_tbl.add_row("unset", "Remove proxy and all reverse ports.")
                        example_tbl.add_row("status", "Show proxy, reverse port, and server status.")
                        example_tbl.add_row("status -d 123", "Show status for specific device.")
                        example_tbl.add_row("frida-start", "Start server (prompts auto-selection).")
                        example_tbl.add_row("frida-kill", "Kill all running frida/florida-server processes on the device.")
                        example_tbl.add_row("pull com.example /Downloads", "Extract single/split APKs to the destination.")
                        example_tbl.add_row("frida-kill -d 123", "Kill all running frida/florida-server processes on the specific device.")
                        example_panel = Panel(
                            example_tbl,
                            title="Examples",
                            title_align="left",
                            border_style="dim"
                        )
                        console.print(example_panel)
                        
                        continue
                    args = shlex.split(cmd)
                    if not args:
                        continue
                        
                    allowed_commands = {"set", "unset", "status", "frida-start", "frida-kill", "pull", "--help", "-h"}
                    if args[0] not in allowed_commands:
                        console.print(f"[bold red][!] Command '{args[0]}' is not supported inside Workspace.[/bold red]")
                        console.print("[yellow]Please type 'exit' to leave the workspace and run it normally, or type 'help' for allowing commands in Workspace.[/yellow]")
                        continue
                        
                    try:
                        ctx.command(args=args, standalone_mode=False)
                    except click.exceptions.Exit:
                        pass
                    except SystemExit:
                        pass
                    except Exception as e:
                        console.print(f"[bold red]Command Error: {e}[/bold red]")
                    finally:
                        # Flush caches sau khi chạy lệnh để refresh RealTime
                        status_cache.flush()
                        
                except KeyboardInterrupt:
                    continue
                except EOFError:
                    break
        finally:
            realtime_monitor.stop()
            packages_cache.clear()
            status_cache.devices.clear()
            status_cache.frida = False
            status_cache.unset = False

@app.command(name="set")
def cmd_set(
    local_port: Annotated[int, typer.Argument(help="Local port to route traffic to (integer)")],
    device_port: Annotated[int, typer.Argument(help="Device port to map (integer)")],
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Set up ADB reverse proxy and HTTP proxy."""
    try:
        if not (1 <= local_port <= 65535) or not (1 <= device_port <= 65535):
            console.print("[bold red][!] Invalid port. Port must be an integer between 1 and 65535.[/bold red]")
            raise typer.Exit(1)
            
        from adbrv_module.devices import select_device, check_devices_info
        target_device = select_device(device)
        set_proxy(local_port, device_port, target_device)
        check_devices_info(target_device, show_title=False)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="unset")
def cmd_unset(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Remove proxy and all reverse ports on the selected (or all) devices."""
    try:
        devices = get_connected_devices()
        if not devices:
            console.print("[bold red][!] No devices connected.[/bold red]")
            raise typer.Exit(1)
        from adbrv_module.devices import select_device, check_devices_info
        if device:
            target_device = select_device(device)
            unset_proxy_and_reverse(target_device)
            check_devices_info(target_device, show_title=False)
        else:
            for d in devices:
                unset_proxy_and_reverse(d)
            check_devices_info(show_title=False)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="status")
def cmd_status(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Display proxy, reverse port, and frida-server status."""
    try:
        devices = get_connected_devices()
        from adbrv_module.devices import select_device
        if device:
            target_device = select_device(device)
            check_devices_info(target_device)
        else:
            check_devices_info()
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="frida-start")
def cmd_frida_start(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Start frida-server on the device with root privileges."""
    try:
        start_frida_server(device)
        from adbrv_module.devices import check_devices_info
        check_devices_info(show_title=False)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="frida-kill")
def cmd_frida_kill(
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Kill all running frida-server processes on the device."""
    try:
        frida_kill(device)
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="pull")
def cmd_pull(
    package_name: Annotated[str, typer.Argument(help="The package name of the app to pull")],
    path: Annotated[Optional[str], typer.Argument(help="Optional destination path to save the APK")] = None,
    device: Annotated[Optional[str], typer.Option("--device", "-d", help="Specific device serial")] = None,
):
    """Pull an installed APK from the device directly to your computer by package name."""
    try:
        from adbrv_module.pullAPK import pull_apk
        pull_apk(package_name, path, device)
    except Exception as e:
        console.print(f"[bold red]❌ {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="update")
def cmd_update():
    """Automatically update the script to the latest version from GitHub."""
    try:
        update_script()
    except (AdbError, ProxyError, CoreError) as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(
    name="resign",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True}
)
def cmd_resign(
    ctx: typer.Context,
    apk: Annotated[str, typer.Option("--apk", help="The APK file to resign")],
):
    """Resign APK file using the integrated uber-apk-signer tool."""
    try:
        # ctx.args provides any additional arguments passed by the user
        resign_args = ['-a', apk] + ctx.args
        resign_apk(resign_args)
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="checksym")
def cmd_checksym(
    output_folder: Annotated[str, typer.Argument(help="Apktool output folder (e.g. base)")],
):
    """Scan native libraries (.so) in the APK decompiled folder, select ABI, and check symbols."""
    try:
        check_symbols(output_folder)
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="findso")
def cmd_findso():
    """Find .so files in APK files in current directory."""
    try:
        find_so_files()
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

@app.command(name="libsec")
def cmd_libsec():
    """Check security features of .so files (PIE, Stack Canary, Debug symbols)."""
    try:
        check_lib_security()
    except Exception as e:
        console.print(f"[bold red][!] {e}[/bold red]")
        raise typer.Exit(1)

def main():
    app()

if __name__ == "__main__":
    main()
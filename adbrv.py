#!/usr/bin/env python3
__version__ = "2.5.1"
import sys, subprocess
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
        import logging
        logging.getLogger("prompt_toolkit").setLevel(logging.ERROR)
        from prompt_toolkit.application import Application
        Application.cpr_not_supported_callback = lambda self: None
        
        allowed_commands_list = [
            "set", "unset", "status", "frida-start", "frida-kill", "pull",
            "traceui", "help", "exit", "quit", "ss", "--help", "-h"
        ]

        import time
        import threading

        import json
        import os

        packages_cache = []
        cache_file_path = os.path.expanduser("~/.adbrv_packages_cache.json")
        if os.path.isfile(cache_file_path):
            try:
                with open(cache_file_path, "r", encoding="utf-8") as f:
                    packages_cache = json.load(f)
            except Exception:
                packages_cache = []

        _status_lock = threading.Lock()
        _packages_lock = threading.Lock()
        _status_done_event = threading.Event()
        _completion_debounce_timer = None
        _completion_debounce_lock = threading.Lock()
        _workspace_start_time = time.time()

        _initial_status_printed = False

        class StatusCache:
            def __init__(self, initial_devices=None):
                self.devices = initial_devices if initial_devices is not None else ["Optimistic"]
                self.device_models = {}
                self.device_androids = {}
                self.device_roots = {}
                self.device_proxies = {}
                self.device_frida_details = {}
                self.device_reverses = {}
                self.frida = True
                self.unset = True
                
                # Eagerly pre-fetch statuses in background
                self.trigger_update()

            def _fetch_status_worker(self):
                if not _status_lock.acquire(blocking=False):
                    return
                _status_done_event.clear()
                try:
                    from adbrv_module.devices import get_connected_devices
                    devs = get_connected_devices()
                    
                    new_models = {}
                    new_androids = {}
                    new_roots = {}
                    new_proxies = {}
                    new_frida_details = {}
                    new_reverses = {}
                    # Batch check proxy + frida + model + android + root in ONE adb shell call
                    is_any_set = False
                    is_any_frida = False
                    for d in devs:
                        adb_base = ["adb", "-s", d]
                        try:
                            batch_cmd = "settings get global http_proxy; echo '---DELIM---'; ps | grep rida-server; echo '---DELIM---'; getprop ro.product.model; echo '---DELIM---'; getprop ro.build.version.release; echo '---DELIM---'; which su"
                            res = subprocess.run(adb_base + ["shell", batch_cmd], capture_output=True, text=True, timeout=5, stdin=subprocess.DEVNULL)
                            parts = res.stdout.split("---DELIM---")
                            
                            proxy = parts[0].strip() if len(parts) > 0 else ""
                            if proxy and proxy not in [":0", "null", ""]:
                                is_any_set = True
                                new_proxies[d] = proxy
                            else:
                                new_proxies[d] = "null"
                            
                            frida_out = parts[1].strip() if len(parts) > 1 else ""
                            if "rida-server" in frida_out:
                                is_any_frida = True
                                # Parse PID and user from frida output
                                try:
                                    for line in frida_out.splitlines():
                                        if "rida-server" in line:
                                            fparts = line.split()
                                            user = fparts[0] if fparts else "shell"
                                            pid = next((p for p in fparts[1:] if p.isdigit()), None)
                                            new_frida_details[d] = f"On ({user} - PID: {pid})" if pid else f"On ({user})"
                                            break
                                except:
                                    new_frida_details[d] = "On"
                            else:
                                new_frida_details[d] = "Off"
                                
                            model = parts[2].strip() if len(parts) > 2 else ""
                            if model:
                                new_models[d] = model
                            
                            android = parts[3].strip() if len(parts) > 3 else ""
                            if android:
                                new_androids[d] = android
                            
                            su_check = parts[4].strip() if len(parts) > 4 else ""
                            new_roots[d] = bool(su_check)
                        except:
                            pass
                        
                        # Reverse ports per device
                        try:
                            rev = subprocess.run(["adb", "-s", d, "reverse", "--list"], capture_output=True, text=True, timeout=2, stdin=subprocess.DEVNULL)
                            rev_out = rev.stdout.strip()
                            if rev_out:
                                # Parse like get_reverse_ports: take last 2 tokens (strips "UsbFfs" prefix)
                                rev_parts = rev_out.split()[-2:]
                                new_reverses[d] = ' '.join(rev_parts) if rev_parts else "null"
                                is_any_set = True
                            else:
                                new_reverses[d] = "null"
                        except:
                            new_reverses[d] = "null"
                    
                    if self.devices != ["Optimistic"]:
                        old_devs = set(self.devices)
                        new_devs = set(devs)
                        
                        from prompt_toolkit import print_formatted_text
                        from prompt_toolkit.formatted_text import HTML
                        
                        removed = old_devs - new_devs
                        for d in removed:
                            model = self.device_models.get(d, "")
                            display_name = model if model else d
                            print_formatted_text(HTML(f"<ansired>[!] Device disconnected: {display_name}</ansired>"))
                            self.device_models.pop(d, None)
                            
                        added = new_devs - old_devs
                        for d in added:
                            model = new_models.get(d, "")
                            if not model:
                                try:
                                    res = subprocess.run(["adb", "-s", d, "shell", "getprop ro.product.model"], capture_output=True, text=True, timeout=2, stdin=subprocess.DEVNULL)
                                    model = res.stdout.strip()
                                    new_models[d] = model
                                except:
                                    pass
                            display_name = model if model else d
                            print_formatted_text(HTML(f"<ansigreen>[+] Device connected: {display_name}</ansigreen>"))
                            _schedule_packages_fetch()
                            
                    self.devices = devs
                    self.device_models.update(new_models)
                    self.device_androids.update(new_androids)
                    self.device_roots.update(new_roots)
                    self.device_proxies.update(new_proxies)
                    self.device_frida_details.update(new_frida_details)
                    self.device_reverses.update(new_reverses)
                    
                    if not devs:
                        self.unset = False
                        self.frida = False
                        return
                                
                    self.unset = is_any_set
                    self.frida = is_any_frida
                    
                    # Auto-print status table on first fetch
                    self._print_initial_status()
                except Exception:
                    pass
                finally:
                    _status_done_event.set()
                    _status_lock.release()
                    self.trigger_completion()

            def _print_initial_status(self):
                nonlocal _initial_status_printed
                if _initial_status_printed or not self.devices:
                    return
                _initial_status_printed = True
                try:
                    from rich.console import Console
                    from rich.table import Table
                    from rich import box
                    from rich.padding import Padding
                    import io
                    
                    _console = Console(file=io.StringIO(), force_terminal=True)
                    table = Table(title=None, box=box.ROUNDED)
                    table.add_column("Device Serial", style="cyan", no_wrap=True, justify="center")
                    table.add_column("Model", style="magenta", justify="center")
                    table.add_column("Android", justify="center")
                    table.add_column("Root Access", justify="center")
                    table.add_column("Frida", justify="center")
                    table.add_column("Proxy", style="yellow", justify="center")
                    table.add_column("Reverse", style="green", justify="center")
                    
                    for d in self.devices:
                        model = self.device_models.get(d, "?")
                        android = self.device_androids.get(d, "?")
                        root = self.device_roots.get(d, False)
                        root_style = "[bold green]Yes[/bold green]" if root else "[bold red]No[/bold red]"
                        frida = self.device_frida_details.get(d, "Off")
                        frida_style = f"[bold green]{frida}[/bold green]" if "On" in frida else f"[dim]{frida}[/dim]"
                        proxy = self.device_proxies.get(d, "null")
                        reverse = self.device_reverses.get(d, "null")
                        table.add_row(d, model, android, root_style, frida_style, proxy, reverse)
                    
                    _console.print(Padding(table, (0, 0, 0, 2)))
                    table_str = _console.file.getvalue()
                    
                    from prompt_toolkit import print_formatted_text
                    from prompt_toolkit.formatted_text import ANSI
                    print_formatted_text(ANSI(table_str))
                except Exception:
                    pass

            def trigger_update(self):
                threading.Thread(target=self._fetch_status_worker, daemon=True).start()

            def trigger_completion(self):
                nonlocal _completion_debounce_timer
                # Skip during first 3s of startup to avoid event loop spam
                if time.time() - _workspace_start_time < 3:
                    return
                # Debounce: only fire once per 1s window
                with _completion_debounce_lock:
                    if _completion_debounce_timer is not None:
                        _completion_debounce_timer.cancel()
                    def _fire():
                        try:
                            from prompt_toolkit.application import get_app
                            app = get_app()
                            def _do():
                                buf = app.current_buffer
                                if buf.text:
                                    buf.cancel_completion()
                                    buf.start_completion(select_first=False)
                            app.loop.call_soon_threadsafe(_do)
                        except Exception:
                            pass
                    _completion_debounce_timer = threading.Timer(1.0, _fire)
                    _completion_debounce_timer.daemon = True
                    _completion_debounce_timer.start()

            def check_devices(self):
                return self.devices

            def check_frida(self):
                return self.frida

            def check_unset(self):
                return self.unset

            def flush(self, include_packages=True):
                self.trigger_update()
                if include_packages:
                    _schedule_packages_fetch()
                
        # Check connected devices at startup
        from adbrv_module.devices import get_connected_devices
        try:
            init_devs = get_connected_devices()
        except Exception:
            init_devs = []
            
        status_cache = StatusCache(init_devs)
        for d in init_devs:
            try:
                res = subprocess.run(["adb", "-s", d, "shell", "getprop ro.product.model"], capture_output=True, text=True, timeout=2)
                model = res.stdout.strip()
                if model:
                    status_cache.device_models[d] = model
            except Exception:
                pass

        class RealtimeMonitor:
            def __init__(self, cache_instance):
                self.cache = cache_instance
                self.process = None
                self._debounce_timer = None
                self._debounce_lock = threading.Lock()
                self.thread = threading.Thread(target=self._run, daemon=True)
                self.thread.start()

            def _debounced_flush(self):
                """Debounce: only flush once after track-devices settles for 1.5s"""
                with self._debounce_lock:
                    if self._debounce_timer is not None:
                        self._debounce_timer.cancel()
                    self._debounce_timer = threading.Timer(1.5, self.cache.flush)
                    self._debounce_timer.daemon = True
                    self._debounce_timer.start()

            def _run(self):
                import subprocess
                try:
                    self.process = subprocess.Popen(["adb", "track-devices"], stdout=subprocess.PIPE, stdin=subprocess.DEVNULL, text=True)
                    while True:
                        line = self.process.stdout.readline()
                        if not line and self.process.poll() is not None:
                            break
                        # Debounce: wait for track-devices to settle before flushing
                        self._debounced_flush()
                except Exception:
                    pass

            def stop(self):
                if self.process:
                    try:
                        self.process.kill()
                    except:
                        pass
                with self._debounce_lock:
                    if self._debounce_timer is not None:
                        self._debounce_timer.cancel()

        realtime_monitor = RealtimeMonitor(status_cache)

        def is_valid_sentence_prefix(text):
            text_lstrip = text.lstrip()
            if not text_lstrip:
                return True
                
            parts = text_lstrip.split()
            ends_with_space = text_lstrip.endswith(" ") or text_lstrip.endswith("\t")
            
            cmd = parts[0].lower()
            valid_cmds = ["set", "unset", "status", "frida-start", "frida-kill", "pull", "traceui", "ss", "help", "exit", "quit", "--help", "-h"]
            matching_cmds = [c for c in valid_cmds if c.startswith(cmd)]
            
            if not matching_cmds:
                return False
                
            if cmd not in valid_cmds:
                if ends_with_space or len(parts) > 1:
                    return False
                return True

            if cmd in ["pull", "traceui", "set", "unset", "status", "frida-start", "frida-kill"]:
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

            expected_pos = 2 if cmd in ["set", "pull"] else (1 if cmd == "traceui" else 0)
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
                    
            if cmd in ["help", "exit", "quit", "ss", "--help", "-h"]:
                if ends_with_space or len(parts) > 1:
                    return False
                    
            if cmd == "traceui":
                if len(parts) > 2:
                    return False
                if len(parts) == 2 and ends_with_space:
                    return False
                    
            return True

        def fetch_packages_fn():
            if not _packages_lock.acquire(blocking=False):
                return
            try:
                # Wait for status fetching to complete (with timeout, no busy-wait)
                _status_done_event.wait(timeout=10)
                    
                devices = status_cache.check_devices()
                if not devices or devices == ["Optimistic"]:
                    return
                target_device = devices[0]
                
                # Stage 1: Get package list quickly
                try:
                    from adbrv_module.pullAPK import get_installed_packages_fast
                    fast_pkgs = get_installed_packages_fast(target_device)
                    if fast_pkgs:
                        existing_names = {p["id"]: p.get("name", "") for p in packages_cache if p.get("name")}
                        updated_pkgs = []
                        for fp in fast_pkgs:
                            pkg_id = fp["id"]
                            friendly_name = existing_names.get(pkg_id, "")
                            updated_pkgs.append({"id": pkg_id, "name": friendly_name})
                        
                        packages_cache.clear()
                        packages_cache.extend(updated_pkgs)
                        
                        try:
                            with open(cache_file_path, "w", encoding="utf-8") as f:
                                json.dump(packages_cache, f, ensure_ascii=False, indent=2)
                        except:
                            pass
                        status_cache.trigger_completion()
                except Exception:
                    pass

                # Stage 2: Load friendly names using frida-ps in the background
                try:
                    from adbrv_module.pullAPK import get_packages_friendly_names
                    friendly_names = get_packages_friendly_names(target_device)
                    if friendly_names:
                        for pkg_obj in packages_cache:
                            pkg_id = pkg_obj["id"]
                            if pkg_id in friendly_names:
                                pkg_obj["name"] = friendly_names[pkg_id]
                        
                        packages_cache.sort(key=lambda x: not bool(x.get("name")))
                        
                        try:
                            with open(cache_file_path, "w", encoding="utf-8") as f:
                                json.dump(packages_cache, f, ensure_ascii=False, indent=2)
                        except:
                            pass
                        status_cache.trigger_completion()
                except Exception:
                    pass
            finally:
                _packages_lock.release()

        def _schedule_packages_fetch():
            threading.Thread(target=fetch_packages_fn, daemon=True).start()
        
        _schedule_packages_fetch()

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
                            yield Completion("enter your path", start_position=-len(word_before_cursor))
                    elif len(parts) == 3 and not ends_with_space and parts[2].startswith("-"):
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                    elif len(parts) == 3 and ends_with_space:
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))
                    elif len(parts) == 4 and not ends_with_space and parts[3].startswith("-"):
                        if "-d".startswith(word_before_cursor.lower()):
                            yield Completion("-d", start_position=-len(word_before_cursor))

                elif cmd == "traceui":
                    search_word = remove_accents(word_before_cursor.lower())
                    if (len(parts) == 1) or (len(parts) == 2 and not ends_with_space):
                        if parts[0].lower() == "traceui":
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


        
        from prompt_toolkit.patch_stdout import patch_stdout

        console.print("[bold cyan]Welcome to adbrv Workspace. Type 'help' for available commands, 'exit' to quit.[/bold cyan]")
        if not status_cache.devices or status_cache.devices == ["Optimistic"]:
            console.print("[bold red][!] Warning: No devices connected. Please connect a device via USB/Wi-Fi.[/bold red]")
        session = PromptSession(history=InMemoryHistory())
    
        try:
            with patch_stdout(raw=True):
                while True:
                    try:
                        # eager=True in the KeyBinding bypasses the delay
                        cmd = session.prompt("adbrv> ", completer=command_completer, complete_while_typing=False, key_bindings=kb)
                        if not cmd.strip():
                            continue
                        if cmd.strip().lower() in ["exit", "quit", "q"]:
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
                            help_tbl.add_row("ss", "Take a screenshot and copy to clipboard.")
                            help_tbl.add_row("traceui", "Trace UI navigation & click handlers (Activity, Fragment, View clicks).")
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
                            example_tbl.add_row("ss", "Take a screenshot and copy to clipboard (Cmd+V to paste).")
                            example_tbl.add_row("traceui com.example.app", "Trace UI: screens + clicks → find handlers in jadx.")
                            example_panel = Panel(
                                example_tbl,
                                title="Examples",
                                title_align="left",
                                border_style="dim"
                            )
                            console.print(example_panel)
                            
                            continue
                        if cmd.strip().lower() == "ss":
                            try:
                                devs = status_cache.devices
                                if not devs or devs == ["Optimistic"]:
                                    console.print("  [bold red]✖[/bold red] No device connected.")
                                    continue
                                serial = devs[0]
                                result = subprocess.run(
                                    ["adb", "-s", serial, "exec-out", "screencap", "-p"],
                                    capture_output=True, timeout=5, stdin=subprocess.DEVNULL
                                )
                                if result.returncode != 0 or not result.stdout:
                                    console.print("  [bold red]✖[/bold red] Screenshot failed.")
                                    continue
                                tmp_path = "/tmp/adbrv_ss.png"
                                with open(tmp_path, "wb") as f:
                                    f.write(result.stdout)
                                # Fire-and-forget: don't wait for clipboard copy
                                subprocess.Popen(
                                    ["osascript", "-e", f'set the clipboard to (read (POSIX file "{tmp_path}") as «class PNGf»)'],
                                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, stdin=subprocess.DEVNULL
                                )
                                console.print("  [bold green]✔[/bold green] Screenshot copied to clipboard.")
                            except subprocess.TimeoutExpired:
                                console.print("  [bold red]✖[/bold red] Screenshot timed out.")
                            except Exception as e:
                                console.print(f"  [bold red]✖[/bold red] Screenshot error: {e}")
                            continue
                        if cmd.strip().lower().startswith("traceui"):
                            try:
                                parts = cmd.strip().split()
                                if len(parts) < 2:
                                    console.print("  [bold red]✖[/bold red] Usage: traceui <package_name>")
                                    continue

                                package_name = parts[1]

                                # Get device serial from cache
                                devs = status_cache.devices
                                if not devs or devs == ["Optimistic"]:
                                    console.print("  [bold red]✖[/bold red] No device connected.")
                                    continue
                                serial = devs[0]

                                # Look up display name from packages_cache
                                display_name = None
                                for pkg in packages_cache:
                                    if pkg["id"] == package_name:
                                        display_name = pkg.get("name", "")
                                        break

                                if not display_name:
                                    console.print(f"  [bold red]✖[/bold red] App '[bold]{package_name}[/bold]' not found. Make sure the app is installed and running.")
                                    continue

                                # JS template with 3-layer hooks + blacklist noise
                                js_code = """Java.perform(function() {
    var BLACKLIST = ["androidx.", "android.", "com.google.", "com.bumptech.", "com.facebook.", "com.crashlytics.", "com.squareup.", "io.reactivex.", "kotlin.", "kotlinx.", "okhttp3.", "retrofit2.", "dagger.", "javax.", "org."];
    function isNoise(cn) {
        for (var i = 0; i < BLACKLIST.length; i++) {
            if (cn.indexOf(BLACKLIST[i]) === 0) return true;
        }
        return false;
    }

    // Layer 1: Activity tracking
    var Activity = Java.use("android.app.Activity");
    Activity.onResume.implementation = function() {
        var cn = this.getClass().getName();
        if (!isNoise(cn)) {
            console.log("\\n[ACTIVITY] >>> " + cn);
        }
        this.onResume();
    };

    // Layer 2: Fragment tracking
    try {
        var Fragment = Java.use("androidx.fragment.app.Fragment");
        Fragment.onResume.implementation = function() {
            var cn = this.getClass().getName();
            if (!isNoise(cn)) {
                console.log("[FRAGMENT] >>> " + cn);
            }
            this.onResume();
        };
    } catch(e) {}

    // Layer 3: Click tracking via View.performClick
    var View = Java.use("android.view.View");
    var viewClass = View.class;
    var liField = viewClass.getDeclaredField("mListenerInfo");
    liField.setAccessible(true);

    View.performClick.implementation = function() {
        try {
            var li = liField.get(this);
            if (li !== null) {
                var onClickField = li.getClass().getDeclaredField("mOnClickListener");
                onClickField.setAccessible(true);
                var listener = onClickField.get(li);
                if (listener !== null) {
                    var listenerClass = listener.getClass().getName();
                    if (!isNoise(listenerClass)) {
                        var viewName = "";
                        try {
                            var id = this.getId();
                            if (id > 0) viewName = this.getResources().getResourceEntryName(id);
                        } catch(e) {}
                        if (!viewName) viewName = this.getClass().getSimpleName();
                        console.log("[CLICK]    " + viewName + " → " + listenerClass);
                    }
                }
            }
        } catch(e) {}
        return this.performClick();
    };

    console.log("[*] UI Tracer loaded! Navigate and tap to trace...");
});"""

                                tmp_js = "/tmp/adbrv_traceui.js"
                                with open(tmp_js, "w") as f:
                                    f.write(js_code)

                                console.print(f"  [bold cyan][*][/bold cyan] Tracing UI on [bold]{display_name}[/bold]... Press Ctrl+C to stop.")

                                proc = subprocess.Popen(
                                    ["frida", "-D", serial, "-n", display_name, "-l", tmp_js],
                                    stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                                    stdin=subprocess.DEVNULL
                                )
                                try:
                                    for line in proc.stdout:
                                        line = line.rstrip()
                                        if not line:
                                            continue
                                        # Skip Frida banner and noise
                                        if '____' in line or '/ _  |' in line or '| (_| |' in line or '> _  |' in line or '/_/ |_|' in line or '. . . .' in line or 'Commands:' in line or 'More info at' in line or 'Connected to' in line or 'Attaching...' in line:
                                            continue
                                        # Strip REPL prompt prefix [device::app ]->
                                        if ']->' in line:
                                            line = line.split('->', 1)[1].strip()
                                            if not line:
                                                continue
                                        # Color the output
                                        if "[ACTIVITY]" in line:
                                            console.print(f"  [bold magenta]{line}[/bold magenta]")
                                        elif "[FRAGMENT]" in line:
                                            console.print(f"  [bold cyan]{line}[/bold cyan]")
                                        elif "[CLICK]" in line:
                                            console.print()
                                            console.print(f"  [bold green]{line}[/bold green]")
                                        else:
                                            console.print(f"  {line}")
                                except KeyboardInterrupt:
                                    print("\r  ", end="")  # Overwrite ^C
                                    proc.terminate()
                                    try:
                                        proc.wait(timeout=3)
                                    except:
                                        proc.kill()
                                console.print("  [bold yellow][*][/bold yellow] Tracing stopped.")
                            except Exception as e:
                                console.print(f"  [bold red]✖[/bold red] traceui error: {e}")
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
                            # Only flush after state-changing commands to avoid unnecessary lag
                            if args and args[0] in {"set", "unset", "frida-start", "frida-kill"}:
                                status_cache.flush(include_packages=False)
                            
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
            
        from adbrv_module.devices import select_device
        target_device = select_device(device)
        set_proxy(local_port, device_port, target_device)
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
        from adbrv_module.devices import select_device
        if device:
            target_device = select_device(device)
            unset_proxy_and_reverse(target_device)
        else:
            for d in devices:
                unset_proxy_and_reverse(d)
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
        console.print(f"[bold red]✖ {e}[/bold red]")
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
#!/usr/bin/env python3
"""
macOS Task Manager - Terminal TUI with Mouse Support
Built with Textual for clickable UI elements.
"""

import os
import signal
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Static, DataTable, Button, Input, Label
from textual.reactive import reactive
from textual.timer import Timer
from textual import events
import psutil


class CPUWidget(Static):
    """Widget displaying CPU usage."""
    
    cpu_percent = reactive(0.0)
    
    def on_mount(self) -> None:
        self.update_cpu()
        self.set_interval(1.5, self.update_cpu)
    
    def update_cpu(self) -> None:
        self.cpu_percent = psutil.cpu_percent(interval=0.1)
        per_core = psutil.cpu_percent(interval=0.1, percpu=True)
        
        color = "green" if self.cpu_percent < 50 else "yellow" if self.cpu_percent < 80 else "red"
        bar_width = 20
        filled = int((self.cpu_percent / 100) * bar_width)
        bar = f"[{color}]{'█' * filled}[/][dim]{'░' * (bar_width - filled)}[/]"
        
        cores_str = " ".join([f"[{'green' if c < 50 else 'yellow' if c < 80 else 'red'}]{c:4.0f}%[/]" for c in per_core[:8]])
        
        self.update(f"""[bold cyan]CPU Usage[/]
{bar} [{color}]{self.cpu_percent:.1f}%[/]

Cores: {psutil.cpu_count(logical=False)} physical, {psutil.cpu_count(logical=True)} logical
Per Core: {cores_str}""")


class MemoryWidget(Static):
    """Widget displaying memory usage."""
    
    def on_mount(self) -> None:
        self.update_memory()
        self.set_interval(1.5, self.update_memory)
    
    def format_bytes(self, bytes_val: int) -> str:
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_val < 1024:
                return f"{bytes_val:.1f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.1f} PB"
    
    def update_memory(self) -> None:
        mem = psutil.virtual_memory()
        swap = psutil.swap_memory()
        
        color = "green" if mem.percent < 60 else "yellow" if mem.percent < 85 else "red"
        bar_width = 20
        filled = int((mem.percent / 100) * bar_width)
        bar = f"[{color}]{'█' * filled}[/][dim]{'░' * (bar_width - filled)}[/]"
        
        swap_filled = int((swap.percent / 100) * bar_width)
        swap_bar = f"[blue]{'█' * swap_filled}[/][dim]{'░' * (bar_width - swap_filled)}[/]"
        
        self.update(f"""[bold cyan]Memory Usage[/]
{bar} [{color}]{mem.percent:.1f}%[/]
Used: {self.format_bytes(mem.used)} / {self.format_bytes(mem.total)}
Available: {self.format_bytes(mem.available)}

[bold cyan]Swap[/]
{swap_bar} [blue]{swap.percent:.1f}%[/]
Used: {self.format_bytes(swap.used)} / {self.format_bytes(swap.total)}""")


class ProcessTable(DataTable):
    """Clickable process table."""
    
    def on_mount(self) -> None:
        self.add_columns("PID", "Name", "CPU %", "Mem %", "Status")
        self.cursor_type = "row"
        self.zebra_stripes = True
        self.refresh_processes()
        self.set_interval(2.0, self.refresh_processes)
    
    def refresh_processes(self, search_query: str = "") -> None:
        self.clear()
        processes = []
        
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
            try:
                info = proc.info
                if info['pid'] > 0:
                    processes.append({
                        'pid': info['pid'],
                        'name': info['name'] or 'Unknown',
                        'cpu': info['cpu_percent'] or 0,
                        'memory': info['memory_percent'] or 0,
                        'status': info['status'] or 'unknown',
                    })
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Sort by CPU
        processes.sort(key=lambda x: x['cpu'], reverse=True)
        
        # Filter
        if search_query:
            processes = [p for p in processes 
                        if search_query.lower() in p['name'].lower() 
                        or search_query in str(p['pid'])]
        
        # Add rows
        for proc in processes[:30]:
            cpu_style = "red" if proc['cpu'] > 50 else "yellow" if proc['cpu'] > 20 else "green"
            mem_style = "red" if proc['memory'] > 10 else "yellow" if proc['memory'] > 5 else "green"
            
            self.add_row(
                str(proc['pid']),
                proc['name'][:30],
                f"[{cpu_style}]{proc['cpu']:.1f}[/]",
                f"[{mem_style}]{proc['memory']:.1f}[/]",
                proc['status'],
                key=str(proc['pid'])
            )


class TaskManagerApp(App):
    """Main Task Manager Application with mouse support."""
    
    CSS = """
    Screen {
        layout: vertical;
    }
    
    #controls {
        height: 3;
        padding: 0 1;
        layout: horizontal;
        align: left middle;
        dock: top;
    }
    
    #stats-row {
        layout: horizontal;
        height: 12;
    }
    
    #cpu-panel {
        width: 1fr;
        border: round cyan;
        padding: 1;
        margin: 0 1;
    }
    
    #memory-panel {
        width: 1fr;
        border: round cyan;
        padding: 1;
        margin: 0 1;
    }
    
    #process-container {
        border: round cyan;
        padding: 0;
        margin: 0 1;
        height: 1fr;
    }
    
    #search-input {
        width: 20;
    }
    
    .btn {
        width: auto;
        min-width: 10;
        margin: 0 1;
    }
    
    #kill-btn {
        background: darkred;
    }
    
    #message {
        margin-left: 2;
    }
    
    ProcessTable {
        height: 100%;
    }
    """
    
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("r", "refresh", "Refresh"),
        ("k", "kill_selected", "Kill"),
        ("s", "focus_search", "Search"),
        ("escape", "clear_selection", "Clear"),
    ]
    
    message_text = reactive("")
    
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        # Controls at top
        yield Horizontal(
            Input(placeholder="Search...", id="search-input"),
            Button("Search", id="search-btn", variant="primary", classes="btn"),
            Button("Clear", id="clear-btn", classes="btn"),
            Button("KILL", id="kill-btn", variant="error", classes="btn"),
            Button("Refresh", id="refresh-btn", classes="btn"),
            Label("", id="message"),
            id="controls"
        )
        # Stats row
        yield Horizontal(
            Container(CPUWidget(), id="cpu-panel"),
            Container(MemoryWidget(), id="memory-panel"),
            id="stats-row"
        )
        # Process table
        yield Container(
            ProcessTable(id="process-table"),
            id="process-container"
        )
        yield Footer()
    
    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks."""
        if event.button.id == "search-btn":
            self.action_search()
        elif event.button.id == "clear-btn":
            self.action_clear_search()
        elif event.button.id == "kill-btn":
            self.action_kill_selected()
        elif event.button.id == "refresh-btn":
            self.action_refresh()
    
    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle Enter key in search input."""
        self.action_search()
    
    def action_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        table = self.query_one("#process-table", ProcessTable)
        table.refresh_processes(search_input.value)
        self.show_message(f"Filtered by: {search_input.value}" if search_input.value else "Showing all")
    
    def action_clear_search(self) -> None:
        search_input = self.query_one("#search-input", Input)
        search_input.value = ""
        table = self.query_one("#process-table", ProcessTable)
        table.refresh_processes("")
        self.show_message("Search cleared")
    
    def action_refresh(self) -> None:
        table = self.query_one("#process-table", ProcessTable)
        search_input = self.query_one("#search-input", Input)
        table.refresh_processes(search_input.value)
        self.show_message("Refreshed")
    
    def action_kill_selected(self) -> None:
        table = self.query_one("#process-table", ProcessTable)
        
        if table.cursor_row is not None:
            try:
                row_key = table.get_row_at(table.cursor_row)
                pid = int(row_key[0])
                self.kill_process(pid)
            except (ValueError, IndexError):
                self.show_message("No process selected", error=True)
        else:
            self.show_message("Click on a process first", error=True)
    
    def kill_process(self, pid: int) -> None:
        """Kill a process by PID."""
        try:
            os.kill(pid, signal.SIGKILL)
            self.show_message(f"Killed process {pid}")
            self.action_refresh()
        except ProcessLookupError:
            self.show_message(f"Process {pid} not found", error=True)
        except PermissionError:
            self.show_message(f"Permission denied for PID {pid}", error=True)
        except Exception as e:
            self.show_message(f"Error: {e}", error=True)
    
    def show_message(self, text: str, error: bool = False) -> None:
        label = self.query_one("#message", Label)
        color = "red" if error else "green"
        label.update(f"[{color}]→ {text}[/]")
    
    def action_clear_selection(self) -> None:
        self.show_message("")


def main():
    app = TaskManagerApp()
    app.run()


if __name__ == "__main__":
    main()

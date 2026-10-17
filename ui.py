"""Reusable Tk and ttk components for the application design system."""

import ctypes
import os
import tkinter as tk
from tkinter import ttk

from theme import Theme


def _motion_enabled():
    if os.environ.get("CRM_REDUCED_MOTION", "").strip().lower() in {"1", "true", "yes"}:
        return False
    if os.name == "nt":
        try:
            enabled = ctypes.c_int()
            success = ctypes.windll.user32.SystemParametersInfoW(
                0x1042, 0, ctypes.byref(enabled), 0
            )
            if success:
                return bool(enabled.value)
        except (AttributeError, OSError):
            pass
    return True


def _transition(widget, target, duration=100):
    if not _motion_enabled():
        widget.configure(bg=target)
        return
    pending = getattr(widget, "_color_transition", None)
    if pending:
        try:
            widget.after_cancel(pending)
        except tk.TclError:
            pass
    try:
        current = widget.cget("bg")
        start_rgb = tuple(int(current[i:i + 2], 16) for i in (1, 3, 5))
        end_rgb = tuple(int(target[i:i + 2], 16) for i in (1, 3, 5))
    except (tk.TclError, ValueError):
        widget.configure(bg=target)
        return

    steps = 5
    interval = max(1, duration // steps)

    def step(index):
        fraction = min(index / steps, 1)
        color = "#" + "".join(
            f"{round(start + (end - start) * fraction):02x}"
            for start, end in zip(start_rgb, end_rgb)
        )
        try:
            widget.configure(bg=color)
        except tk.TclError:
            return
        if index < steps:
            widget._color_transition = widget.after(interval, lambda: step(index + 1))
        else:
            widget._color_transition = None

    step(1)


def animate_card_entrance(widget):
    """Briefly ease in a card border, honoring reduced-motion preferences."""
    if not _motion_enabled():
        return
    try:
        widget.configure(highlightbackground=Theme.BLUE_LIGHT)
    except tk.TclError:
        return
    def restore_border():
        try:
            if widget.winfo_exists():
                widget.configure(highlightbackground=Theme.BORDER)
        except tk.TclError:
            return

    widget.after(100, restore_border)


def modern_button(parent, text, command=None, kind="primary", width=None, pad=(16, 8)):
    """Create a keyboard-accessible, flat button with restrained hover feedback."""
    palette = {
        "primary": (Theme.BLUE, Theme.BLUE_HOVER, Theme.WHITE),
        "danger": (Theme.RED, Theme.RED_HOVER, Theme.WHITE),
        "success": (Theme.SUCCESS, "#125741", Theme.WHITE),
        "dark": (Theme.NAVY, Theme.NAVY_LIGHT, Theme.WHITE),
        "warning": (Theme.WARNING, "#704410", Theme.WHITE),
        "ghost": (Theme.CARD_ALT, Theme.BLUE_SOFT, Theme.TEXT),
        "sidebar": (Theme.SIDEBAR, Theme.SIDEBAR_HOVER, Theme.TEXT_ON_DARK),
    }
    bg, hover, fg = palette.get(kind, palette["primary"])
    button = tk.Button(
        parent,
        text=text,
        command=command,
        bg=bg,
        fg=fg,
        activebackground=hover,
        activeforeground=fg,
        disabledforeground=Theme.TEXT_MUTED,
        font=Theme.F_BUTTON,
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=pad[0],
        pady=pad[1],
        takefocus=True,
        highlightthickness=1,
        highlightbackground=bg,
        highlightcolor=Theme.BLUE_LIGHT,
    )
    if width:
        button.config(width=width)

    button.bind("<Enter>", lambda _event: _transition(button, hover))
    button.bind("<Leave>", lambda _event: _transition(button, bg))
    button.bind("<FocusIn>", lambda _event: button.config(highlightbackground=Theme.BLUE_LIGHT))
    button.bind("<FocusOut>", lambda _event: button.config(highlightbackground=bg))
    return button


def sidebar_button(parent, text, command, active=False):
    button = tk.Button(
        parent,
        text=text,
        command=command,
        anchor="w",
        bg=Theme.NAVY_LIGHT if active else Theme.SIDEBAR,
        fg=Theme.WHITE if active else Theme.TEXT_SOFT,
        activebackground=Theme.SIDEBAR_HOVER,
        activeforeground=Theme.WHITE,
        font=(Theme.FONT, 10, "bold" if active else "normal"),
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=18,
        pady=12,
        takefocus=True,
        highlightthickness=0,
    )
    button._nav_active = active

    def on_enter(_event):
        if not button._nav_active:
            _transition(button, Theme.SIDEBAR_HOVER)
            button.config(fg=Theme.WHITE)

    def on_leave(_event):
        if not button._nav_active:
            _transition(button, Theme.SIDEBAR)
            button.config(fg=Theme.TEXT_SOFT)

    button.bind("<Enter>", on_enter)
    button.bind("<Leave>", on_leave)
    return button


def apply_global_styles(root=None):
    style = ttk.Style(root)
    try:
        style.theme_use("clam")
    except tk.TclError:
        pass

    style.configure(".", font=Theme.F_BODY, foreground=Theme.TEXT)
    style.configure("TFrame", background=Theme.BG)
    style.configure("Workspace.TFrame", background=Theme.BG)
    style.configure("Card.TFrame", background=Theme.CARD)
    style.configure("TLabel", background=Theme.BG, foreground=Theme.TEXT, font=Theme.F_BODY)
    style.configure("Muted.TLabel", background=Theme.BG, foreground=Theme.TEXT_MUTED)
    style.configure("Card.TLabel", background=Theme.CARD, foreground=Theme.TEXT)

    style.configure(
        "TNotebook",
        background=Theme.BG,
        borderwidth=0,
        tabmargins=0,
    )
    style.configure(
        "TNotebook.Tab",
        background=Theme.BG,
        foreground=Theme.TEXT_MUTED,
        padding=[20, 11],
        font=Theme.F_TAB,
        borderwidth=0,
    )
    style.map(
        "TNotebook.Tab",
        background=[("selected", Theme.CARD)],
        foreground=[("selected", Theme.BLUE)],
    )
    style.layout("Hidden.TNotebook.Tab", [])
    style.configure("Hidden.TNotebook", background=Theme.BG, borderwidth=0)

    style.configure(
        "Treeview",
        font=Theme.F_BODY,
        rowheight=34,
        background=Theme.CARD,
        fieldbackground=Theme.CARD,
        foreground=Theme.TEXT,
        borderwidth=0,
        relief="flat",
    )
    style.configure(
        "Treeview.Heading",
        font=Theme.F_SUBHEAD,
        background=Theme.NAVY,
        foreground=Theme.WHITE,
        relief="flat",
        padding=(10, 12),
    )
    style.map("Treeview.Heading", background=[("active", Theme.NAVY_LIGHT)])
    style.map(
        "Treeview",
        background=[("selected", Theme.BLUE)],
        foreground=[("selected", Theme.WHITE)],
    )

    style.configure(
        "TCombobox",
        fieldbackground=Theme.INPUT,
        background=Theme.CARD,
        foreground=Theme.TEXT,
        arrowcolor=Theme.BLUE,
        bordercolor=Theme.BORDER,
        lightcolor=Theme.BORDER,
        darkcolor=Theme.BORDER,
        padding=7,
    )
    style.map(
        "TCombobox",
        fieldbackground=[("readonly", Theme.INPUT), ("disabled", Theme.CARD_ALT)],
        foreground=[("readonly", Theme.TEXT)],
        bordercolor=[("focus", Theme.BLUE)],
    )

    for orient in ("Vertical", "Horizontal"):
        style.configure(
            f"{orient}.TScrollbar",
            background=Theme.BORDER,
            troughcolor=Theme.BG,
            borderwidth=0,
            arrowcolor=Theme.TEXT_MUTED,
            relief="flat",
        )
        style.map(f"{orient}.TScrollbar", background=[("active", Theme.BLUE_LIGHT)])

    style.configure("TSeparator", background=Theme.BORDER)
    style.configure(
        "TLabelframe",
        background=Theme.CARD,
        bordercolor=Theme.BORDER,
        borderwidth=1,
        relief="solid",
    )
    style.configure(
        "TLabelframe.Label",
        background=Theme.CARD,
        foreground=Theme.NAVY,
        font=Theme.F_SUBHEAD,
    )
    style.configure("TRadiobutton", background=Theme.CARD, foreground=Theme.TEXT, font=Theme.F_BODY)
    style.configure(
        "TProgressbar",
        background=Theme.BLUE,
        troughcolor=Theme.BORDER_SOFT,
        bordercolor=Theme.BORDER_SOFT,
        lightcolor=Theme.BLUE,
        darkcolor=Theme.BLUE,
    )

    if root is not None:
        root.option_add("*Font", Theme.F_BODY)
        root.option_add("*Dialog.msg.font", Theme.F_BODY)
        root.option_add("*background", Theme.BG)
        root.option_add("*foreground", Theme.TEXT)
        root.option_add("*Entry.background", Theme.INPUT)
        root.option_add("*Entry.foreground", Theme.TEXT)
        root.option_add("*Entry.insertBackground", Theme.TEXT)
        root.option_add("*Menu.background", Theme.CARD)
        root.option_add("*Menu.foreground", Theme.TEXT)
        root.option_add("*Menu.activeBackground", Theme.BLUE)
        root.option_add("*Menu.activeForeground", Theme.WHITE)
        root.option_add("*Toplevel.background", Theme.BG)
        root.option_add("*LabelFrame.background", Theme.CARD)
        root.option_add("*Listbox.background", Theme.CARD)
        root.option_add("*Listbox.foreground", Theme.TEXT)


def build_police_header(parent, subtitle="Balochistan Police  /  Secure Records Portal"):
    header = tk.Frame(parent, bg=Theme.NAVY, height=76)
    header.pack(fill="x")
    header.pack_propagate(False)

    title_box = tk.Frame(header, bg=Theme.NAVY)
    title_box.pack(side="left", padx=26, pady=12)
    tk.Label(
        title_box,
        text="CRIMINAL RECORDS",
        font=Theme.F_LOGO,
        bg=Theme.NAVY,
        fg=Theme.WHITE,
    ).pack(anchor="w")
    tk.Label(
        title_box,
        text=subtitle,
        font=Theme.F_SMALL,
        bg=Theme.NAVY,
        fg=Theme.TEXT_SOFT,
    ).pack(anchor="w", pady=(2, 0))
    tk.Frame(parent, bg=Theme.GOLD, height=2).pack(fill="x")
    return header


def add_header_meta(header):
    """Right-side session identity and local clock."""
    box = tk.Frame(header, bg=Theme.NAVY)
    box.pack(side="right", padx=26)
    clock = tk.Label(box, text="", font=Theme.F_SMALL, bg=Theme.NAVY, fg=Theme.TEXT_SOFT)
    clock.pack(anchor="e")
    user = tk.Label(box, text="", font=Theme.F_SUBHEAD, bg=Theme.NAVY, fg=Theme.WHITE)
    user.pack(anchor="e", pady=(3, 0))
    return user, clock


def add_admin_label(header, text):
    user, _clock = add_header_meta(header)
    user.config(text=text)
    return user


def stat_card(parent, title, value="0", color=Theme.BLUE):
    """Return a restrained card and its live value label."""
    card = tk.Frame(
        parent,
        bg=Theme.CARD,
        highlightbackground=Theme.BORDER,
        highlightthickness=1,
        bd=0,
    )
    tk.Frame(card, bg=color, width=4).pack(side="left", fill="y")
    body = tk.Frame(card, bg=Theme.CARD)
    body.pack(side="left", fill="both", expand=True, padx=17, pady=15)
    val = tk.Label(body, text=value, font=Theme.F_STAT, bg=Theme.CARD, fg=Theme.NAVY)
    val.pack(anchor="w")
    tk.Label(body, text=title, font=Theme.F_SMALL, bg=Theme.CARD, fg=Theme.TEXT_MUTED).pack(
        anchor="w", pady=(2, 0)
    )
    return card, val


def darken(hex_color, f=0.82):
    h = hex_color.lstrip("#")
    r, g, b = (int(h[i:i + 2], 16) for i in (0, 2, 4))
    return "#%02x%02x%02x" % (int(r * f), int(g * f), int(b * f))

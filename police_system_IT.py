#!/usr/bin/env python3
import base64
import csv
import io
import json
import os
import subprocess
import uuid
import webbrowser
from datetime import datetime
from tkinter import filedialog, messagebox

import tkinter as tk
from tkinter import ttk
import customtkinter as ctk
import pycountry
try:
    from sqlcipher3 import dbapi2 as sqlite3
except ModuleNotFoundError:
    import sqlite3

from PIL import Image, ImageTk
from pypdf import PdfReader, PdfWriter
from config import (
    APP_NAME,
    APP_VERSION,
    BASE_DIR,
    BACKUP_DIR,
    CRIMINALS_DB,
    IDLE_TIMEOUT_MS,
    MEDIA_DIR,
    ORGANIZATION,
    POLICE_DB as AUTH_DB_PATH,
    RESOURCE_DIR,
    ensure_directories,
    is_under_dir,
)
from theme import Theme
from ui import (
    add_header_meta,
    animate_card_entrance,
    apply_global_styles,
    build_police_header,
    modern_button,
    sidebar_button,
    stat_card,
)
from security import (
    account_lock_seconds,
    auth_connect,
    ensure_user_security_columns,
    hash_password,
    is_default_password,
    password_issues,
    register_failure,
    register_success,
    valid_username,
    verify_password,
)
from secure_storage import (
    decrypt_photo_data,
    encrypt_photo_data,
    protect_photo_file,
    secure_connect,
    secure_output_path,
    secure_permissions,
)

DATABASE_NAME = CRIMINALS_DB

STATUS_OPTIONS = ["Wanted", "Arrested", "Incarcerated", "Released", "Deceased"]

LEGACY_NATIONALITY_OPTIONS = (
    "Afghan", "Albanian", "Algerian", "American", "Andorran", "Angolan",
    "Anguillan", "Antiguan and Barbudan", "Argentine", "Armenian", "Aruban",
    "Australian", "Austrian", "Azerbaijani", "Bahamian", "Bahraini", "Bangladeshi",
    "Barbadian", "Belarusian", "Belgian", "Belizean", "Beninese", "Bermudian",
    "Bhutanese", "Bolivian", "Bosnian and Herzegovinian", "Botswanan", "Brazilian",
    "British", "British Virgin Islander", "Bruneian", "Bulgarian", "Burkinabe",
    "Burmese", "Burundian", "Cabo Verdean", "Cambodian", "Cameroonian", "Canadian",
    "Caymanian", "Central African", "Chadian", "Chilean", "Chinese", "Colombian",
    "Comorian", "Congolese (Republic of the Congo)", "Congolese (DR Congo)",
    "Cook Islander", "Costa Rican", "Croatian", "Cuban", "Curacaoan", "Cypriot",
    "Czech", "Danish", "Djiboutian", "Dominican (Dominica)",
    "Dominican (Dominican Republic)", "Dutch", "East Timorese", "Ecuadorean", "Egyptian",
    "Salvadoran", "Equatorial Guinean", "Eritrean", "Estonian", "Eswatini", "Ethiopian",
    "Faroese", "Fijian", "Filipino", "Finnish", "French", "French Guianese",
    "French Polynesian", "Gabonese", "Gambian", "Georgian", "German", "Ghanaian",
    "Gibraltarian", "Greek", "Greenlandic", "Grenadian", "Guadeloupean", "Guamanian",
    "Guatemalan", "Guernsey", "Guinean", "Bissau-Guinean", "Guyanese", "Haitian",
    "Honduran", "Hong Konger", "Hungarian", "Icelandic", "Indian", "Indonesian",
    "Iranian", "Iraqi", "Irish", "Israeli", "Italian", "Ivorian", "Jamaican",
    "Japanese", "Jerseyan", "Jordanian", "Kazakh", "Kenyan", "Kittitian and Nevisian",
    "Kiribati", "Kosovar", "Kuwaiti", "Kyrgyz", "Lao", "Latvian", "Lebanese",
    "Liberian", "Libyan", "Liechtensteiner", "Lithuanian", "Luxembourgish", "Macanese",
    "Macedonian", "Malagasy", "Malawian", "Malaysian", "Maldivian", "Malian", "Maltese",
    "Manx", "Marshallese", "Martinican", "Mauritanian", "Mauritian", "Mexican",
    "Micronesian", "Moldovan", "Monegasque", "Mongolian", "Montenegrin", "Montserratian",
    "Moroccan", "Mozambican", "Namibian", "Nauruan", "Nepalese", "New Caledonian",
    "New Zealander", "Nicaraguan", "Nigerien", "Nigerian", "Niuean", "North Korean",
    "Northern Mariana Islander", "Norwegian", "Omani", "Pakistani", "Palauan",
    "Palestinian", "Panamanian", "Papua New Guinean", "Paraguayan", "Peruvian",
    "Polish", "Portuguese", "Puerto Rican", "Qatari", "Reunionese", "Romanian",
    "Russian", "Rwandan", "Saint Lucian", "Saint Vincentian", "Samoan", "San Marinese",
    "Sao Tomean", "Saudi Arabian", "Senegalese", "Serbian", "Seychellois",
    "Sierra Leonean", "Singaporean", "Sint Maartener", "Slovak", "Slovenian",
    "Solomon Islander", "Somali", "South African", "South Korean", "South Sudanese",
    "Spanish", "Sri Lankan", "Sudanese", "Surinamese", "Swedish", "Swiss", "Syrian",
    "Taiwanese", "Tajik", "Tanzanian", "Thai", "Togolese", "Tokelauan", "Tongan",
    "Trinidadian and Tobagonian", "Tunisian", "Turkish", "Turkmen", "Tuvaluan", "Ugandan",
    "Ukrainian", "Emirati", "Uruguayan", "Uzbek", "Vanuatuan", "Vatican", "Venezuelan",
    "Vietnamese", "Yemeni", "Zambian", "Zimbabwean", "Other",
)
NATIONALITY_OPTIONS = tuple(sorted(
    {country.name for country in pycountry.countries}
    | set(LEGACY_NATIONALITY_OPTIONS),
    key=str.casefold,
))

STATUS_COLORS = Theme.STATUS

TREE_COLUMNS = ("id", "name", "alias", "dob", "gender", "nationality", "location", "crimes", "status", "arrest_date")
TREE_HEADINGS = (
"ID", "Full Name", "Alias", "Date of Birth", "Gender", "Nationality", "Last Location", "Crimes", "Status",
"Arrest Date")
TREE_WIDTHS = (50, 160, 110, 100, 70, 110, 140, 200, 100, 100)
TREE_ANCHORS = (tk.CENTER, tk.W, tk.W, tk.CENTER, tk.CENTER, tk.W, tk.W, tk.W, tk.CENTER, tk.CENTER)

RECORD_PDF_ATTACHMENT = "criminal_records.json"
RECORD_PDF_FORMAT = "criminal-record-export"
RECORD_PDF_VERSION = 1

RECORD_EXPORT_FIELDS = (
    "id", "first_name", "last_name", "alias", "cnic", "date_of_birth", "gender",
    "nationality", "last_known_location", "crimes", "status", "arrest_date",
    "release_date", "notes", "case_number", "created_at", "updated_at",
)


def spreadsheet_safe_value(value):
    if not isinstance(value, str):
        return value
    if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")):
        return "'" + value
    return value


def spreadsheet_safe_row(values):
    return [spreadsheet_safe_value(value) for value in values]


def read_records_pdf(path: str) -> list[tuple[dict, bytes | None]]:
    reader = PdfReader(path, strict=True)
    attachments = reader.attachments.get(RECORD_PDF_ATTACHMENT, [])
    if len(attachments) != 1:
        raise ValueError("This PDF does not contain one valid app-exported records attachment.")
    try:
        payload = json.loads(attachments[0].decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("The records attachment in this PDF is invalid.") from exc
    if (
        not isinstance(payload, dict)
        or payload.get("format") != RECORD_PDF_FORMAT
        or payload.get("version") != RECORD_PDF_VERSION
        or not isinstance(payload.get("records"), list)
        or not payload["records"]
    ):
        raise ValueError("This PDF is not a supported criminal-record export.")

    imported_records = []
    for index, record in enumerate(payload["records"], start=1):
        if not isinstance(record, dict):
            raise ValueError(f"Record {index} in the PDF is invalid.")
        if not isinstance(record.get("first_name"), str) or not record["first_name"].strip():
            raise ValueError(f"Record {index} is missing a first name.")
        if not isinstance(record.get("last_name"), str) or not record["last_name"].strip():
            raise ValueError(f"Record {index} is missing a last name.")
        for field in RECORD_EXPORT_FIELDS:
            if field == "id":
                continue
            value = record.get(field)
            if value is not None and not isinstance(value, str):
                raise ValueError(f"Record {index} contains an invalid {field.replace('_', ' ')}.")
        id_error = national_id_validation_error(
            record.get("nationality") or "", record.get("cnic") or ""
        )
        if id_error:
            raise ValueError(f"Record {index}: {id_error}")

        photo_data = record.get("photo")
        if photo_data is not None:
            if not isinstance(photo_data, str):
                raise ValueError(f"Record {index} contains an invalid photo.")
            try:
                decoded_photo = base64.b64decode(photo_data, validate=True)
                with Image.open(io.BytesIO(decoded_photo)) as photo:
                    photo.verify()
            except (ValueError, OSError) as exc:
                raise ValueError(f"Record {index} contains an invalid photo.") from exc
        else:
            decoded_photo = None
        imported_records.append((record, decoded_photo))
    return imported_records


def _secure_existing_photos() -> None:
    conn = secure_connect(DATABASE_NAME)
    try:
        rows = conn.execute(
            "SELECT id,first_name,last_name,photo_path FROM criminals "
            "WHERE photo_path IS NOT NULL AND photo_path!=''"
        ).fetchall()
        for record_id, first_name, last_name, photo_path in rows:
            resolved_path = (
                photo_path
                if os.path.isabs(photo_path)
                else os.path.join(BASE_DIR, photo_path)
            )
            resolved_path = os.path.abspath(resolved_path)
            if not os.path.isfile(resolved_path):
                continue
            if is_under_dir(resolved_path, MEDIA_DIR):
                protect_photo_file(resolved_path)
                if resolved_path != photo_path:
                    conn.execute(
                        "UPDATE criminals SET photo_path=? WHERE id=?",
                        (resolved_path, record_id),
                    )
            else:
                managed_path = copy_photo_to_media(
                    resolved_path, first_name, last_name
                )
                conn.execute(
                    "UPDATE criminals SET photo_path=? WHERE id=?",
                    (managed_path, record_id),
                )
        conn.commit()
    finally:
        conn.close()


def _photo_embedding_from_path(engine, path: str):
    with open(path, "rb") as photo_file:
        data = decrypt_photo_data(photo_file.read())
    image = cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if image is None:
        raise ValueError("Saved photo could not be decoded.")
    return engine.embedding_from_image(image)


def get_db_connection() -> sqlite3.Connection | None:
    try:
        ensure_directories()
        conn = secure_connect(DATABASE_NAME, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.execute("PRAGMA busy_timeout=5000")
        return conn
    except (sqlite3.Error, OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as e:
        messagebox.showerror("Database Error", f"Failed to connect to database:\n{e}")
        return None


def init_db():
    ensure_directories()
    conn = secure_connect(DATABASE_NAME)
    conn.execute("PRAGMA foreign_keys=ON")
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS criminals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            alias TEXT,
            date_of_birth TEXT,
            gender TEXT,
            nationality TEXT,
            last_known_location TEXT,
            crimes TEXT,
            status TEXT,
            arrest_date TEXT,
            release_date TEXT,
            notes TEXT,
            photo_path TEXT,
            photo_data BLOB,
            fingerprint_data BLOB,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_action TEXT NOT NULL,
            table_name TEXT NOT NULL,
            record_id INTEGER,
            old_values TEXT,
            new_values TEXT,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def validate_date(value: str) -> bool:
    if not value:
        return True
    try:
        datetime.strptime(value, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def _auto_date_dash(entry) -> None:
    digits = "".join(ch for ch in entry.get() if ch.isdigit())[:8]
    if not digits:
        entry.set_value("")
        return
    if len(digits) <= 4:
        fmt = digits
    elif len(digits) <= 6:
        fmt = digits[:4] + "-" + digits[4:]
    else:
        fmt = digits[:4] + "-" + digits[4:6] + "-" + digits[6:8]
    if fmt != entry.get():
        entry.set_value(fmt)
    try:
        entry.icursor(len(fmt))
    except Exception:
        pass


def _canvas_yview(canvas, units) -> None:
    try:
        if canvas.winfo_exists():
            canvas.yview_scroll(units, "units")
    except tk.TclError:
        pass


def _canvas_wheel(canvas, event) -> None:
    try:
        if canvas.winfo_exists() and canvas.winfo_containing(event.x_root, event.y_root) == canvas:
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
    except tk.TclError:
        pass


def _rebind_default_scroll(app) -> None:
    ca = getattr(app, "add_scroll_canvas", None)
    if ca is None or not ca.winfo_exists():
        return
    try:
        ca.bind_all("<MouseWheel>", lambda e, _c=ca: _canvas_wheel(_c, e))
        ca.bind_all("<Button-4>", lambda e, _c=ca: _canvas_yview(_c, -1))
        ca.bind_all("<Button-5>", lambda e, _c=ca: _canvas_yview(_c, 1))
    except Exception:
        pass


def safe_str(val) -> str:
    if val is None:
        return ""
    return str(val).replace('\x00', '').replace('\n', ' ').replace('\r', ' ')


def copy_photo_to_media(source_path: str, first_name: str, last_name: str) -> str:
    try:
        img = Image.open(source_path)
        img.load()
    except (OSError, ValueError) as exc:
        raise ValueError("Uploaded file is not a valid image.") from exc
    return _save_photo_to_media(img, first_name, last_name)


def save_photo_bytes_to_media(photo_data: bytes, first_name: str, last_name: str) -> str:
    try:
        img = Image.open(io.BytesIO(photo_data))
        img.load()
    except (OSError, ValueError) as exc:
        raise ValueError("Imported record photo is not a valid image.") from exc
    return _save_photo_to_media(img, first_name, last_name)


def _save_photo_to_media(img: Image.Image, first_name: str, last_name: str) -> str:
    os.makedirs(MEDIA_DIR, exist_ok=True)
    safe_fn = "".join(c for c in first_name if c.isalnum() or c in "_- ").strip() or "unknown"
    safe_ln = "".join(c for c in last_name if c.isalnum() or c in "_- ").strip() or "unknown"
    filename = f"{safe_fn}_{safe_ln}_{uuid.uuid4().hex[:8]}.jpg"
    dest = os.path.abspath(os.path.join(MEDIA_DIR, filename))
    if not is_under_dir(dest, MEDIA_DIR):
        raise ValueError("Invalid photo destination.")
    img.thumbnail((800, 800), Image.Resampling.LANCZOS)
    image_data = io.BytesIO()
    img.convert("RGB").save(image_data, format="JPEG", quality=85, optimize=True)
    with open(dest, "wb") as photo_file:
        photo_file.write(encrypt_photo_data(image_data.getvalue()))
    secure_permissions(dest)
    return dest


def load_photo_for_label(label: tk.Label, photo_path: str | None, photo_data: bytes | None,
                         max_w: int = 200, max_h: int = 250):
    img = None
    if photo_path and os.path.exists(photo_path):
        try:
            with open(photo_path, "rb") as photo_file:
                img = Image.open(io.BytesIO(decrypt_photo_data(photo_file.read())))
        except Exception:
            pass
    if img is None and photo_data:
        try:
            img = Image.open(io.BytesIO(photo_data))
        except Exception:
            pass
    if img:
        img.thumbnail((max_w, max_h), Image.Resampling.LANCZOS)
        tk_img = ImageTk.PhotoImage(img)
        label.config(image=tk_img, text="")
        label.image = tk_img
    else:
        label.config(image="", text="No photo available")
        label.image = None


class StyledEntry(tk.Entry):
    def __init__(self, parent, placeholder="", placeholder_color=Theme.TEXT_MUTED,
                 focus_color=Theme.BLUE, normal_fg=Theme.TEXT, **kwargs):
        super().__init__(parent, **kwargs)
        self.placeholder = placeholder
        self.placeholder_color = placeholder_color
        self.focus_color = focus_color
        self.normal_fg = normal_fg
        self._placeholder_shown = False

        if placeholder:
            self._show_placeholder()

        self.bind("<FocusIn>", self._on_focus_in)
        self.bind("<FocusOut>", self._on_focus_out)

    def _show_placeholder(self):
        self.delete(0, tk.END)
        self.insert(0, self.placeholder)
        self.config(fg=self.placeholder_color)
        self._placeholder_shown = True

    def _on_focus_in(self, _event=None):
        if self._placeholder_shown:
            self.delete(0, tk.END)
            self.config(fg=self.normal_fg)
            self._placeholder_shown = False
        self.config(highlightcolor=self.focus_color, highlightthickness=2,
                    highlightbackground=Theme.BLUE_LIGHT)

    def _on_focus_out(self, _event=None):
        if not tk.Entry.get(self):
            self._show_placeholder()
        self.config(highlightthickness=1, highlightbackground=Theme.BORDER)

    def get_value(self) -> str:
        if self._placeholder_shown:
            return ""
        return tk.Entry.get(self)

    def set_value(self, value: str):
        self._placeholder_shown = False
        self.delete(0, tk.END)
        if value:
            self.insert(0, value)
            self.config(fg=self.normal_fg)
        else:
            if self.placeholder:
                self._show_placeholder()


class StyledCombobox(ttk.Combobox):
    def get_value(self) -> str:
        return self.get()
    def set_value(self, value: str):
        self.set(value)


def make_treeview(parent, columns=TREE_COLUMNS, headings=TREE_HEADINGS,
                  widths=TREE_WIDTHS, anchors=TREE_ANCHORS) -> ttk.Treeview:
    frame = tk.Frame(parent, bg=Theme.BG)
    frame.pack(fill=tk.BOTH, expand=True)

    vsb = ttk.Scrollbar(frame, orient="vertical")
    hsb = ttk.Scrollbar(frame, orient="horizontal")

    tree = ttk.Treeview(frame, columns=columns, show="headings",
                        selectmode="browse",
                        yscrollcommand=vsb.set, xscrollcommand=hsb.set)
    vsb.config(command=tree.yview)
    hsb.config(command=tree.xview)

    for col, head, w, anch in zip(columns, headings, widths, anchors):
        tree.heading(col, text=head, anchor=anch)
        tree.column(col, width=w, anchor=anch, minwidth=40)

    vsb.pack(side=tk.RIGHT, fill=tk.Y)
    hsb.pack(side=tk.BOTTOM, fill=tk.X)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    tree.tag_configure("evenrow", background=Theme.ROW_ALT)
    tree.tag_configure("oddrow", background=Theme.CARD)
    return tree


def populate_tree(tree: ttk.Treeview, criminals: list):
    tree.delete(*tree.get_children())
    for i, c in enumerate(criminals):
        vals = (
            safe_str(c[0]),
            f"{safe_str(c[1])} {safe_str(c[2])}".strip(),
            safe_str(c[3]),
            safe_str(c[4]),
            safe_str(c[5]),
            safe_str(c[6]),
            safe_str(c[7]),
            safe_str(c[8]),
            safe_str(c[9]),
            safe_str(c[10]),
        )
        tree.insert("", tk.END, values=vals, tags=("evenrow" if i % 2 == 0 else "oddrow",))


class CriminalDatabaseApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1440x900")
        self.root.minsize(980, 640)
        self.root.configure(bg=Theme.BG)
        apply_global_styles(self.root)
        header = build_police_header(self.root)
        self.header_user_label, self.header_clock_label = add_header_meta(header)
        signed_in = getattr(self, "current_user", {})
        signed_in_name = signed_in.get("full_name") or signed_in.get("username")
        self.header_user_label.config(
            text=(
                f"{signed_in_name}  ·  @{signed_in.get('username')}  ·  "
                f"{signed_in.get('role', 'Secure session')}"
                if signed_in_name else "Secure session"
            )
        )
        self._tick_clock()

        self.photo_image: ImageTk.PhotoImage | None = None
        self.photo_path: str = ""
        self._idle_after = None

        init_db()
        self._apply_styles()
        self._create_menu_bar()
        self._build_footer()
        self._build_notebook()
        self.root.bind_all("<KeyPress>", self._reset_idle_timeout, add="+")
        self.root.bind_all("<ButtonPress>", self._reset_idle_timeout, add="+")
        self._reset_idle_timeout()

    def _reset_idle_timeout(self, _event=None):
        if self._idle_after is not None:
            self.root.after_cancel(self._idle_after)
        self._idle_after = self.root.after(IDLE_TIMEOUT_MS, self._expire_idle_session)

    def _expire_idle_session(self):
        self._idle_after = None
        session = getattr(self, "_session", None)
        if session is not None:
            session["relaunch"] = True
            session["notice"] = "Session locked after inactivity."
        try:
            self.root.quit()
        except tk.TclError:
            pass

    def _tick_clock(self):
        try:
            self.header_clock_label.config(text=datetime.now().strftime("%d %b %Y   %H:%M:%S"))
            self.root.after(1000, self._tick_clock)
        except tk.TclError:
            pass

    def _build_footer(self):
        foot = tk.Frame(self.root, bg=Theme.NAVY, height=28)
        foot.pack(fill=tk.X, side=tk.BOTTOM)
        foot.pack_propagate(False)
        self.footer_label = tk.Label(
            foot, text=f"{ORGANIZATION}   /   {APP_NAME} v{APP_VERSION}   /   Local workspace",
            font=Theme.F_SMALL, bg=Theme.NAVY, fg=Theme.TEXT_SOFT, anchor="w"
        )
        self.footer_label.pack(side=tk.LEFT, padx=14)
        self.session_label = tk.Label(
            foot, text="●  SECURE SESSION", font=Theme.F_SMALL,
            bg=Theme.NAVY, fg="#89D7B8", anchor="e"
        )
        self.session_label.pack(side=tk.RIGHT, padx=20)

    def _apply_styles(self):
        apply_global_styles(self.root)

    def _create_menu_bar(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Export All Records to PDF", command=self.export_records_pdf)
        file_menu.add_command(label="Import Records from PDF", command=self.import_records_pdf)
        file_menu.add_command(label="Database Backup", command=self.backup_database)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.root.quit)
        menubar.add_cascade(label="File", menu=file_menu)

        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Statistics", command=lambda: self.notebook.select(self.stats_frame))
        tools_menu.add_command(label="Clear All Data", command=self.clear_all_data)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        self._tools_menu = tools_menu

        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)

    def _build_notebook(self):
        self.workspace = tk.Frame(self.root, bg=Theme.BG)
        self.workspace.pack(fill=tk.BOTH, expand=True)
        self.sidebar = tk.Frame(self.workspace, bg=Theme.SIDEBAR, width=232)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)

        brand = tk.Frame(self.sidebar, bg=Theme.SIDEBAR)
        brand.pack(fill=tk.X, padx=18, pady=(25, 22))
        tk.Label(
            brand, text="CRM", font=(Theme.FONT, 22, "bold"),
            bg=Theme.SIDEBAR, fg=Theme.WHITE
        ).pack(anchor="w")
        tk.Label(
            brand, text="RECORDS CONSOLE", font=(Theme.FONT, 8, "bold"),
            bg=Theme.SIDEBAR, fg=Theme.GOLD
        ).pack(anchor="w", pady=(2, 0))
        tk.Frame(self.sidebar, bg="#29354A", height=1).pack(fill=tk.X, padx=18, pady=(0, 18))
        tk.Label(
            self.sidebar, text="WORKSPACE", font=(Theme.FONT, 8, "bold"),
            bg=Theme.SIDEBAR, fg="#738198", anchor="w"
        ).pack(fill=tk.X, padx=20, pady=(0, 7))
        self._nav_area = tk.Frame(self.sidebar, bg=Theme.SIDEBAR)
        self._nav_area.pack(fill=tk.X)
        self._nav_buttons = {}
        profile = tk.Frame(self.sidebar, bg=Theme.SIDEBAR)
        profile.pack(side=tk.BOTTOM, fill=tk.X, padx=18, pady=18)
        tk.Frame(profile, bg="#29354A", height=1).pack(fill=tk.X, pady=(0, 12))
        user = getattr(self, "current_user", {})
        tk.Label(
            profile, text=user.get("full_name") or user.get("username") or "Secure session",
            font=Theme.F_SUBHEAD, bg=Theme.SIDEBAR, fg=Theme.WHITE, anchor="w"
        ).pack(fill=tk.X)
        tk.Label(
            profile, text=user.get("role", "LOCAL ACCESS").upper(),
            font=(Theme.FONT, 8, "bold"), bg=Theme.SIDEBAR, fg=Theme.TEXT_SOFT, anchor="w"
        ).pack(fill=tk.X, pady=(3, 0))
        self.sidebar_logout_button = modern_button(
            profile, "Sign out", self.logout, "danger", pad=(10, 6)
        )
        self.sidebar_logout_button.pack(fill=tk.X, pady=(12, 0))

        self.main_content = tk.Frame(self.workspace, bg=Theme.BG)
        self.main_content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.notebook = ttk.Notebook(self.main_content, style="Hidden.TNotebook")
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=22, pady=18)
        self.notebook.bind("<<NotebookTabChanged>>", self._sync_navigation)

        self.dashboard_frame = ttk.Frame(
            self.notebook, padding=18, style="Workspace.TFrame"
        )
        self.add_frame = ttk.Frame(self.notebook, padding=12, style="Workspace.TFrame")
        self.view_frame = ttk.Frame(self.notebook, padding=12, style="Workspace.TFrame")
        self.stats_frame = ttk.Frame(self.notebook, padding=12, style="Workspace.TFrame")

        self.notebook.add(self.dashboard_frame, text="Dashboard")
        self.notebook.add(self.add_frame, text="Add Record")
        self.notebook.add(self.view_frame, text="Records")
        self.notebook.add(self.stats_frame, text="Analytics")
        self._add_nav_item("⌂   Overview", self.dashboard_frame)
        self._add_nav_item("+   Add record", self.add_frame)
        self._add_nav_item("≡   Records", self.view_frame)
        self._add_nav_item("◷   Analytics", self.stats_frame)

        self._setup_dashboard_frame()
        self._setup_add_frame()
        self._setup_view_frame()
        self._setup_stats_frame()
        self.notebook.select(self.dashboard_frame)
        self._sync_navigation()

    def _add_nav_item(self, text, page):
        button = sidebar_button(
            self._nav_area,
            text,
            lambda target=page: self.notebook.select(target),
        )
        button.pack(fill=tk.X, padx=10, pady=2)
        self._nav_buttons[str(page)] = button

    def _sync_navigation(self, _event=None):
        selected = self.notebook.select()
        for page_id, button in self._nav_buttons.items():
            active = page_id == selected
            button._nav_active = active
            button.configure(
                bg=Theme.NAVY_LIGHT if active else Theme.SIDEBAR,
                fg=Theme.WHITE if active else Theme.TEXT_SOFT,
                font=(Theme.FONT, 10, "bold" if active else "normal"),
            )

    def _setup_dashboard_frame(self):
        frame = self.dashboard_frame
        hero = tk.Frame(frame, bg=Theme.BG)
        hero.pack(fill=tk.X, pady=(0, 17))
        welcome = tk.Frame(hero, bg=Theme.BG)
        welcome.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 16))
        user = getattr(self, "current_user", {})
        display_name = user.get("full_name") or user.get("username") or "Officer"
        self.dashboard_welcome_label = tk.Label(
            welcome,
            text=f"Welcome back, {display_name}",
            font=Theme.F_TITLE,
            bg=Theme.BG,
            fg=Theme.TEXT,
        )
        self.dashboard_welcome_label.pack(anchor="w")
        tk.Label(
            welcome,
            text="Your secure records workspace at a glance.",
            font=Theme.F_BODY,
            bg=Theme.BG,
            fg=Theme.TEXT_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        self._dashboard_labels = {}
        cards = tk.Frame(frame, bg=Theme.BG)
        cards.pack(fill=tk.X)
        for column in range(2):
            cards.grid_columnconfigure(column, weight=1, uniform="dashboard-card")
        metrics = (
            ("total", "Total records", Theme.BLUE),
            ("wanted", "Wanted", Theme.RED),
            ("custody", "In custody", Theme.WARNING),
            ("photos", "Records with photos", Theme.SUCCESS),
        )
        for index, (key, title, accent) in enumerate(metrics):
            card, value = stat_card(cards, title, "—", accent)
            card.grid(row=index // 2, column=index % 2, sticky="nsew", padx=6, pady=6)
            self._dashboard_labels[key] = value
            animate_card_entrance(card)

        actions = tk.Frame(
            frame, bg=Theme.CARD, highlightbackground=Theme.BORDER, highlightthickness=1
        )
        actions.pack(fill=tk.X, padx=6, pady=(18, 0))
        tk.Label(
            actions, text="QUICK ACTIONS", font=(Theme.FONT, 8, "bold"),
            bg=Theme.CARD, fg=Theme.TEXT_MUTED
        ).pack(anchor="w", padx=18, pady=(15, 5))
        action_row = tk.Frame(actions, bg=Theme.CARD)
        action_row.pack(fill=tk.X, padx=12, pady=(0, 15))
        modern_button(
            action_row, "＋  Add a record",
            lambda: self.notebook.select(self.add_frame), "primary"
        ).pack(side=tk.LEFT, padx=5)
        modern_button(
            action_row, "Browse records",
            lambda: self.notebook.select(self.view_frame), "ghost"
        ).pack(side=tk.LEFT, padx=5)
        modern_button(
            action_row, "View analytics",
            lambda: self.notebook.select(self.stats_frame), "ghost"
        ).pack(side=tk.LEFT, padx=5)

    def refresh_dashboard(self):
        if not hasattr(self, "_dashboard_labels"):
            return
        conn = get_db_connection()
        if not conn:
            return
        try:
            row = conn.execute(
                """SELECT COUNT(*),
                          SUM(CASE WHEN status='Wanted' THEN 1 ELSE 0 END),
                          SUM(CASE WHEN status IN ('Arrested','Incarcerated') THEN 1 ELSE 0 END),
                          SUM(CASE WHEN (photo_path IS NOT NULL AND photo_path!='')
                                    OR photo_data IS NOT NULL THEN 1 ELSE 0 END)
                   FROM criminals"""
            ).fetchone()
        finally:
            conn.close()
        for key, value in zip(("total", "wanted", "custody", "photos"), row):
            self._dashboard_labels[key].config(text=str(value or 0))

    def _setup_add_frame(self):
        frame = self.add_frame

        main = tk.Frame(frame, bg=Theme.BG)
        main.pack(fill=tk.BOTH, expand=True)

        form_outer = tk.Frame(
            main, bg=Theme.CARD, bd=0, highlightthickness=1,
            highlightbackground=Theme.BORDER
        )
        form_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8), pady=4)

        tk.Label(form_outer, text="Add a criminal record",
                 font=Theme.F_HEADING, fg=Theme.TEXT, bg=Theme.CARD
                 ).pack(anchor="w", padx=14, pady=(12, 4))
        ttk.Separator(form_outer, orient="horizontal").pack(fill=tk.X, padx=14, pady=(0, 8))

        scroll_canvas = tk.Canvas(form_outer, bg=Theme.CARD, highlightthickness=0)
        scroll_canvas.pack(fill=tk.BOTH, expand=True, padx=8)
        form_frame = tk.Frame(scroll_canvas, bg=Theme.CARD)
        scroll_window = scroll_canvas.create_window((0, 0), window=form_frame, anchor="nw")
        form_frame.bind("<Configure>",
                        lambda e: scroll_canvas.configure(scrollregion=scroll_canvas.bbox("all")))
        scroll_canvas.bind("<Configure>",
                           lambda e: scroll_canvas.itemconfigure(scroll_window, width=e.width))
        vsb = ttk.Scrollbar(form_outer, orient="vertical", command=scroll_canvas.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_canvas.configure(yscrollcommand=vsb.set)
        scroll_canvas.bind_all("<MouseWheel>",
                               lambda e, _c=scroll_canvas: _canvas_wheel(_c, e))
        scroll_canvas.bind_all("<Button-4>",
                               lambda e, _c=scroll_canvas: _canvas_yview(_c, -1))
        scroll_canvas.bind_all("<Button-5>",
                               lambda e, _c=scroll_canvas: _canvas_yview(_c, 1))
        self.add_scroll_canvas = scroll_canvas

        FIELDS = [
            ("First Name *", "first_name", "Enter first name"),
            ("Last Name *", "last_name", "Enter last name"),
            ("Alias", "alias", "e.g. 'The Phantom'"),
            ("CNIC / Foreign ID *", "cnic", "Enter national ID number"),
            ("Date of Birth", "dob", "Pick a date"),
            ("Gender", "gender", "Male / Female / Other"),
            ("Nationality", "nationality", "e.g. American"),
            ("Last Known Location", "location", "City, Country"),
            ("Crimes (comma-separated)", "crimes", "e.g. Robbery, Fraud"),
            ("Arrest Date", "arrest_date", "YYYY-MM-DD"),
            ("Release Date", "release_date", "YYYY-MM-DD"),
            ("Notes", "notes", "Additional notes"),
        ]

        self.entries: dict[str, StyledEntry] = {}
        self.date_pickers = {} 
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        now_year = datetime.now().year

        for i, (label, key, ph) in enumerate(FIELDS):
            row = tk.Frame(form_frame, bg=Theme.CARD)
            row.pack(fill=tk.X, padx=10, pady=3)
            lbl_text = label.replace(" *", "")
            lbl = tk.Label(row, text=lbl_text + ":", anchor="w", width=22,
                           font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT)
            lbl.pack(side=tk.LEFT)
            if key == "cnic":
                self.national_id_label_widget = lbl
            if "*" in label:
                tk.Label(row, text="*", fg=Theme.RED, font=Theme.F_SUBHEAD,
                         bg=Theme.CARD).pack(side=tk.LEFT)

            if key in ("dob", "arrest_date", "release_date"):
                picker = tk.Frame(row, bg=Theme.CARD)
                picker.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                days = [""] + [str(d) for d in range(1, 32)]
                mons = [""] + months
                yrs = [""] + [str(y) for y in range(1900, now_year + 5)]

                day_cb = ttk.Combobox(picker, width=6, state="readonly", values=days)
                mon_cb = ttk.Combobox(picker, width=11, state="readonly", values=mons)
                yr_cb = ttk.Combobox(picker, width=8, state="readonly", values=yrs)
                
                day_cb.pack(side=tk.LEFT, padx=(0, 3))
                mon_cb.pack(side=tk.LEFT, padx=(0, 3))
                yr_cb.pack(side=tk.LEFT)

                dob_out_date = tk.Label(
                    row, text="", font=Theme.F_SMALL, fg=Theme.BLUE, bg=Theme.CARD
                )
                dob_out_date.pack(side=tk.LEFT, padx=(8, 2))

                date_entry = StyledEntry(
                    row, placeholder="", font=Theme.F_BODY, bg=Theme.INPUT,
                    fg=Theme.TEXT, relief=tk.FLAT, bd=0,
                    highlightbackground=Theme.BORDER, highlightcolor=Theme.BLUE,
                    highlightthickness=1, insertbackground=Theme.TEXT
                )
                self.entries[key] = date_entry
                self.date_pickers[key] = (day_cb, mon_cb, yr_cb)

                def make_sync(d_cb, m_cb, y_cb, out_ent, lbl_out):
                    def _sync(*args):
                        d, m, y = d_cb.get(), m_cb.get(), y_cb.get()
                        if d and m and y:
                            mm = str(months.index(m) + 1).zfill(2)
                            out_ent.set_value(f"{y}-{mm}-{d.zfill(2)}")
                            lbl_out.config(text=f"→ {out_ent.get_value()}")
                        else:
                            out_ent.set_value("")
                            lbl_out.config(text="")
                    return _sync

                sync_func = make_sync(day_cb, mon_cb, yr_cb, date_entry, dob_out_date)
                for w in (day_cb, mon_cb, yr_cb):
                    w.bind("<<ComboboxSelected>>", sync_func)

            elif key in ("gender", "nationality"):
                vals = ["Male", "Female", "Other"] if key == "gender" else NATIONALITY_OPTIONS
                cb = StyledCombobox(
                    row, values=vals,
                    state="readonly" if key == "gender" else "normal",
                    font=Theme.F_BODY, width=28
                )
                cb.pack(side=tk.LEFT)
                self.entries[key] = cb
                if key == "nationality":
                    cb.bind("<<ComboboxSelected>>", self._update_add_national_id_label)
                    cb.bind("<KeyRelease>", self._update_add_national_id_label)

            else:
                entry = StyledEntry(
                    row, placeholder=ph, font=Theme.F_BODY,
                    bg=Theme.INPUT, fg=Theme.TEXT, relief=tk.FLAT,
                    bd=0, highlightbackground=Theme.BORDER,
                    highlightcolor=Theme.BLUE, highlightthickness=1,
                    insertbackground=Theme.TEXT
                )
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                self.entries[key] = entry

        self._update_add_national_id_label()

        status_row = tk.Frame(form_frame, bg=Theme.CARD)
        status_row.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(status_row, text="Status:", anchor="w", width=22,
                 font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT).pack(side=tk.LEFT)
        self.status_var = tk.StringVar(value="Wanted")
        ttk.Combobox(status_row, textvariable=self.status_var,
                     values=STATUS_OPTIONS, width=28, state="readonly",
                     font=Theme.F_BODY).pack(side=tk.LEFT)

        ttk.Separator(form_frame, orient="horizontal").pack(fill=tk.X, padx=10, pady=10)

        btn_row = tk.Frame(form_frame, bg=Theme.CARD)
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 10))
        self._btn(btn_row, "Add record", self.add_criminal, "#27ae60").pack(side=tk.LEFT, padx=(0, 8))
        self._btn(btn_row, "Clear form", self.clear_form, "#e74c3c").pack(side=tk.LEFT)

        photo_panel = tk.LabelFrame(
            main, text="PHOTO",
            font=Theme.F_SUBHEAD, fg=Theme.NAVY,
            padx=12, pady=12, bg=Theme.BG,
            highlightbackground=Theme.BORDER
        )
        photo_panel.pack(side=tk.RIGHT, fill=tk.Y, pady=4)

        self.photo_label = tk.Label(photo_panel, text="No photo selected",
                                    relief=tk.FLAT, bg=Theme.CARD,
                                    fg=Theme.TEXT_MUTED,
                                    width=22, height=14)
        self.photo_label.pack(pady=(0, 8))

        pbf = tk.Frame(photo_panel, bg=Theme.BG)
        pbf.pack()
        self._btn(pbf, "Browse", self.browse_photo, "#2980b9").pack(side=tk.LEFT, padx=3)
        self._btn(pbf, "Clear", self.clear_photo, "#e74c3c").pack(side=tk.LEFT, padx=3)

    def _setup_view_frame(self):
        frame = self.view_frame

        header = tk.Frame(frame, bg=Theme.BG)
        header.pack(fill=tk.X, pady=(0, 6))
        tk.Label(header, text="All Criminal Records",
                 font=Theme.F_HEADING, fg=Theme.TEXT, bg=Theme.BG).pack(side=tk.LEFT)

        filter_bar = tk.Frame(frame, bg=Theme.BG)
        filter_bar.pack(fill=tk.X, pady=(0, 4))
        tk.Label(
            filter_bar, text="SEARCH", font=(Theme.FONT, 8, "bold"),
            fg=Theme.TEXT_MUTED, bg=Theme.BG
        ).pack(side=tk.LEFT)
        self.filter_entry = StyledEntry(filter_bar, placeholder="Name, alias, nationality, crimes, status…",
                                   font=Theme.F_BODY,
                                   width=44, bg=Theme.INPUT, fg=Theme.TEXT,
                                   relief=tk.FLAT, bd=0,
                                   highlightbackground=Theme.BORDER,
                                   highlightcolor=Theme.BLUE,
                                   highlightthickness=1,
                                   insertbackground=Theme.TEXT)
        self.filter_entry.pack(side=tk.LEFT, padx=5)
        self.filter_entry.bind("<Return>", lambda _: self.filter_criminals())
        self._btn(filter_bar, "Filter", self.filter_criminals, "#2980b9", pad=(8, 3)).pack(side=tk.LEFT, padx=2)
        self._btn(filter_bar, "Clear", self.clear_filter, "#7f8c8d", pad=(8, 3)).pack(side=tk.LEFT, padx=2)

        self.tree = make_treeview(frame)
        self.tree.bind("<Double-1>", self.show_criminal_details)
        self.tree.bind("<Button-3>", self._show_context_menu)

        self.context_menu = tk.Menu(self.root, tearoff=0)
        self.context_menu.add_command(label="View Details", command=self.show_criminal_details)
        self.context_menu.add_command(label="Edit Record", command=self.edit_criminal)
        self.context_menu.add_command(label="Delete Record", command=self.delete_criminal)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Export Selected PDF", command=self.export_selected)

        action_bar = tk.Frame(frame, bg=Theme.BG)
        action_bar.pack(fill=tk.X, pady=(6, 0))
        self._btn(action_bar, "Refresh", self.load_criminals, "#27ae60").pack(side=tk.LEFT, padx=3)
        self._btn(action_bar, "Edit", self.edit_criminal, "#f39c12", fg="black").pack(side=tk.LEFT, padx=3)
        self.delete_btn = self._btn(action_bar, "Delete", self.delete_criminal, "#e74c3c")
        self.delete_btn.pack(side=tk.LEFT, padx=3)
        self._btn(action_bar, "Export PDF", self.export_records_pdf, "#2980b9").pack(side=tk.LEFT, padx=3)
        self._btn(action_bar, "Import PDF", self.import_records_pdf, "#8e44ad").pack(side=tk.LEFT, padx=3)
        self._btn(action_bar, "Analytics", lambda: self.notebook.select(self.stats_frame), "#8e44ad").pack(
            side=tk.LEFT, padx=3)

        self.status_bar = tk.Label(
            frame, text="", font=Theme.F_SMALL,
            fg=Theme.TEXT_MUTED, bg=Theme.BG, anchor="w"
        )
        self.status_bar.pack(fill=tk.X, pady=(3, 0))

        self.load_criminals()

    def _setup_stats_frame(self):
        frame = self.stats_frame

        tk.Label(
            frame, text="Database analytics",
            font=Theme.F_HEADING, bg=Theme.BG, fg=Theme.TEXT
        ).pack(anchor="w", pady=(0, 10))
        tk.Label(
            frame, text="Live overview of record status, caseload, demographics, and recent additions.",
            font=Theme.F_SMALL, bg=Theme.BG, fg=Theme.TEXT_MUTED
        ).pack(anchor="w", pady=(0, 10))

        body = tk.Frame(frame, bg=Theme.BG)
        body.pack(fill=tk.BOTH, expand=True)

        summary_frame = tk.LabelFrame(
            body, text="SUMMARY", font=Theme.F_SUBHEAD,
            padx=16, pady=12, bg=Theme.CARD, fg=Theme.NAVY,
            highlightbackground=Theme.BORDER
        )
        summary_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))
        summary_frame.grid_columnconfigure(1, weight=1)

        STAT_KEYS = [
            ("Total Records", "total"),
            ("Wanted", "wanted"),
            ("Arrested", "arrested"),
            ("Incarcerated", "incarcerated"),
            ("Released", "released"),
            ("Deceased", "deceased"),
            ("Average Age", "avg_age"),
            ("Unique Nationalities", "nationalities"),
            ("Records with Photos", "with_photos"),
            ("Total Cases", "cases"),
            ("Open Cases", "open_cases"),
            ("Database Size", "db_size"),
        ]
        self._stat_labels: dict[str, tk.Label] = {}
        for i, (label, key) in enumerate(STAT_KEYS):
            tk.Label(
                summary_frame, text=label + ":", font=Theme.F_BODY,
                anchor="w", bg=Theme.CARD, fg=Theme.TEXT_MUTED
            ).grid(row=i, column=0, sticky=tk.W, pady=5, padx=(0, 12))
            lbl = tk.Label(
                summary_frame, text="—", font=Theme.F_SUBHEAD,
                anchor="w", bg=Theme.CARD, fg=Theme.TEXT
            )
            lbl.grid(row=i, column=1, sticky=tk.W)
            self._stat_labels[key] = lbl

        right = tk.Frame(body, bg=Theme.BG)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        chart_frame = tk.LabelFrame(
            right, text="RECORD STATUS",
            font=Theme.F_SUBHEAD, padx=10, pady=8,
            bg=Theme.CARD, fg=Theme.NAVY, highlightbackground=Theme.BORDER
        )
        chart_frame.pack(fill=tk.X)
        self.status_canvas = tk.Canvas(
            chart_frame, height=238, bg=Theme.CARD,
            highlightthickness=1, highlightbackground=Theme.BORDER
        )
        self.status_canvas.pack(fill=tk.X)
        self.status_canvas.bind("<Configure>", lambda _event: self._redraw_status_chart())

        trend_frame = tk.LabelFrame(
            right, text="RECORDS ADDED — LAST 6 MONTHS",
            font=Theme.F_SUBHEAD, padx=10, pady=8,
            bg=Theme.CARD, fg=Theme.NAVY, highlightbackground=Theme.BORDER
        )
        trend_frame.pack(fill=tk.X, pady=(8, 0))
        self.trend_canvas = tk.Canvas(
            trend_frame, height=150, bg=Theme.CARD,
            highlightthickness=1, highlightbackground=Theme.BORDER
        )
        self.trend_canvas.pack(fill=tk.X)
        self.trend_canvas.bind("<Configure>", lambda _event: self._redraw_monthly_chart())

        nat_frame = tk.LabelFrame(
            right, text="TOP NATIONALITIES",
            font=Theme.F_SUBHEAD, padx=10, pady=10,
            bg=Theme.CARD, fg=Theme.NAVY, highlightbackground=Theme.BORDER
        )
        nat_frame.pack(fill=tk.BOTH, expand=True, pady=(8, 0))
        self.nationality_list = tk.Listbox(
            nat_frame, font=Theme.F_BODY, height=8, bd=0, relief=tk.FLAT,
            bg=Theme.CARD_ALT, fg=Theme.TEXT,
            selectbackground=Theme.BLUE, selectforeground=Theme.WHITE
        )
        self.nationality_list.pack(fill=tk.BOTH, expand=True)
        self._statistics_cache = {}

        btn_row = tk.Frame(frame, bg=Theme.BG)
        btn_row.pack(pady=10)
        self._btn(btn_row, "Refresh statistics", self.update_statistics, "#2980b9").pack(side=tk.LEFT, padx=4)
        self._btn(btn_row, "Export statistics", self.export_statistics, "#27ae60").pack(side=tk.LEFT, padx=4)

        self.update_statistics()

    def update_statistics(self):
        conn = get_db_connection()
        if not conn:
            return
        try:
            stats = self._collect_statistics(conn)
        finally:
            conn.close()
        self._statistics_cache = stats
        for key, value in stats["summary"].items():
            if key in self._stat_labels:
                self._stat_labels[key].config(text=value)
        self._draw_status_chart(stats["status_counts"])
        self._draw_monthly_chart(stats["monthly_counts"])
        self.nationality_list.delete(0, tk.END)
        if stats["top_nationalities"]:
            for nat, count in stats["top_nationalities"]:
                self.nationality_list.insert(tk.END, f"  {nat}: {count}")
        else:
            self.nationality_list.insert(tk.END, "  No nationality data available")
        self.update_status_counts()
        self.refresh_dashboard()

    def _collect_statistics(self, conn):
        today = datetime.now().date()
        records = conn.execute(
            "SELECT status,date_of_birth,nationality,photo_path,photo_data,created_at "
            "FROM criminals"
        ).fetchall()
        total = len(records)
        status_counts = {status: 0 for status in STATUS_OPTIONS}
        status_counts["Other / unspecified"] = 0
        ages = []
        nationalities = {}
        photo_count = 0
        month_keys = []
        year, month = today.year, today.month
        for _ in range(5, -1, -1):
            month_keys.append(f"{year:04d}-{month:02d}")
            month -= 1
            if month == 0:
                year -= 1
                month = 12
        monthly_counts = {key: 0 for key in month_keys}

        for status, dob, nationality, photo_path, photo_data, created_at in records:
            status_key = status if status in STATUS_OPTIONS else "Other / unspecified"
            status_counts[status_key] += 1
            if dob:
                try:
                    birth_date = datetime.strptime(dob, "%Y-%m-%d").date()
                    if birth_date <= today:
                        age = today.year - birth_date.year - (
                            (today.month, today.day) < (birth_date.month, birth_date.day)
                        )
                        ages.append(age)
                except (TypeError, ValueError):
                    pass
            if nationality and nationality.strip():
                normalized = nationality.strip()
                nationalities[normalized] = nationalities.get(normalized, 0) + 1
            if (photo_path and photo_path.strip()) or photo_data:
                photo_count += 1
            if created_at:
                month_key = str(created_at)[:7]
                if month_key in monthly_counts:
                    monthly_counts[month_key] += 1

        cases = conn.execute("SELECT COUNT(*) FROM cases").fetchone()[0]
        open_cases = conn.execute(
            "SELECT COUNT(*) FROM cases WHERE lower(trim(coalesce(status,'')))='open'"
        ).fetchone()[0]
        db_size = 0
        for suffix in ("", "-wal", "-shm"):
            try:
                db_size += os.path.getsize(DATABASE_NAME + suffix)
            except OSError:
                continue
        summary = {
            "total": str(total),
            "wanted": str(status_counts["Wanted"]),
            "arrested": str(status_counts["Arrested"]),
            "incarcerated": str(status_counts["Incarcerated"]),
            "released": str(status_counts["Released"]),
            "deceased": str(status_counts["Deceased"]),
            "avg_age": f"{sum(ages) / len(ages):.1f} yrs" if ages else "N/A",
            "nationalities": str(len(nationalities)),
            "with_photos": (
                f"{photo_count} ({photo_count / total * 100:.0f}%)" if total else "0 (0%)"
            ),
            "cases": str(cases),
            "open_cases": str(open_cases),
            "db_size": f"{db_size / (1024 * 1024):.2f} MB",
        }
        return {
            "summary": summary,
            "total": total,
            "status_counts": status_counts,
            "monthly_counts": monthly_counts,
            "top_nationalities": sorted(
                nationalities.items(), key=lambda item: (-item[1], item[0].casefold())
            )[:10],
        }

    def _draw_status_chart(self, status_counts: dict):
        self._status_counts = status_counts
        self._redraw_status_chart()

    def _redraw_status_chart(self):
        c = self.status_canvas
        c.delete("all")
        width = max(c.winfo_width(), 360)
        label_width, count_width = 120, 52
        bar_left, bar_right = label_width + 8, width - count_width - 10
        bar_width = max(10, bar_right - bar_left)
        row_height = 34
        max_count = max(self._status_counts.values(), default=0) or 1
        for index, status in enumerate(STATUS_OPTIONS + ["Other / unspecified"]):
            count = self._status_counts.get(status, 0)
            y = 20 + index * row_height
            _, color = STATUS_COLORS.get(status, (Theme.CARD_ALT, Theme.BLUE))
            c.create_text(
                label_width, y + 8, text=status, anchor="e",
                font=Theme.F_SMALL, fill=Theme.TEXT_MUTED
            )
            c.create_rectangle(
                bar_left, y, bar_right, y + 16,
                fill=Theme.CARD_ALT, outline=Theme.BORDER
            )
            if count:
                c.create_rectangle(
                    bar_left, y, bar_left + bar_width * count / max_count, y + 16,
                    fill=color, outline=color
                )
            percentage = count / sum(self._status_counts.values()) * 100 if sum(self._status_counts.values()) else 0
            c.create_text(
                width - 6, y + 8, text=f"{count}  ({percentage:.0f}%)",
                anchor="e", font=Theme.F_SMALL, fill=Theme.TEXT
            )

    def _draw_monthly_chart(self, monthly_counts: dict):
        self._monthly_counts = monthly_counts
        self._redraw_monthly_chart()

    def _redraw_monthly_chart(self):
        if not hasattr(self, "trend_canvas"):
            return
        c = self.trend_canvas
        c.delete("all")
        width = max(c.winfo_width(), 360)
        height = 150
        left, right, top, bottom = 34, width - 18, 16, height - 30
        values = list(self._monthly_counts.values())
        max_count = max(values, default=0) or 1
        points = []
        count_span = max(1, len(values) - 1)
        for index, (month_key, count) in enumerate(self._monthly_counts.items()):
            x = left + (right - left) * index / count_span
            y = bottom - (bottom - top) * count / max_count
            points.append((x, y))
            c.create_text(
                x, height - 12, text=month_key[5:],
                font=Theme.F_SMALL, fill=Theme.TEXT_MUTED
            )
            c.create_text(
                x, y - 10, text=str(count),
                font=Theme.F_SMALL, fill=Theme.TEXT
            )
        for tick in range(3):
            y = bottom - (bottom - top) * tick / 2
            c.create_line(left, y, right, y, fill=Theme.BORDER_SOFT)
        if len(points) > 1:
            coords = [coordinate for point in points for coordinate in point]
            c.create_line(*coords, fill=Theme.BLUE, width=2, smooth=True)
        for x, y in points:
            c.create_oval(x - 3, y - 3, x + 3, y + 3, fill=Theme.BLUE, outline=Theme.WHITE)
        if not sum(values):
            c.create_text(
                width / 2, height / 2, text="No records added in this period",
                font=Theme.F_SMALL, fill=Theme.TEXT_MUTED
            )

    def export_statistics(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv",
                                            filetypes=[("CSV files", "*.csv")],
                                            title="Save Statistics")
        if not path:
            return
        conn = get_db_connection()
        if not conn:
            return
        try:
            stats = self._collect_statistics(conn)
        finally:
            conn.close()

        with secure_output_path(path) as output_path:
            with open(output_path, "w", newline="", encoding="utf-8-sig") as f:
                w = csv.writer(f)
                w.writerow(["Criminal Database Analytics"])
                w.writerow(["Generated", datetime.now().strftime("%Y-%m-%d %H:%M:%S")])
                w.writerow([])
                w.writerow(spreadsheet_safe_row(["Metric", "Value"]))
                for key, value in stats["summary"].items():
                    w.writerow(spreadsheet_safe_row([key.replace("_", " ").title(), value]))
                w.writerow([])
                w.writerow(spreadsheet_safe_row(["Status", "Count", "Percent"]))
                for status in STATUS_OPTIONS + ["Other / unspecified"]:
                    count = stats["status_counts"][status]
                    percent = count / stats["total"] * 100 if stats["total"] else 0
                    w.writerow(spreadsheet_safe_row([status, count, f"{percent:.1f}%"]))
                w.writerow([])
                w.writerow(spreadsheet_safe_row(["Top Nationalities", "Count"]))
                for nationality, count in stats["top_nationalities"]:
                    w.writerow(spreadsheet_safe_row([nationality, count]))
                w.writerow([])
                w.writerow(spreadsheet_safe_row(["Month", "Records Added"]))
                for month, count in stats["monthly_counts"].items():
                    w.writerow([month, count])
        messagebox.showinfo("Exported", f"Statistics saved to:\n{path}")

    def browse_photo(self):
        path = filedialog.askopenfilename(
            title="Select Photo",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp")])
        if path:
            self.photo_path = path
            load_photo_for_label(self.photo_label, path, None, 180, 220)

    def clear_photo(self):
        self.photo_path = ""
        self.photo_image = None
        self.photo_label.config(image="", text="No photo selected")
        self.photo_label.image = None

    def add_criminal(self):
        data = {k: e.get_value() for k, e in self.entries.items()}
        data["status"] = self.status_var.get()
        if is_pakistani_nationality(data["nationality"]):
            data["cnic"] = normalize_cnic(data["cnic"])
        else:
            data["cnic"] = data["cnic"].strip()

        if not data["first_name"] or not data["last_name"]:
            messagebox.showerror("Validation Error", "First and Last Name are required.")
            return
        id_error = national_id_validation_error(data["nationality"], data["cnic"])
        if id_error:
            messagebox.showerror("Nationality / ID Validation", id_error)
            return

        for date_key in ("dob", "arrest_date", "release_date"):
            if not validate_date(data[date_key]):
                messagebox.showerror("Validation Error", f"Invalid date in '{date_key}'. Use YYYY-MM-DD.")
                return

        photo_path = ""
        if self.photo_path and os.path.exists(self.photo_path):
            try:
                photo_path = copy_photo_to_media(self.photo_path, data["first_name"], data["last_name"])
            except (OSError, ValueError) as exc:
                messagebox.showerror("Photo Error", str(exc))
                return

        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO criminals (
                first_name, last_name, alias, cnic, date_of_birth, gender,
                nationality, last_known_location, crimes, status,
                arrest_date, release_date, notes, photo_path,
                created_at, updated_at
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP)
        """, (data["first_name"], data["last_name"], data["alias"] or None, data["cnic"] or None, data["dob"] or None,
              data["gender"] or None, data["nationality"] or None, data["location"] or None,
              data["crimes"] or None, data["status"], data["arrest_date"] or None,
              data["release_date"] or None, data["notes"] or None, photo_path or None))
        new_id = cur.lastrowid
        conn.commit()
        self._log_audit(conn, "INSERT", "criminals", new_id)
        conn.commit()
        conn.close()

        messagebox.showinfo("Success", "Criminal record added successfully.")
        self.clear_form()
        self.load_criminals()

    def clear_form(self):
        for entry in self.entries.values():
            entry.set_value("")
        if hasattr(self, "date_pickers"):
            for pickers in self.date_pickers.values():
                for cb in pickers:
                    cb.set("")
        self.status_var.set("Wanted")
        self.clear_photo()
        self._update_add_national_id_label()

    def _update_add_national_id_label(self, _event=None):
        if hasattr(self, "national_id_label_widget"):
            self.national_id_label_widget.config(
                text=national_id_label(self.entries["nationality"].get_value()) + ":"
            )

    def clear_filter(self):
        self.filter_entry.set_value("")
        self.load_criminals()

    def load_criminals(self):
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT * FROM criminals ORDER BY last_name, first_name")
        criminals = cur.fetchall()
        conn.close()
        populate_tree(self.tree, criminals)
        self.update_status_counts()
        self.refresh_dashboard()

    def filter_criminals(self):
        term = self.filter_entry.get_value().strip().lower()
        if not term:
            self.load_criminals()
            return
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT * FROM criminals ORDER BY last_name, first_name")
        all_rows = cur.fetchall()
        conn.close()
        filtered = [
            r for r in all_rows
            if term in f"{safe_str(r[1])} {safe_str(r[2])}".lower()
               or term in safe_str(r[3]).lower()
               or term in safe_str(r[6]).lower()
               or term in safe_str(r[8]).lower()
               or term in safe_str(r[9]).lower()
        ]
        populate_tree(self.tree, filtered)
        self.status_bar.config(text=f"Showing {len(filtered)} of {len(all_rows)} records")

    def update_status_counts(self):
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM criminals")
        total = cur.fetchone()[0]
        conn.close()
        self.root.title(f"{APP_NAME} — {total} records")
        if hasattr(self, "status_bar"):
            self.status_bar.config(text=f"{total} total records")

    def delete_criminal(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("No Selection", "Select a record to delete.")
            return
        if not messagebox.askyesno("Confirm Delete", "Permanently delete this record?"):
            return
        cid = self.tree.item(sel[0])["values"][0]
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("DELETE FROM criminals WHERE id=?", (cid,))
        conn.commit()
        if cur.rowcount:
            self._log_audit(conn, "DELETE", "criminals", cid)
            conn.commit()
        conn.close()
        self.load_criminals()

    def edit_criminal(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("No Selection", "Select a record to edit.")
            return
        cid = self.tree.item(sel[0])["values"][0]
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT * FROM criminals WHERE id=?", (cid,))
        c = cur.fetchone()
        conn.close()
        if not c:
            return
        self._open_edit_window(c)

    def _open_edit_window(self, c: tuple):
        win = tk.Toplevel(self.root)
        win.title(f"Edit — {c[1]} {c[2]}")
        win.geometry("1020x640")
        win.minsize(860, 540)
        win.grab_set()

        main = tk.Frame(win, bg=Theme.BG)
        main.pack(fill=tk.BOTH, expand=True, padx=12, pady=10)

        photo_panel = tk.LabelFrame(
            main, text="PHOTO", font=Theme.F_SUBHEAD,
            fg=Theme.NAVY, padx=12, pady=12, width=240,
            bg=Theme.BG, highlightbackground=Theme.BORDER
        )
        photo_panel.pack(side=tk.RIGHT, fill=tk.Y, padx=(8, 0))
        photo_panel.pack_propagate(False)

        ep_label = tk.Label(
            photo_panel, text="No photo", relief=tk.FLAT,
            bg=Theme.CARD, fg=Theme.TEXT_MUTED, width=22, height=14
        )
        ep_label.pack(fill=tk.BOTH, expand=True, pady=(0, 6))
        load_photo_for_label(ep_label, c[13], c[14])

        edit_photo_path = [c[13] or ""]

        def browse_edit_photo():
            path = filedialog.askopenfilename(
                title="Select Photo",
                filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.gif *.webp")])
            if path:
                edit_photo_path[0] = path
                load_photo_for_label(ep_label, path, None)
                e_entries["photo_path"].set_value(path)

        def clear_edit_photo():
            edit_photo_path[0] = ""
            ep_label.config(image="", text="No photo")
            ep_label.image = None
            e_entries["photo_path"].set_value("")

        pbf = tk.Frame(photo_panel, bg=Theme.BG)
        pbf.pack()
        self._btn(pbf, "Browse", browse_edit_photo, "#2980b9").pack(side=tk.LEFT, padx=3)
        self._btn(pbf, "Clear", clear_edit_photo, "#e74c3c").pack(side=tk.LEFT, padx=3)

        form_outer = tk.Frame(
            main, bd=0, relief=tk.FLAT, bg=Theme.CARD,
            highlightthickness=1, highlightbackground=Theme.BORDER
        )
        form_outer.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        tk.Label(form_outer, text="Edit Criminal Record",
                 font=Theme.F_HEADING, fg=Theme.TEXT, bg=Theme.CARD
                 ).pack(anchor="w", padx=12, pady=(10, 4))
        ttk.Separator(form_outer, orient="horizontal").pack(fill=tk.X, padx=12)

        scroll_c = tk.Canvas(form_outer, bg=Theme.CARD, highlightthickness=0)
        scroll_c.pack(fill=tk.BOTH, expand=True, padx=6)
        form_frame = tk.Frame(scroll_c, bg=Theme.CARD)
        edit_scroll_window = scroll_c.create_window((0, 0), window=form_frame, anchor="nw")
        form_frame.bind("<Configure>",
                        lambda e: scroll_c.configure(scrollregion=scroll_c.bbox("all")))
        scroll_c.bind("<Configure>",
                      lambda e: scroll_c.itemconfigure(edit_scroll_window, width=e.width))
        vsb = ttk.Scrollbar(form_outer, orient="vertical", command=scroll_c.yview)
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        scroll_c.configure(yscrollcommand=vsb.set)
        scroll_c.bind_all("<MouseWheel>",
                          lambda e, _c=scroll_c: _canvas_wheel(_c, e))
        scroll_c.bind_all("<Button-4>",
                          lambda e, _c=scroll_c: _canvas_yview(_c, -1))
        scroll_c.bind_all("<Button-5>",
                          lambda e, _c=scroll_c: _canvas_yview(_c, 1))

        def _on_edit_close():
            try:
                win.unbind_all("<MouseWheel>")
                win.unbind_all("<Button-4>")
                win.unbind_all("<Button-5>")
            except Exception:
                pass
            _rebind_default_scroll(self)
            win.destroy()
        win.protocol("WM_DELETE_WINDOW", _on_edit_close)

        EDIT_FIELDS = [
            ("First Name *", "first_name", safe_str(c[1])),
            ("Last Name *", "last_name", safe_str(c[2])),
            ("Alias", "alias", safe_str(c[3])),
            ("CNIC / Foreign ID *", "cnic", safe_str(c[18])),
            ("Date of Birth", "dob", safe_str(c[4])),
            ("Gender", "gender", safe_str(c[5])),
            ("Nationality", "nationality", safe_str(c[6])),
            ("Last Known Location", "location", safe_str(c[7])),
            ("Crimes (comma-separated)", "crimes", safe_str(c[8])),
            ("Arrest Date", "arrest_date", safe_str(c[10])),
            ("Release Date", "release_date", safe_str(c[11])),
            ("Notes", "notes", safe_str(c[12])),
            ("Photo Path", "photo_path", safe_str(c[13])),
        ]

        e_entries: dict[str, StyledEntry] = {}
        edit_national_id_label = None
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        now_year = datetime.now().year

        for label, key, val in EDIT_FIELDS:
            row = tk.Frame(form_frame, bg=Theme.CARD)
            row.pack(fill=tk.X, padx=10, pady=3)
            field_label = tk.Label(
                row, text=label.replace(" *", "") + ":", anchor="w", width=22,
                font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT
            )
            field_label.pack(side=tk.LEFT)
            if key == "cnic":
                edit_national_id_label = field_label
            if "*" in label:
                tk.Label(
                    row, text="*", fg=Theme.RED, font=Theme.F_SUBHEAD,
                    bg=Theme.CARD
                ).pack(side=tk.LEFT)

            if key in ("dob", "arrest_date", "release_date"):
                picker = tk.Frame(row, bg=Theme.CARD)
                picker.pack(side=tk.LEFT, fill=tk.X, expand=True)
                
                days = [""] + [str(d) for d in range(1, 32)]
                mons = [""] + months
                yrs = [""] + [str(y) for y in range(1900, now_year + 5)]

                day_cb = ttk.Combobox(picker, width=6, state="readonly", values=days)
                mon_cb = ttk.Combobox(picker, width=11, state="readonly", values=mons)
                yr_cb = ttk.Combobox(picker, width=8, state="readonly", values=yrs)
                
                day_cb.pack(side=tk.LEFT, padx=(0, 3))
                mon_cb.pack(side=tk.LEFT, padx=(0, 3))
                yr_cb.pack(side=tk.LEFT)

                dob_out_date = tk.Label(
                    row, text="", font=Theme.F_SMALL, fg=Theme.BLUE, bg=Theme.CARD
                )
                dob_out_date.pack(side=tk.LEFT, padx=(8, 2))

                date_entry = StyledEntry(
                    row, font=Theme.F_BODY, bg=Theme.INPUT, fg=Theme.TEXT,
                    relief=tk.FLAT, bd=0, highlightbackground=Theme.BORDER,
                    highlightcolor=Theme.BLUE, highlightthickness=1,
                    insertbackground=Theme.TEXT
                )
                e_entries[key] = date_entry

                if val:
                    try:
                        d_obj = datetime.strptime(val, "%Y-%m-%d")
                        yr_cb.set(str(d_obj.year))
                        mon_cb.set(months[d_obj.month - 1])
                        day_cb.set(str(d_obj.day))
                        date_entry.set_value(val)
                        dob_out_date.config(text=f"→ {val}")
                    except ValueError:
                        pass

                def make_sync(d_cb, m_cb, y_cb, out_ent, lbl_out):
                    def _sync(*args):
                        d, m, y = d_cb.get(), m_cb.get(), y_cb.get()
                        if d and m and y:
                            mm = str(months.index(m) + 1).zfill(2)
                            out_ent.set_value(f"{y}-{mm}-{d.zfill(2)}")
                            lbl_out.config(text=f"→ {out_ent.get_value()}")
                        else:
                            out_ent.set_value("")
                            lbl_out.config(text="")
                    return _sync

                sync_func = make_sync(day_cb, mon_cb, yr_cb, date_entry, dob_out_date)
                for w in (day_cb, mon_cb, yr_cb):
                    w.bind("<<ComboboxSelected>>", sync_func)

            elif key in ("gender", "nationality"):
                vals = ["Male", "Female", "Other"] if key == "gender" else NATIONALITY_OPTIONS
                cb = StyledCombobox(
                    row, values=vals,
                    state="readonly" if key == "gender" else "normal",
                    font=Theme.F_BODY, width=28
                )
                cb.pack(side=tk.LEFT)
                cb.set_value(val)
                e_entries[key] = cb
                if key == "nationality":
                    cb.bind(
                        "<<ComboboxSelected>>",
                        lambda _event: edit_national_id_label.config(
                            text=national_id_label(e_entries["nationality"].get_value()) + ":"
                        ),
                    )
                    cb.bind(
                        "<KeyRelease>",
                        lambda _event: edit_national_id_label.config(
                            text=national_id_label(e_entries["nationality"].get_value()) + ":"
                        ),
                    )
            else:
                entry = StyledEntry(
                    row, font=Theme.F_BODY, bg=Theme.INPUT, fg=Theme.TEXT,
                    relief=tk.FLAT, bd=0, highlightbackground=Theme.BORDER,
                    highlightcolor=Theme.BLUE, highlightthickness=1,
                    insertbackground=Theme.TEXT
                )
                entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
                entry.set_value(val)
                e_entries[key] = entry

        edit_national_id_label.config(text=national_id_label(e_entries["nationality"].get_value()) + ":")

        st_row = tk.Frame(form_frame, bg=Theme.CARD)
        st_row.pack(fill=tk.X, padx=10, pady=3)
        tk.Label(st_row, text="Status:", anchor="w", width=22,
                 font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT).pack(side=tk.LEFT)
        edit_status_var = tk.StringVar(value=safe_str(c[9]))
        ttk.Combobox(st_row, textvariable=edit_status_var, values=STATUS_OPTIONS,
                     width=28, state="readonly", font=Theme.F_BODY).pack(side=tk.LEFT)

        ttk.Separator(form_frame, orient="horizontal").pack(fill=tk.X, padx=10, pady=10)

        def save_changes():
            updated = {k: e.get_value() for k, e in e_entries.items()}
            updated["status"] = edit_status_var.get()

            if not updated["first_name"] or not updated["last_name"]:
                messagebox.showerror("Validation Error", "First and Last Name are required.")
                return
            if is_pakistani_nationality(updated["nationality"]):
                updated["cnic"] = normalize_cnic(updated["cnic"])
            else:
                updated["cnic"] = updated["cnic"].strip()
            id_error = national_id_validation_error(updated["nationality"], updated["cnic"])
            if id_error:
                messagebox.showerror("Nationality / ID Validation", id_error)
                return
            for dk in ("dob", "arrest_date", "release_date"):
                if not validate_date(updated[dk]):
                    messagebox.showerror("Validation Error", f"Invalid date in '{dk}'. Use YYYY-MM-DD.")
                    return

            photo_path = edit_photo_path[0]
            if photo_path and os.path.exists(photo_path) and photo_path != (c[13] or ""):
                try:
                    photo_path = copy_photo_to_media(photo_path, updated["first_name"], updated["last_name"])
                except (OSError, ValueError) as exc:
                    messagebox.showerror("Photo Error", str(exc))
                    return

            db_conn = get_db_connection()
            if not db_conn:
                return
            db_cur = db_conn.cursor()
            db_cur.execute("""
                UPDATE criminals SET
                    first_name=?, last_name=?, alias=?, cnic=?, date_of_birth=?, gender=?,
                    nationality=?, last_known_location=?, crimes=?, status=?,
                    arrest_date=?, release_date=?, notes=?, photo_path=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (updated["first_name"], updated["last_name"], updated["alias"] or None,
                updated["cnic"] or None,
                  updated["dob"] or None, updated["gender"] or None, updated["nationality"] or None,
                  updated["location"] or None, updated["crimes"] or None, updated["status"],
                  updated["arrest_date"] or None, updated["release_date"] or None,
                  updated["notes"] or None, photo_path or None, c[0]))
            db_conn.commit()
            self._log_audit(db_conn, "UPDATE", "criminals", c[0])
            db_conn.commit()
            db_conn.close()

            messagebox.showinfo("Saved", "Record updated successfully.")
            win.destroy()
            self.load_criminals()

        btn_row = tk.Frame(form_frame, bg=Theme.CARD)
        btn_row.pack(fill=tk.X, padx=10, pady=(0, 10))
        self._btn(btn_row, "Save changes", save_changes, "#27ae60").pack(side=tk.LEFT, padx=(0, 8))
        self._btn(btn_row, "Cancel", win.destroy, "#7f8c8d").pack(side=tk.LEFT)

    def show_criminal_details(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        cid = self.tree.item(sel[0])["values"][0]
        self._open_details_window(cid)

    def _open_details_window(self, criminal_id):
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("SELECT * FROM criminals WHERE id=?", (criminal_id,))
        c = cur.fetchone()
        conn.close()
        if not c:
            return

        win = tk.Toplevel(self.root)
        win.title(f"Details — {c[1]} {c[2]}")
        win.geometry("980x660")
        win.minsize(860, 560)

        header = tk.Frame(win, bg=Theme.NAVY, padx=18, pady=12)
        header.pack(fill=tk.X)
        tk.Label(header, text=f"👤  {c[1]} {c[2]}",
                 font=Theme.F_HEADING, fg=Theme.WHITE, bg=Theme.NAVY).pack(side=tk.LEFT)
        sc, tc = STATUS_COLORS.get(safe_str(c[9]), (Theme.CARD_ALT, Theme.TEXT_MUTED))
        tk.Label(header, text=f"  {c[9]}  ", font=Theme.F_SUBHEAD,
                 bg=sc, fg=tc, padx=8, pady=4).pack(side=tk.RIGHT)

        body = tk.Frame(win, padx=14, pady=10, bg=Theme.BG)
        body.pack(fill=tk.BOTH, expand=True)

        right = tk.Frame(body, width=270, bg=Theme.BG)
        right.pack(side=tk.RIGHT, fill=tk.Y, padx=(10, 0))
        right.pack_propagate(False)

        pf = tk.LabelFrame(
            right, text="PHOTO", font=Theme.F_SUBHEAD,
            padx=8, pady=8, bg=Theme.CARD, fg=Theme.NAVY,
            highlightbackground=Theme.BORDER
        )
        pf.pack(fill=tk.X)
        plabel = tk.Label(
            pf, text="No photo available", bg=Theme.CARD_ALT,
            fg=Theme.TEXT_MUTED, relief=tk.FLAT
        )
        plabel.pack(fill=tk.BOTH, expand=True, ipady=4)
        load_photo_for_label(plabel, c[13], c[14], 240, 260)

        qf = tk.LabelFrame(
            right, text="QUICK INFO", font=Theme.F_SUBHEAD,
            padx=10, pady=8, bg=Theme.CARD, fg=Theme.NAVY,
            highlightbackground=Theme.BORDER
        )
        qf.pack(fill=tk.X, pady=(8, 0))
        for lbl, val in [("ID:", c[0]), ("Gender:", c[5]), ("Nationality:", c[6]),
                         ("DOB:", c[4] or "Unknown"), ("Alias:", c[3] or "None")]:
            tk.Label(
                qf, text=f"{lbl}  {val}", anchor="w",
                font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT
            ).pack(fill=tk.X, pady=2)

        left = tk.Frame(body, bg=Theme.BG)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        det_canvas = tk.Canvas(left, bg=Theme.BG, highlightthickness=0)
        det_vsb = ttk.Scrollbar(left, orient="vertical", command=det_canvas.yview)
        det_canvas.configure(yscrollcommand=det_vsb.set)
        det_vsb.pack(side=tk.RIGHT, fill=tk.Y)
        det_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        sf = tk.Frame(det_canvas, bg=Theme.BG)
        sf.bind("<Configure>",
                lambda e: det_canvas.configure(scrollregion=det_canvas.bbox("all")))
        det_canvas.create_window((0, 0), window=sf, anchor="nw")

        sections = [
            ("👤 Personal Information", [
                ("Full Name", f"{c[1]} {c[2]}"),
                ("Alias", c[3] or "—"),
                (national_id_label(c[6]), safe_str(c[18]) or "—"),
                ("Date of Birth", c[4] or "—"),
                ("Gender", c[5] or "—"),
                ("Nationality", c[6] or "—"),
            ]),
            ("📋 Case Information", [
                ("Status", c[9] or "—"),
                ("Crimes", c[8] or "—"),
                ("Last Known Location", c[7] or "—"),
                ("Arrest Date", c[10] or "—"),
                ("Release Date", c[11] or "—"),
            ]),
            ("📝 Notes & Metadata", [
                ("Notes", c[12] or "—"),
                ("Created At", c[16] or "—"),
                ("Updated At", c[17] or "—"),
            ]),
        ]

        row_idx = 0
        for sec_title, items in sections:
            tk.Label(
                sf, text=sec_title, font=Theme.F_SUBHEAD,
                fg=Theme.BLUE, bg=Theme.BG
            ).grid(row=row_idx, column=0, columnspan=2,
                                        sticky=tk.W, padx=8, pady=(12, 4))
            row_idx += 1
            for lbl, val in items:
                tk.Label(
                    sf, text=lbl + ":", font=Theme.F_SUBHEAD,
                    anchor="w", width=18, bg=Theme.BG, fg=Theme.TEXT
                ).grid(row=row_idx, column=0, sticky=tk.W, padx=(8, 0), pady=2)
                if lbl == "Crimes":
                    crime_bg, crime_fg = Theme.STATUS["Wanted"]
                    vf = tk.Frame(sf, bg=crime_bg, padx=6, pady=3)
                    vf.grid(row=row_idx, column=1, sticky=tk.W, padx=8, pady=2)
                    tk.Label(vf, text=val, wraplength=480, justify=tk.LEFT,
                             font=Theme.F_BODY, fg=crime_fg, bg=crime_bg).pack()
                else:
                    tk.Label(sf, text=val, wraplength=480, justify=tk.LEFT,
                             font=Theme.F_BODY, bg=Theme.BG, fg=Theme.TEXT).grid(row=row_idx, column=1,
                                                        sticky=tk.W, padx=8, pady=2)
                row_idx += 1
            ttk.Separator(sf, orient="horizontal").grid(row=row_idx, column=0,
                                                        columnspan=2, sticky="ew", padx=8, pady=4)
            row_idx += 1

        foot = tk.Frame(win, padx=14, pady=8, bg=Theme.BG)
        foot.pack(fill=tk.X)
        self._btn(foot, "Close", win.destroy, "#7f8c8d").pack(side=tk.LEFT, padx=(0, 6))
        self._btn(foot, "Edit record", lambda: [win.destroy(), self.edit_criminal()], "#2980b9").pack(side=tk.LEFT,
                                                                                                         padx=(0, 6))
        self._btn(
            foot, "Export PDF", lambda: self._export_record_by_id(criminal_id), "#27ae60"
        ).pack(side=tk.LEFT)

    def export_records_pdf(self):
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Export All Records",
            initialfile="criminal_records.pdf",
        )
        if not path:
            return
        conn = get_db_connection()
        if not conn:
            return
        try:
            rows = conn.execute(
                """SELECT id,first_name,last_name,alias,cnic,date_of_birth,gender,
                          nationality,last_known_location,crimes,status,arrest_date,
                          release_date,notes,case_number,created_at,updated_at,
                          photo_path,photo_data
                   FROM criminals ORDER BY last_name,first_name"""
            ).fetchall()
        except sqlite3.Error as exc:
            messagebox.showerror("Export", f"Could not read criminal records:\n{exc}")
            return
        finally:
            conn.close()
        if not rows:
            messagebox.showinfo("Export", "There are no records to export.")
            return
        try:
            records = [self._record_for_pdf(row) for row in rows]
            self._build_records_pdf(path, records)
            messagebox.showinfo("Exported", f"{len(records)} records saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export", str(exc))

    def export_selected(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("No Selection", "Select a record to export.")
            return
        cid = self.tree.item(sel[0])["values"][0]
        self._export_record_by_id(cid)

    def _export_record_by_id(self, cid):
        conn = get_db_connection()
        if not conn:
            return
        try:
            row = conn.execute(
                """SELECT id,first_name,last_name,alias,cnic,date_of_birth,gender,
                          nationality,last_known_location,crimes,status,arrest_date,
                          release_date,notes,case_number,created_at,updated_at,
                          photo_path,photo_data
                   FROM criminals WHERE id=?""",
                (cid,),
            ).fetchone()
        except sqlite3.Error as exc:
            messagebox.showerror("Export", f"Could not read the selected record:\n{exc}")
            return
        finally:
            conn.close()
        if not row:
            messagebox.showerror("Export", "The selected record could not be found.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            title="Export Record",
            initialfile=f"criminal_{cid}.pdf",
        )
        if not path:
            return
        try:
            self._build_records_pdf(path, [self._record_for_pdf(row)])
            messagebox.showinfo("Exported", f"Record saved to:\n{path}")
        except Exception as exc:
            messagebox.showerror("Export", str(exc))

    @staticmethod
    def _record_for_pdf(row):
        record = dict(zip(RECORD_EXPORT_FIELDS, row[:len(RECORD_EXPORT_FIELDS)]))
        photo_path, photo_data = row[-2:]
        photo_bytes = bytes(photo_data) if photo_data else None
        if photo_path and os.path.isfile(photo_path):
            try:
                with open(photo_path, "rb") as photo_file:
                    photo_bytes = decrypt_photo_data(photo_file.read())
            except Exception:
                # Skip an unreadable photo rather than failing the whole export.
                pass
        record["photo"] = base64.b64encode(photo_bytes).decode("ascii") if photo_bytes else None
        return record

    def _build_records_pdf(self, path, records):
        if pdf_colors is None:
            raise RuntimeError("ReportLab is not installed. Run pip install -r requirements.txt")
        pdf_buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            pdf_buffer, pagesize=A4, rightMargin=15 * mm, leftMargin=15 * mm,
            topMargin=15 * mm, bottomMargin=15 * mm,
        )
        styles = getSampleStyleSheet()
        story = []
        attachment_records = []
        display_sections = (
            ("Personal Information", (
                ("Full Name", None), ("Alias", "alias"), ("National ID", "cnic"),
                ("Date of Birth", "date_of_birth"), ("Gender", "gender"),
                ("Nationality", "nationality"),
            )),
            ("Case Information", (
                ("Status", "status"), ("Crimes", "crimes"),
                ("Last Known Location", "last_known_location"),
                ("Arrest Date", "arrest_date"), ("Release Date", "release_date"),
            )),
            ("Notes & Metadata", (
                ("Notes", "notes"), ("Created At", "created_at"),
                ("Updated At", "updated_at"),
            )),
        )
        from xml.sax.saxutils import escape

        for index, record in enumerate(records):
            if index:
                story.append(PageBreak())
            name = f"{record['first_name']} {record['last_name']}".strip()
            story.append(Paragraph(escape(name), styles["Title"]))
            story.append(Paragraph(f"Record ID: {record['id']}", styles["Normal"]))
            photo_data = base64.b64decode(record["photo"]) if record["photo"] else None
            if photo_data:
                story.append(Paragraph("PHOTO", styles["Heading2"]))
                story.append(Spacer(1, 8))
                story.append(PDFImage(
                    io.BytesIO(photo_data), width=45 * mm, height=55 * mm,
                    kind="proportional",
                ))
                story.append(Spacer(1, 8))
            details = []
            for section, fields in display_sections:
                details.append([
                    Paragraph(escape(section), styles["Heading3"]), "",
                ])
                for label, field in fields:
                    if field == "cnic":
                        label = national_id_label(record["nationality"])
                    value = name if field is None else (record[field] or "—")
                    details.append([
                        Paragraph(escape(label), styles["BodyText"]),
                        Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["BodyText"]),
                    ])
            table = Table(details, colWidths=[42 * mm, 138 * mm])
            table.setStyle(TableStyle([
                ("FONTSIZE", (0, 0), (-1, -1), 8),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("SPAN", (0, 0), (1, 0)),
                ("SPAN", (0, 7), (1, 7)),
                ("SPAN", (0, 13), (1, 13)),
                ("BACKGROUND", (0, 0), (-1, 0), pdf_colors.HexColor("#e8eef7")),
                ("BACKGROUND", (0, 7), (-1, 7), pdf_colors.HexColor("#e8eef7")),
                ("BACKGROUND", (0, 13), (-1, 13), pdf_colors.HexColor("#e8eef7")),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, pdf_colors.grey),
                ("LINEBELOW", (0, 7), (-1, 7), 0.5, pdf_colors.grey),
                ("LINEBELOW", (0, 13), (-1, 13), 0.5, pdf_colors.grey),
            ]))
            story.append(table)
            attachment_records.append(record)

        doc.build(story)
        payload = json.dumps({
            "format": RECORD_PDF_FORMAT,
            "version": RECORD_PDF_VERSION,
            "records": attachment_records,
        }, ensure_ascii=False).encode("utf-8")
        pdf_buffer.seek(0)
        reader = PdfReader(pdf_buffer, strict=True)
        writer = PdfWriter()
        writer.clone_document_from_reader(reader)
        writer.add_attachment(RECORD_PDF_ATTACHMENT, payload)
        with secure_output_path(path) as output_path:
            writer.write(output_path)

    def import_records_pdf(self):
        path = filedialog.askopenfilename(
            title="Import App-Exported Records PDF",
            filetypes=[("PDF files", "*.pdf")],
        )
        if not path:
            return
        try:
            imported_records = read_records_pdf(path)
        except Exception as exc:
            messagebox.showerror("Import", f"Could not import records from this PDF:\n{exc}")
            return
        count = len(imported_records)
        if not messagebox.askyesno(
            "Confirm Import",
            f"Import {count} record(s) and their photos?\n"
            "Records will be added as new entries; existing records will not be replaced.",
        ):
            return

        conn = get_db_connection()
        if not conn:
            return
        created_photo_paths = []
        try:
            conn.execute("BEGIN")
            for record, photo_data in imported_records:
                first_name = record["first_name"].strip()
                last_name = record["last_name"].strip()
                photo_path = None
                if photo_data:
                    photo_path = save_photo_bytes_to_media(photo_data, first_name, last_name)
                    created_photo_paths.append(photo_path)
                imported_status = record.get("status")
                if imported_status not in STATUS_OPTIONS:
                    imported_status = "Wanted"
                cursor = conn.execute(
                    """INSERT INTO criminals (
                        first_name,last_name,alias,cnic,date_of_birth,gender,nationality,
                        last_known_location,crimes,status,arrest_date,release_date,notes,
                        case_number,photo_path,created_at,updated_at
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (
                        first_name, last_name, record.get("alias"), record.get("cnic"),
                        record.get("date_of_birth"), record.get("gender"),
                        record.get("nationality"), record.get("last_known_location"),
                        record.get("crimes"), imported_status,
                        record.get("arrest_date"), record.get("release_date"),
                        record.get("notes"), record.get("case_number"), photo_path,
                        record.get("created_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        record.get("updated_at") or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    ),
                )
                self._log_audit(conn, "IMPORT", "criminals", cursor.lastrowid)
            conn.commit()
        except Exception as exc:
            conn.rollback()
            cleanup_errors = []
            for photo_path in created_photo_paths:
                try:
                    os.remove(photo_path)
                except OSError as cleanup_error:
                    cleanup_errors.append(str(cleanup_error))
            message = f"Could not import records:\n{exc}"
            if cleanup_errors:
                message += "\nSome temporary photo files could not be removed:\n" + "\n".join(cleanup_errors)
            messagebox.showerror("Import", message)
            return
        finally:
            conn.close()
        self.load_criminals()
        messagebox.showinfo("Import", f"{count} record(s) imported successfully, including available photos.")

    def backup_database(self):
        path = filedialog.asksaveasfilename(defaultextension=".db",
                                            filetypes=[("SQLite Database", "*.db")],
                                            title="Save Backup")
        if not path:
            return
        try:
            os.makedirs(BACKUP_DIR, exist_ok=True)
            source = get_db_connection()
            if not source:
                return
            try:
                destination = secure_connect(path)
                try:
                    source.backup(destination)
                    destination.commit()
                finally:
                    destination.close()
                secure_permissions(path, force=True)
            finally:
                source.close()
            conn = get_db_connection()
            if conn:
                self._log_audit(conn, "BACKUP", "database", None)
                conn.commit()
                conn.close()
            messagebox.showinfo("Backup", f"Backup saved to:\n{path}")
        except Exception as e:
            messagebox.showerror("Backup Failed", str(e))

    def clear_all_data(self):
        if not messagebox.askyesno("Confirm", "DELETE ALL RECORDS?\n\nThis cannot be undone!"):
            return
        conn = get_db_connection()
        if not conn:
            return
        cur = conn.cursor()
        cur.execute("DELETE FROM criminals")
        conn.commit()
        self._log_audit(conn, "CLEAR_ALL", "criminals", None)
        conn.commit()
        conn.close()
        messagebox.showinfo("Cleared", "All records have been deleted.")
        self.load_criminals()
        self.update_statistics()

    def show_about(self):
        win = tk.Toplevel(self.root)
        win.title("About")
        win.geometry("400x320")
        win.resizable(False, False)
        win.configure(bg=Theme.BG)
        win.grab_set()

        tk.Label(
            win, text="Criminal Database\nManagement System",
            font=Theme.F_HEADING, fg=Theme.TEXT, bg=Theme.BG
        ).pack(pady=(20, 4))
        tk.Label(
            win, text=f"Version {APP_VERSION}", font=Theme.F_SMALL,
            fg=Theme.TEXT_MUTED, bg=Theme.BG
        ).pack()

        ttk.Separator(win, orient="horizontal").pack(fill=tk.X, padx=24, pady=14)

        features = [
            "Criminal records: add, view, edit, delete, filter",
            "Identity, national ID validation and multi-case files",
            "Face recognition and official PDF reports",
            "Role-based login, lockout and audit logging",
            "Local SQLite storage with encrypted passwords",
        ]
        for f in features:
            tk.Label(
                win, text=f"• {f}", anchor="w", font=Theme.F_SMALL,
                fg=Theme.TEXT, bg=Theme.BG
            ).pack(fill=tk.X, padx=28)

        ttk.Separator(win, orient="horizontal").pack(fill=tk.X, padx=24, pady=10)

        tk.Label(
            win, text="Built with Python · Tkinter · SQLCipher · Pillow",
            font=Theme.F_SMALL, fg=Theme.TEXT_MUTED, bg=Theme.BG
        ).pack()

        link = tk.Label(
            win, text="nexoratech.solutions", fg=Theme.BLUE,
            font=Theme.F_SMALL, cursor="hand2", bg=Theme.BG
        )
        link.pack(pady=4)
        link.bind("<Button-1>", lambda _: webbrowser.open("https://nexoratech.solutions/"))

        self._btn(win, "Close", win.destroy, "#7f8c8d").pack(pady=10)

    def _show_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if iid:
            self.tree.selection_set(iid)
        try:
            self.context_menu.tk_popup(event.x_root, event.y_root)
        finally:
            self.context_menu.grab_release()

    def _log_audit(self, conn: sqlite3.Connection, action: str, table: str,
                   record_id):
        user = ""
        if getattr(self, "current_user", None):
            user = self.current_user.get("username", "")
        conn.execute("""INSERT INTO audit_log (user_action,table_name,record_id,old_values,new_values)
                        VALUES (?,?,?,NULL,NULL)""",
                     (f"{action} [{user}]" if user else action, table, record_id))

    @staticmethod
    def _btn(parent, text: str, command, bg: str, fg: str = "white", pad=(12, 4)) -> tk.Button:
        normalized = bg.lower()
        if normalized in {"#e74c3c", "#c0392b", "#d95363"}:
            kind = "danger"
        elif normalized in {"#27ae60", "#16a34a", "#23876a"}:
            kind = "success"
        elif normalized in {"#f39c12", "#e67e22", "#f59e0b"}:
            kind = "warning"
        elif normalized in {"#7f8c8d", "#95a5a6"}:
            kind = "ghost"
        else:
            kind = "primary"
        return modern_button(parent, text, command, kind=kind, pad=pad)



# ========================= ENHANCED FYP EXTENSIONS =========================

import re
import threading

try:
    from reportlab.lib import colors as pdf_colors
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (
        Image as PDFImage,
        PageBreak,
        SimpleDocTemplate,
        Paragraph,
        Spacer,
        Table,
        TableStyle,
    )
except ImportError:
    pdf_colors = None

try:
    import numpy as np
    import cv2
    from face_engine import FaceEngine
except ImportError:
    np = None
    cv2 = None
    FaceEngine = None

ENHANCED_DB = DATABASE_NAME
POLICE_DB = AUTH_DB_PATH


def init_enhanced_db():
    init_db()
    conn = secure_connect(ENHANCED_DB)
    cur = conn.cursor()
    cur.execute("PRAGMA foreign_keys=ON")
    existing = {r[1] for r in cur.execute("PRAGMA table_info(criminals)").fetchall()}
    migrations = {
        "cnic": "TEXT",
        "case_number": "TEXT",
        "face_embedding": "BLOB",
    }
    for col, typ in migrations.items():
        if col not in existing:
            cur.execute(f"ALTER TABLE criminals ADD COLUMN {col} {typ}")

    cur.execute("""CREATE TABLE IF NOT EXISTS cases (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        criminal_id INTEGER NOT NULL,
        case_number TEXT NOT NULL UNIQUE,
        case_title TEXT,
        crime_type TEXT,
        station TEXT,
        officer TEXT,
        status TEXT DEFAULT 'Open',
        opened_date TEXT,
        closed_date TEXT,
        notes TEXT,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(criminal_id) REFERENCES criminals(id) ON DELETE CASCADE
    )""")
    cur.execute("""CREATE TABLE IF NOT EXISTS face_embeddings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        criminal_id INTEGER NOT NULL,
        embedding BLOB NOT NULL,
        model_name TEXT NOT NULL DEFAULT 'MobileFaceNet',
        created_at TEXT DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(criminal_id) REFERENCES criminals(id) ON DELETE CASCADE
    )""")
    conn.commit()
    conn.close()

    auth = secure_connect(POLICE_DB)
    auth.execute("""CREATE TABLE IF NOT EXISTS app_users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('Admin','Officer')),
        full_name TEXT,
        active INTEGER DEFAULT 1,
        created_at TEXT DEFAULT CURRENT_TIMESTAMP
    )""")
    ensure_user_security_columns(auth)
    if auth.execute("SELECT COUNT(*) FROM app_users").fetchone()[0] == 0:
        auth.execute(
            "INSERT INTO app_users(username,password_hash,role,full_name,must_change) VALUES(?,?,?,?,1)",
            ("admin", hash_password("admin123"), "Admin", "System Administrator"),
        )
        auth.execute(
            "INSERT INTO app_users(username,password_hash,role,full_name,must_change) VALUES(?,?,?,?,1)",
            ("officer", hash_password("officer123"), "Officer", "Police Officer"),
        )
    auth.commit()
    auth.close()
    _secure_existing_photos()


def validate_cnic(value: str) -> bool:
    return bool(re.fullmatch(r"\d{5}-\d{7}-\d", value.strip()))


def normalize_cnic(value: str) -> str:
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 13:
        return f"{digits[:5]}-{digits[5:12]}-{digits[12]}"
    return value.strip()


def is_pakistani_nationality(nationality: str) -> bool:
    return (nationality or "").strip().casefold() in {"pakistan", "pakistani"}


def national_id_label(nationality: str) -> str:
    if is_pakistani_nationality(nationality):
        return "CNIC"
    if (nationality or "").strip():
        return "Foreign ID"
    return "CNIC / Foreign ID"


def national_id_validation_error(nationality: str, identifier: str) -> str | None:
    if not (nationality or "").strip():
        return "Select a nationality before entering the national ID."
    label = national_id_label(nationality)
    if not (identifier or "").strip():
        return f"{label} is required."
    if is_pakistani_nationality(nationality) and not validate_cnic(normalize_cnic(identifier)):
        return "Use Pakistani CNIC format: XXXXX-XXXXXXX-X."
    return None


def _apply_window_icon(window) -> None:
    """Set the window icon from the bundled assets, best effort."""
    ico = os.path.join(RESOURCE_DIR, "assets", "icon.ico")
    png = os.path.join(RESOURCE_DIR, "assets", "icon.png")
    try:
        if os.path.isfile(ico):
            window.iconbitmap(ico)
            return
    except Exception:
        pass
    try:
        if os.path.isfile(png):
            image = tk.PhotoImage(file=png)
            window.iconphoto(True, image)
            window._icon_image = image
    except Exception:
        pass


def _open_login(notice: str = ""):
    try:
        init_enhanced_db()
    except (OSError, RuntimeError, ValueError, sqlite3.Error, subprocess.CalledProcessError) as exc:
        messagebox.showerror("Secure Storage Error", f"Could not initialize protected local data:\n{exc}")
        return
    ctk.set_appearance_mode("Dark")
    while True:
        root = tk.Tk()
        root.withdraw()
        _apply_window_icon(root)
        session = {"relaunch": False, "notice": ""}
        LoginWindow(root, notice, session)
        root.mainloop()
        try:
            root.destroy()
        except tk.TclError:
            pass
        if not session["relaunch"]:
            break
        notice = session["notice"]


class LoginWindow:
    def __init__(self, root, notice="", session=None):
        self.root = root
        self.session = session if session is not None else {"relaunch": False, "notice": ""}
        self.win = ctk.CTkToplevel(root)
        self.win.title("Secure Officer Login")
        _apply_window_icon(self.win)
        self.win.geometry("520x650")
        self.win.minsize(460, 580)
        self.win.resizable(True, True)
        self.win.protocol("WM_DELETE_WINDOW", root.destroy)
        self.win.configure(fg_color=Theme.SIDEBAR)

        ctk.CTkLabel(
            self.win,
            text="CRIMINAL RECORDS",
            font=ctk.CTkFont(family=Theme.FONT, size=12, weight="bold"),
            text_color=Theme.GOLD
        ).pack(anchor="w", padx=44, pady=(36, 6))
        
        ctk.CTkLabel(
            self.win,
            text="Welcome to your secure workspace",
            font=ctk.CTkFont(family=Theme.FONT, size=25, weight="bold"),
            text_color=Theme.WHITE
        ).pack(anchor="w", padx=44)
        ctk.CTkLabel(
            self.win,
            text="Sign in with your authorized officer account.",
            font=ctk.CTkFont(family=Theme.FONT, size=13),
            text_color=Theme.TEXT_SOFT
        ).pack(anchor="w", padx=44, pady=(6, 21))

        card = ctk.CTkFrame(
            self.win, corner_radius=16, fg_color=Theme.NAVY,
            border_width=1, border_color="#34435B"
        )
        card.pack(padx=36, fill="both", expand=True)

        ctk.CTkLabel(
            card, text="Username", font=ctk.CTkFont(weight="bold", size=12),
            text_color=Theme.TEXT_ON_DARK
        ).pack(anchor="w", padx=30, pady=(32, 7))
        self.username = ctk.CTkEntry(
            card, height=44, placeholder_text="Enter your username",
            fg_color="#172338", border_color="#34435B", text_color=Theme.WHITE,
            placeholder_text_color="#8190A6", corner_radius=8
        )
        self.username.pack(fill="x", padx=30)

        ctk.CTkLabel(
            card, text="Password", font=ctk.CTkFont(weight="bold", size=12),
            text_color=Theme.TEXT_ON_DARK
        ).pack(anchor="w", padx=30, pady=(18, 7))
        self.password = ctk.CTkEntry(
            card, height=44, show="•", placeholder_text="Enter your password",
            fg_color="#172338", border_color="#34435B", text_color=Theme.WHITE,
            placeholder_text_color="#8190A6", corner_radius=8
        )
        self.password.pack(fill="x", padx=30)
        self.password.bind("<Return>", lambda event: self.login())

        self.message = ctk.CTkLabel(
            card, text="", text_color=Theme.RED_LIGHT,
            font=ctk.CTkFont(size=12), wraplength=360
        )
        self.message.pack(pady=(15, 8))
        if notice:
            self.message.configure(text=notice, text_color=Theme.TEXT_SOFT)

        ctk.CTkButton(
            card,
            text="Sign in",
            height=46,
            corner_radius=8,
            font=ctk.CTkFont(weight="bold", size=13),
            command=self.login,
            fg_color=Theme.BLUE,
            hover_color=Theme.BLUE_HOVER
        ).pack(fill="x", padx=30, pady=(4, 30))

        ctk.CTkLabel(
            self.win,
            text="Balochistan Police   /   Local encrypted records",
            text_color=Theme.TEXT_SOFT,
            font=ctk.CTkFont(size=10)
        ).pack(pady=16)
        
        self.username.focus_set()
        self.win.deiconify()

    def login(self):
        username = self.username.get().strip()
        password = self.password.get()
        if not username or not password:
            self.message.configure(text="Enter your username and password.")
            return
        remaining = account_lock_seconds(username)
        if remaining > 0:
            self.message.configure(
                text=f"Account locked after too many failed attempts. Try again in {remaining}s."
            )
            return

        conn = secure_connect(POLICE_DB)
        row = conn.execute(
            "SELECT username,password_hash,role,full_name,must_change "
            "FROM app_users WHERE username=? AND active=1",
            (username,),
        ).fetchone()
        conn.close()

        if not row or not verify_password(password, row[1]):
            locked_for = register_failure(username)
            if locked_for > 0:
                self.message.configure(
                    text=f"Too many failed attempts. Account locked for {locked_for}s."
                )
            else:
                self.message.configure(text="Invalid username or password.")
            return

        register_success(username)
        self.win.destroy()
        self.root.deiconify()
        _apply_window_icon(self.root)
        EnhancedCriminalDatabaseApp(
            self.root,
            {
                "username": row[0],
                "role": row[2],
                "full_name": row[3],
                "must_change": bool(row[4]),
            },
            self.session,
        )


class EnhancedCriminalDatabaseApp(CriminalDatabaseApp):
    def __init__(self, root, user, session=None):
        init_enhanced_db()
        self.current_user = user
        self.face_engine = None
        self._session = session if session is not None else {"relaunch": False, "notice": ""}
        super().__init__(root)
        self.root.title(f"Criminal Record Management System — {user['role']}: {user['full_name'] or user['username']}")
        self._build_enhanced_features()
        self._apply_permissions()
        if user.get("must_change"):
            self.root.after(300, self._prompt_default_password_change)

    def _prompt_default_password_change(self):
        messagebox.showwarning(
            "Change your password",
            "This account is still using its default password.\n"
            "Please choose a new password now.",
            parent=self.root,
        )
        self.change_password()

    def _apply_permissions(self):
        if self.current_user["role"] != "Admin":
            self._tools_menu.entryconfig("Clear All Data", state=tk.DISABLED)

    def _build_enhanced_features(self):
        self.user_dashboard_frame = ttk.Frame(
            self.notebook, padding=18, style="Workspace.TFrame"
        )
        self.identity_frame = ttk.Frame(
            self.notebook, padding=12, style="Workspace.TFrame"
        )
        self.face_frame = ttk.Frame(
            self.notebook, padding=12, style="Workspace.TFrame"
        )
        self.reports_frame = ttk.Frame(
            self.notebook, padding=12, style="Workspace.TFrame"
        )
        self.notebook.add(self.identity_frame, text="Identity & Cases")
        self.notebook.add(self.face_frame, text="Face Recognition")
        self.notebook.add(self.reports_frame, text="Reports")
        self.notebook.add(self.user_dashboard_frame, text="User Dashboard")
        self._add_nav_item("◇   Identity & cases", self.identity_frame)
        self._add_nav_item("◉   Face recognition", self.face_frame)
        self._add_nav_item("▤   Reports", self.reports_frame)
        self._add_nav_item("◉   User dashboard", self.user_dashboard_frame)
        self._sync_navigation()
        self._setup_identity_frame()
        self._setup_face_frame()
        self._setup_reports_frame()
        self._add_security_menu()
        self._setup_user_dashboard()

    def _is_active_admin(self):
        conn = secure_connect(POLICE_DB)
        try:
            row = conn.execute(
                "SELECT role,active FROM app_users WHERE username=?",
                (self.current_user["username"],),
            ).fetchone()
            return bool(row and row[0] == "Admin" and row[1] == 1)
        finally:
            conn.close()

    def _require_admin(self, action="perform this action"):
        try:
            if self._is_active_admin():
                return True
        except (
            OSError, RuntimeError, ValueError, sqlite3.Error,
            subprocess.CalledProcessError,
        ) as exc:
            messagebox.showerror(
                "Permission Check Failed",
                f"Could not verify administrator access:\n{exc}",
                parent=self.root,
            )
            return False
        messagebox.showwarning(
            "Administrator Required",
            f"Only an active Administrator can {action}.",
            parent=self.root,
        )
        return False

    def _setup_user_dashboard(self):
        frame = self.user_dashboard_frame
        user = self.current_user
        display_name = user.get("full_name") or user.get("username") or "User"

        tk.Label(
            frame, text="User dashboard", font=Theme.F_TITLE,
            bg=Theme.BG, fg=Theme.TEXT
        ).pack(anchor="w")
        tk.Label(
            frame, text="Your account details, access level, and session controls.",
            font=Theme.F_BODY, bg=Theme.BG, fg=Theme.TEXT_MUTED
        ).pack(anchor="w", pady=(4, 18))

        profile = tk.Frame(
            frame, bg=Theme.CARD, highlightbackground=Theme.BORDER,
            highlightthickness=1, padx=24, pady=20
        )
        profile.pack(fill=tk.X)
        self.user_dashboard_name_label = tk.Label(
            profile, text=display_name, font=Theme.F_TITLE,
            bg=Theme.CARD, fg=Theme.TEXT
        )
        self.user_dashboard_name_label.pack(anchor="w")
        tk.Label(
            profile, text=f"@{user.get('username', '')}",
            font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT_MUTED
        ).pack(anchor="w", pady=(3, 12))

        account_values = {
            "Role": user.get("role", "User"),
            "Account status": "Active",
            "Account created": "Not available",
            "Last sign-in": "Current session",
        }
        conn = secure_connect(POLICE_DB)
        try:
            row = conn.execute(
                "SELECT role,active,created_at,last_login FROM app_users WHERE username=?",
                (user["username"],),
            ).fetchone()
        finally:
            conn.close()
        if row:
            account_values["Role"] = row[0] or "User"
            account_values["Account status"] = "Active" if row[1] else "Disabled"
            account_values["Account created"] = row[2] or "Not available"
            account_values["Last sign-in"] = row[3] or "Current session"
        self.current_user["role"] = account_values["Role"]

        details = tk.Frame(profile, bg=Theme.CARD)
        details.pack(fill=tk.X)
        for column in range(2):
            details.grid_columnconfigure(column, weight=1)
        self.user_dashboard_values = {}
        for index, (label, value) in enumerate(account_values.items()):
            cell = tk.Frame(details, bg=Theme.CARD)
            cell.grid(
                row=index // 2, column=index % 2, sticky="ew",
                padx=(0, 16), pady=(8, 4)
            )
            tk.Label(
                cell, text=label.upper(), font=(Theme.FONT, 8, "bold"),
                bg=Theme.CARD, fg=Theme.TEXT_MUTED
            ).pack(anchor="w")
            value_label = tk.Label(
                cell, text=value, font=Theme.F_SUBHEAD,
                bg=Theme.CARD, fg=Theme.TEXT
            )
            value_label.pack(anchor="w", pady=(3, 0))
            self.user_dashboard_values[label] = value_label

        access = tk.Frame(
            frame, bg=Theme.CARD, highlightbackground=Theme.BORDER,
            highlightthickness=1, padx=20, pady=16
        )
        access.pack(fill=tk.X, pady=(14, 0))
        is_admin = account_values["Role"] == "Admin"
        tk.Label(
            access, text="YOUR ACCESS", font=(Theme.FONT, 8, "bold"),
            bg=Theme.CARD, fg=Theme.TEXT_MUTED
        ).pack(anchor="w")
        access_text = (
            "Administrator access: manage user accounts and all administrative tools."
            if is_admin else
            "Officer access: manage records and use operational tools. User administration is restricted to active administrators."
        )
        tk.Label(
            access, text=access_text, font=Theme.F_BODY,
            bg=Theme.CARD, fg=Theme.TEXT, wraplength=760, justify=tk.LEFT
        ).pack(anchor="w", pady=(6, 0))

        actions = tk.Frame(frame, bg=Theme.BG)
        actions.pack(fill=tk.X, pady=(16, 0))
        modern_button(
            actions, "Change my password", self.change_password,
            "ghost"
        ).pack(side=tk.LEFT, padx=(0, 8))
        if is_admin:
            modern_button(
                actions, "Manage users", self.manage_users, "primary"
            ).pack(side=tk.LEFT, padx=8)
        modern_button(
            actions, "Sign out", self.logout, "danger"
        ).pack(side=tk.RIGHT)

    def _add_security_menu(self):
        menubar = self.root.nametowidget(self.root["menu"])
        security = tk.Menu(menubar, tearoff=0)
        security.add_command(label=f"Signed in: {self.current_user['username']} ({self.current_user['role']})")
        security.add_separator()
        security.add_command(label="Manage Users", command=self.manage_users,
                             state=tk.NORMAL if self.current_user["role"] == "Admin" else tk.DISABLED)
        security.add_command(label="Change My Password", command=self.change_password)
        security.add_separator()
        security.add_command(label="Logout", command=self.logout)
        menubar.add_cascade(label="Security", menu=security)

    def _setup_identity_frame(self):
        f = self.identity_frame
        tk.Label(
            f, text="Identity & Case Management", font=Theme.F_HEADING,
            fg=Theme.TEXT, bg=Theme.BG
        ).pack(anchor="w", pady=(0, 8))
        top = tk.Frame(f, bg=Theme.BG)
        top.pack(fill=tk.X, pady=5)
        tk.Label(
            top, text="Criminal ID:", font=Theme.F_BODY,
            bg=Theme.BG, fg=Theme.TEXT
        ).pack(side=tk.LEFT)
        self.identity_id = tk.Entry(
            top, width=10, font=Theme.F_BODY, bg=Theme.INPUT,
            fg=Theme.TEXT, relief=tk.FLAT, highlightthickness=1,
            highlightbackground=Theme.BORDER, highlightcolor=Theme.BLUE,
            insertbackground=Theme.TEXT
        )
        self.identity_id.pack(side=tk.LEFT, padx=5)
        self._btn(top, "Load", self.load_identity, "#2980b9", pad=(10,3)).pack(side=tk.LEFT)
        self._btn(top, "Selected Record", self.load_selected_identity, "#8e44ad", pad=(10,3)).pack(side=tk.LEFT, padx=5)
        self.identity_name = tk.Label(
            f, text="No record loaded", font=Theme.F_SUBHEAD,
            fg=Theme.TEXT_MUTED, bg=Theme.BG
        )
        self.identity_name.pack(anchor="w", pady=4)

        form = tk.LabelFrame(
            f, text="IDENTITY", padx=12, pady=10, font=Theme.F_SUBHEAD,
            bg=Theme.CARD, fg=Theme.NAVY, highlightbackground=Theme.BORDER
        )
        form.pack(fill=tk.X, pady=5)
        self.cnic_var = tk.StringVar()
        self.identity_nationality = ""
        self.case_var = tk.StringVar()
        self.case_title_var = tk.StringVar()
        self.station_var = tk.StringVar()
        self.officer_var = tk.StringVar(value=self.current_user["full_name"] or self.current_user["username"])
        self.identity_id_label = tk.Label(
            form, text="CNIC / Foreign ID *:", width=24, anchor="w",
            font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT
        )
        self.identity_id_label.grid(row=0, column=0, sticky="w", pady=4)
        identity_fields = [
            ("Primary Case Number", self.case_var),
            ("Case Title", self.case_title_var),
            ("Police Station", self.station_var),
            ("Investigating Officer", self.officer_var),
        ]
        for i, (label, var) in enumerate(identity_fields, start=1):
            tk.Label(
                form, text=label + ":", width=24, anchor="w",
                font=Theme.F_BODY, bg=Theme.CARD, fg=Theme.TEXT
            ).grid(row=i, column=0, sticky="w", pady=4)
        tk.Entry(
            form, textvariable=self.cnic_var, width=45, font=Theme.F_BODY,
            bg=Theme.INPUT, fg=Theme.TEXT, relief=tk.FLAT,
            highlightthickness=1, highlightbackground=Theme.BORDER,
            highlightcolor=Theme.BLUE, insertbackground=Theme.TEXT
        ).grid(row=0, column=1, sticky="w", pady=4)
        for i, (_label, var) in enumerate(identity_fields, start=1):
            tk.Entry(
                form, textvariable=var, width=45, font=Theme.F_BODY,
                bg=Theme.INPUT, fg=Theme.TEXT, relief=tk.FLAT,
                highlightthickness=1, highlightbackground=Theme.BORDER,
                highlightcolor=Theme.BLUE, insertbackground=Theme.TEXT
            ).grid(row=i, column=1, sticky="w", pady=4)
        self._btn(form, "Validate & Save Identity", self.save_identity, "#27ae60").grid(row=5, column=1, sticky="w", pady=8)

        cases = tk.LabelFrame(
            f, text="CASES FOR SELECTED CRIMINAL", padx=8, pady=8,
            font=Theme.F_SUBHEAD, bg=Theme.CARD, fg=Theme.NAVY,
            highlightbackground=Theme.BORDER
        )
        cases.pack(fill=tk.BOTH, expand=True, pady=8)
        self.case_tree = ttk.Treeview(cases, columns=("id","case","title","crime","station","officer","status","opened"), show="headings", height=7)
        for col, head, w in zip(self.case_tree["columns"], ["ID","Case No.","Title","Crime","Station","Officer","Status","Opened"], [45,120,160,130,120,130,80,90]):
            self.case_tree.heading(col, text=head); self.case_tree.column(col, width=w)
        self.case_tree.pack(fill=tk.BOTH, expand=True)
        bar = tk.Frame(f, bg=Theme.BG); bar.pack(pady=5)
        self._btn(bar, "Add case", self.add_case, "#27ae60").pack(side=tk.LEFT, padx=3)
        self._btn(bar, "Edit case", self.edit_case, "#f39c12", fg="black").pack(side=tk.LEFT, padx=3)
        self._btn(bar, "Delete case", self.delete_case, "#e74c3c").pack(side=tk.LEFT, padx=3)

    def load_selected_identity(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showerror("Identity", "Select a criminal from View All first."); return
        self.identity_id.delete(0, tk.END); self.identity_id.insert(0, self.tree.item(sel[0])["values"][0]); self.load_identity()

    def load_identity(self):
        cid = self.identity_id.get().strip()
        if not cid.isdigit():
            messagebox.showerror("Identity", "Enter a valid criminal ID."); return
        conn = secure_connect(ENHANCED_DB)
        row = conn.execute(
            "SELECT id,first_name,last_name,cnic,case_number,nationality "
            "FROM criminals WHERE id=?", (int(cid),)
        ).fetchone()
        conn.close()
        if not row:
            messagebox.showerror("Identity", "Criminal record not found."); return
        self.identity_name.config(text=f"Record #{row[0]} — {row[1]} {row[2]}")
        self.cnic_var.set(row[3] or "")
        self.identity_nationality = row[5] or ""
        self.identity_id_label.config(text=national_id_label(self.identity_nationality) + " *:")
        self.case_var.set(row[4] or "")
        self.load_cases(int(cid))
        self.identity_frame.update_idletasks()

    def save_identity(self):
        cid = self.identity_id.get().strip()
        cnic = self.cnic_var.get().strip()
        case_no = self.case_var.get().strip()
        if not cid.isdigit(): messagebox.showerror("Validation", "Load a valid criminal ID first."); return
        if is_pakistani_nationality(self.identity_nationality):
            cnic = normalize_cnic(cnic)
        id_error = national_id_validation_error(self.identity_nationality, cnic)
        if id_error:
            messagebox.showerror("Nationality / ID Validation", id_error)
            return
        conn = secure_connect(ENHANCED_DB)
        try:
            conn.execute("UPDATE criminals SET cnic=?,case_number=?,updated_at=CURRENT_TIMESTAMP WHERE id=?", (cnic or None, case_no or None, int(cid)))
            conn.commit()
            conn.execute("INSERT INTO audit_log(user_action,table_name,record_id) VALUES(?,?,?)",
                         ("UPDATE_IDENTITY", "criminals", int(cid)))
            conn.commit()
        except sqlite3.IntegrityError as e:
            messagebox.showerror("Database", str(e)); return
        finally: conn.close()
        messagebox.showinfo("Saved", "Identity and primary case information saved.")
        self.load_criminals()
        self.load_identity()

    def load_cases(self, cid):
        self.case_tree.delete(*self.case_tree.get_children())
        conn = secure_connect(ENHANCED_DB)
        rows = conn.execute("SELECT id,case_number,case_title,crime_type,station,officer,status,opened_date FROM cases WHERE criminal_id=? ORDER BY id DESC", (cid,)).fetchall()
        conn.close()
        for r in rows: self.case_tree.insert("", tk.END, values=r)

    def add_case(self): self._case_dialog()
    def edit_case(self):
        sel = self.case_tree.selection()
        if not sel: messagebox.showerror("Case", "Select a case first."); return
        self._case_dialog(int(self.case_tree.item(sel[0])["values"][0]))
    def delete_case(self):
        sel = self.case_tree.selection()
        if not sel: return
        cid_str = self.identity_id.get().strip()
        if not cid_str.isdigit(): messagebox.showerror("Case", "Load a criminal first."); return
        if not messagebox.askyesno("Delete Case", "Delete this case? This cannot be undone."): return
        case_id = int(self.case_tree.item(sel[0])["values"][0]); cid = int(cid_str)
        conn=secure_connect(ENHANCED_DB); conn.execute("DELETE FROM cases WHERE id=?", (case_id,)); conn.commit(); conn.close(); self.load_cases(cid)

    def _case_dialog(self, case_id=None):
        cid = self.identity_id.get().strip()
        if not cid.isdigit(): messagebox.showerror("Case", "Load a criminal first."); return
        data = ["", "", "", self.station_var.get(), self.officer_var.get(), "Open", datetime.now().strftime("%Y-%m-%d"), "", ""]
        if case_id:
            conn=secure_connect(ENHANCED_DB); row=conn.execute("SELECT case_number,case_title,crime_type,station,officer,status,opened_date,closed_date,notes FROM cases WHERE id=?",(case_id,)).fetchone(); conn.close()
            if not row:return
            data=list(row)
        win=tk.Toplevel(self.root); win.title("Case Record"); win.geometry("540x500"); win.configure(bg=Theme.BG); win.grab_set()
        labels=["Case Number *","Case Title","Crime Type","Police Station","Officer","Status","Opened Date","Closed Date","Notes"]
        entries=[]
        for i,(lab,val) in enumerate(zip(labels,data[:9])):
            tk.Label(
                win, text=lab+":", width=18, anchor="w",
                font=Theme.F_BODY, bg=Theme.BG, fg=Theme.TEXT
            ).grid(row=i,column=0,padx=15,pady=5,sticky="w")
            if i == 5:
                status=ttk.Combobox(win,values=["Open","Under Investigation","Closed","Court"],state="readonly",width=35,font=Theme.F_BODY)
                status.set(val or "Open"); status.grid(row=i,column=1,pady=5)
                entries.append(status)
                continue
            e=tk.Entry(
                win,width=38,font=Theme.F_BODY,bg=Theme.INPUT,fg=Theme.TEXT,
                relief=tk.FLAT,highlightthickness=1,
                highlightbackground=Theme.BORDER,highlightcolor=Theme.BLUE,
                insertbackground=Theme.TEXT
            )
            e.insert(0,val or ""); e.grid(row=i,column=1,pady=5); entries.append(e)
        def save():
            vals=[e.get().strip() for e in entries]
            if not vals[0]: messagebox.showerror("Case","Case number is required."); return
            if vals[6] and not validate_date(vals[6]) or vals[7] and not validate_date(vals[7]): messagebox.showerror("Case","Dates must use YYYY-MM-DD."); return
            conn=secure_connect(ENHANCED_DB)
            try:
                if case_id:
                    conn.execute("UPDATE cases SET case_number=?,case_title=?,crime_type=?,station=?,officer=?,status=?,opened_date=?,closed_date=?,notes=? WHERE id=?",(*vals,case_id))
                else:
                    conn.execute("INSERT INTO cases(criminal_id,case_number,case_title,crime_type,station,officer,status,opened_date,closed_date,notes) VALUES(?,?,?,?,?,?,?,?,?,?)",(int(cid),*vals))
                conn.commit()
            except sqlite3.IntegrityError as e: messagebox.showerror("Case", f"Case number already exists or is invalid.\n{e}"); return
            finally: conn.close()
            win.destroy(); self.load_cases(int(cid))
        self._btn(win,"Save case",save,"#27ae60").grid(row=10,column=1,pady=15,sticky="w")

    def _setup_face_frame(self):
        f=self.face_frame
        self._face_buttons=[]
        def _mk(parent,text,cmd,bg,fg="white"):
            b=self._btn(parent,text,cmd,bg,fg); self._face_buttons.append(b); b.pack(side=tk.LEFT,padx=2); return b

        tk.Label(
            f, text="Face recognition", font=Theme.F_HEADING,
            fg=Theme.TEXT, bg=Theme.BG
        ).pack(anchor="w")
        tk.Label(
            f,
            text="Choose an image or use the camera to match against saved criminal photos.",
            font=Theme.F_BODY, fg=Theme.TEXT_MUTED, bg=Theme.BG,
            wraplength=860, justify=tk.LEFT
        ).pack(anchor="w",pady=(3,12))

        db=tk.LabelFrame(
            f,text="FACE DATABASE",padx=12,pady=10,font=Theme.F_SUBHEAD,
            bg=Theme.CARD,fg=Theme.NAVY,highlightbackground=Theme.BORDER
        )
        db.pack(fill=tk.X)
        self.face_index_lbl=tk.Label(
            db,text="Checking…",font=Theme.F_BODY,
            fg=Theme.TEXT_MUTED,bg=Theme.CARD
        )
        self.face_index_lbl.pack(anchor="w",pady=(0,4))
        _mk(db,"Build / refresh face database",self.rebuild_face_index,"#2980b9")

        tk.Label(
            f,text="Search",font=Theme.F_SUBHEAD,
            fg=Theme.TEXT,bg=Theme.BG
        ).pack(anchor="w",pady=(12,4))
        searchbar=tk.Frame(f,bg=Theme.BG); searchbar.pack(anchor="w")
        _mk(searchbar,"Find by image",self.recognize_image,"#27ae60")
        _mk(searchbar,"Live camera",self.live_recognition,"#f39c12","black")

        tk.Label(
            f,text="Enroll a face",font=Theme.F_SUBHEAD,
            fg=Theme.TEXT,bg=Theme.BG
        ).pack(anchor="w",pady=(12,4))
        self.face_target_lbl=tk.Label(
            f,text="No person chosen yet.",font=Theme.F_BODY,
            fg=Theme.TEXT_MUTED,bg=Theme.BG
        )
        self.face_target_lbl.pack(anchor="w")
        enrollbar=tk.Frame(f,bg=Theme.BG); enrollbar.pack(anchor="w",pady=(4,0))
        _mk(enrollbar,"Choose selected record",self._pick_selected_for_face,"#8e44ad")
        _mk(enrollbar,"Enroll saved photo",self.enroll_selected_face,"#27ae60")
        _mk(enrollbar,"Enroll from camera",self.enroll_camera,"#2980b9")
        self._refresh_face_target()

        self.face_status=tk.Label(
            f,text="",fg=Theme.TEXT_MUTED,bg=Theme.BG,
            wraplength=860,justify="left",font=Theme.F_BODY
        )
        self.face_status.pack(anchor="w",pady=(8,0))
        self._refresh_face_status()

        foot=tk.Frame(f,bg=Theme.BG); foot.pack(anchor="w",pady=(4,0))
        _mk(foot,"Download AI models",self.download_models_click,"#e67e22")
        _mk(foot,"AI help",self.show_ai_setup,"#7f8c8d")

        self.face_preview=tk.Label(
            f,text="Photo / live preview",bg=Theme.CARD,fg=Theme.TEXT_MUTED,
            width=76,height=12,relief=tk.FLAT,
            highlightthickness=1,highlightbackground=Theme.BORDER,
            font=Theme.F_BODY
        )
        self.face_preview.pack(pady=8,expand=True,fill=tk.BOTH)

        self._face_downloading=False; self._dl_progress=[]; self._pending_after_download=None; self._dl_result=[None,None]
        self._refresh_face_status()

        try:
            self.notebook.bind(
                "<<NotebookTabChanged>>",
                lambda e: self._update_face_index_lbl(),
                add="+",
            )
        except Exception:
            pass

    def _auto_pick_view_selection(self):
        if self.identity_id.get().strip().isdigit():
            return
        sel=self.tree.selection()
        if not sel:
            return
        cid=self.tree.item(sel[0])["values"][0]
        if str(cid).isdigit():
            self.identity_id.delete(0,tk.END); self.identity_id.insert(0,str(cid))

    def _refresh_face_target(self):
        if not hasattr(self, "face_target_lbl"):
            return
        self._auto_pick_view_selection()
        cid=self.identity_id.get().strip()
        if not cid.isdigit():
            self.face_target_lbl.config(text="No person chosen yet.",fg=Theme.RED); return
        conn=secure_connect(ENHANCED_DB)
        r=conn.execute("SELECT first_name,last_name FROM criminals WHERE id=?",(int(cid),)).fetchone()
        conn.close()
        if not r:
            self.face_target_lbl.config(text="No person chosen yet.",fg=Theme.RED)
        else:
            self.face_target_lbl.config(text=f"Adding a face for: {r[0]} {r[1]} (ID #{cid})",fg=Theme.SUCCESS)

    def _load_face_target(self, cid_str):
        self.identity_id.delete(0,tk.END)
        self.identity_id.insert(0,cid_str)
        self.load_identity()
        self._refresh_face_target()

    def _pick_selected_for_face(self):
        sel=self.tree.selection()
        if not sel:
            messagebox.showinfo("Choose a person", "Go to the View All tab, highlight a record, then come back and press this button.")
            self.notebook.select(self.view_frame)
            return
        self._load_face_target(str(self.tree.item(sel[0])["values"][0]))

    def _require_target(self):
        self._auto_pick_view_selection()
        cid=self.identity_id.get().strip()
        if not cid.isdigit():
            raise RuntimeError(
                "Choose a person first: select a record in the Records tab, "
                "then press 'Choose selected record' on the Face Recognition tab."
            )
        return int(cid)

    def _face_index_summary(self):
        try:
            conn=secure_connect(ENHANCED_DB)
            with_photo=conn.execute("SELECT COUNT(*) FROM criminals WHERE (photo_path IS NOT NULL AND photo_path!='') OR photo_data IS NOT NULL").fetchone()[0]
            indexed=conn.execute("SELECT COUNT(DISTINCT criminal_id) FROM face_embeddings").fetchone()[0]
            conn.close()
            return int(with_photo), int(indexed)
        except Exception:
            return 0, 0

    def _update_face_index_lbl(self):
        if not hasattr(self, "face_index_lbl"):
            return
        with_photo, indexed = self._face_index_summary()
        self.face_index_lbl.config(text=f"{indexed} of {with_photo} saved photos have a face on file.")

    def _refresh_face_status(self):
        if FaceEngine is None:
            self.face_status.config(text="Face AI is disabled: run 'python -m pip install -r requirements.txt'.",fg=Theme.RED)
            self._update_face_index_lbl(); return
        eng=FaceEngine(); missing=eng.status()
        if missing:
            self.face_status.config(text=f"Face AI is off — models will download on first use ({', '.join(missing)}).",fg=Theme.WARNING)
            self._update_face_index_lbl(); return
        with_photo, indexed = self._face_index_summary()
        self._update_face_index_lbl()
        if with_photo == 0:
            self.face_status.config(text="No saved photos to search yet. Add criminals with photos, then press 'Build / refresh face database'.",fg=Theme.TEXT_MUTED)
        elif indexed < with_photo:
            self.face_status.config(text=f"Faces ready on {indexed} of {with_photo} records. Press 'Build / refresh face database' to finish.",fg=Theme.WARNING)
        else:
            self.face_status.config(text=f"Ready — {indexed} faces on file. Use Find by image or Live camera.",fg=Theme.SUCCESS)

    def _build_face_index(self, all_records=False):
        if not self._ensure_face_models(None):
            return 0, 0, 0
        engine = self._get_face_engine()
        self._set_face_busy(True)
        conn = secure_connect(ENHANCED_DB)
        rows = conn.execute(
            "SELECT id,first_name,last_name,photo_path,photo_data FROM criminals "
            "WHERE (photo_path IS NOT NULL AND photo_path!='') OR photo_data IS NOT NULL"
        ).fetchall()
        if not all_records:
            done = {r[0] for r in conn.execute("SELECT criminal_id FROM face_embeddings")}
            rows = [r for r in rows if r[0] not in done]
        total = len(rows)
        ok = 0; failed = 0
        try:
            for i, (cid, fn, ln, path, data) in enumerate(rows, 1):
                self.face_status.config(text=f"Building face database… {i}/{total} ({fn} {ln})", fg=Theme.WARNING)
                self.root.update_idletasks()
                try:
                    if path and os.path.exists(path):
                        emb, _, _ = _photo_embedding_from_path(engine, path)
                    elif data:
                        arr = np.frombuffer(data, dtype=np.uint8)
                        img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                        if img is None:
                            raise RuntimeError("Could not decode photo")
                        emb, _, _ = engine.embedding_from_image(img)
                    else:
                        continue
                    if all_records:
                        conn.execute("DELETE FROM face_embeddings WHERE criminal_id=?", (cid,))
                    conn.execute("INSERT INTO face_embeddings(criminal_id,embedding,model_name) VALUES(?,?,?)",
                                 (cid, emb.astype(np.float32).tobytes(), "SFace"))
                    conn.execute("UPDATE criminals SET face_embedding=? WHERE id=?", (emb.astype(np.float32).tobytes(), cid))
                    conn.commit(); ok += 1
                except Exception:
                    failed += 1
        finally:
            conn.close()
            self._set_face_busy(False)
        return total, ok, failed

    def _ensure_index(self):
        with_photo, indexed = self._face_index_summary()
        if indexed < with_photo:
            n, ok, failed = self._build_face_index()
            self._refresh_face_status()
        return self._face_index_summary()

    def rebuild_face_index(self):
        if getattr(self, "_face_downloading", False):
            return
        with_photo, _ = self._face_index_summary()
        if with_photo == 0:
            messagebox.showinfo("Face database", "No criminal records have a saved photo yet.\nAdd or update criminals with photos in the Add/Edit form, then come back.")
            return
        try:
            if not messagebox.askyesno("Build face database", f"{with_photo} record(s) have saved photos.\n\nBuild all faces now? (Refreshes any changed photos.)"):
                return
        except Exception:
            pass
        try:
            n, ok, failed = self._build_face_index(all_records=True)
        except Exception as e:
            messagebox.showerror("Face database", str(e)); self._refresh_face_status(); return
        msg = f"Face database built: {ok} of {n} indexed." + (f" {failed} failed (no clear face)." if failed else "")
        self.face_status.config(text=msg, fg=Theme.SUCCESS)
        self._refresh_face_status()

    def _set_face_busy(self, busy):
        st=tk.DISABLED if busy else tk.NORMAL
        for b in getattr(self,"_face_buttons",[]):
            b.config(state=st)
        try: self.root.config(cursor="watch" if busy else "")
        except Exception: pass

    def _ensure_face_models(self, after):
        if FaceEngine is None:
            messagebox.showerror("Face AI", "Install OpenCV, NumPy first: python -m pip install -r requirements.txt")
            return False
        if not FaceEngine().status():
            return True
        if not self._face_downloading:
            self._start_download()
        self._pending_after_download=after
        return False

    def download_models_click(self):
        if self._face_downloading:
            self.face_status.config(text="Already downloading AI models… please wait.",fg=Theme.WARNING)
            return
        if not self._ensure_face_models(None):
            return
        self._refresh_face_status()

    def _start_download(self):
        self._face_downloading=True
        self._dl_progress=[]
        self._dl_result=[None,None]
        self._dl_finished=False
        self._set_face_busy(True)
        self.face_status.config(text="⬇️ Downloading AI models for the first time…",fg=Theme.WARNING)
        if self.root:
            try: self.root.update_idletasks()
            except Exception: pass
        eng=FaceEngine()
        def worker():
            try:
                self._dl_result[1]=eng.download_models(
                    progress=lambda label,recv,total: self._dl_progress.append((label,recv,total))
                )
            except Exception as e:
                self._dl_result[0]=str(e)
            # Signal completion; the Tk thread finishes the job from _poll_download.
            self._dl_finished=True
        threading.Thread(target=worker, daemon=True).start()
        self.root.after(80, self._poll_download)

    def _poll_download(self):
        if not self._face_downloading:
            return
        if self._dl_progress:
            label,recv,total=self._dl_progress[-1]
            mb=recv/(1024*1024)
            pct=(recv/total*100) if total else 0
            self.face_status.config(text=f"⬇️ Downloading {label}… {mb:.1f} MB ({pct:.0f}%)",fg=Theme.WARNING)
        if self._dl_finished:
            self._download_done()
            return
        self.root.after(120, self._poll_download)

    def _download_done(self):
        self._face_downloading=False
        err= self._dl_result[0]
        self._set_face_busy(False)
        if err:
            self.face_status.config(text=err.split("\n")[0],fg=Theme.RED)
            messagebox.showerror("Download failed", err)
            self._pending_after_download=None
            return
        self._refresh_face_status()
        self._refresh_face_target()
        pending=self._pending_after_download
        self._pending_after_download=None
        if pending:
            pending()

    def _get_face_engine(self):
        if FaceEngine is None:
            raise RuntimeError("Install OpenCV, NumPy and ONNX Runtime first: python -m pip install -r requirements.txt")
        if self.face_engine is None: self.face_engine=FaceEngine()
        try:
            self.face_engine.load()
        except Exception as e:
            self.face_engine=None
            raise RuntimeError(str(e))
        return self.face_engine

    def _selected_id(self):
        sel=self.tree.selection()
        if not sel: raise RuntimeError("Select a criminal record from View All first.")
        return int(self.tree.item(sel[0])["values"][0])

    def enroll_selected_face(self):
        if not self._ensure_face_models(self.enroll_selected_face): return
        try: cid=self._require_target()
        except Exception as e: messagebox.showerror("Face Enrollment",str(e)); return
        conn=secure_connect(ENHANCED_DB); row=conn.execute("SELECT first_name,last_name,photo_path,photo_data FROM criminals WHERE id=?",(cid,)).fetchone(); conn.close()
        if not row:
            messagebox.showerror("Face Enrollment", f"Record #{cid} could not be found."); return
        if not row[2]:
            messagebox.showerror("Face Enrollment",f"{row[0]} {row[1]} (record #{cid}) has no saved photo.\nOpen the record in View All and add a photo, then try again, or use Enroll From Camera."); return
        try:
            engine=self._get_face_engine(); emb,_,count=_photo_embedding_from_path(engine, row[2])
            conn=secure_connect(ENHANCED_DB); conn.execute("INSERT INTO face_embeddings(criminal_id,embedding,model_name) VALUES(?,?,?)",(cid,emb.astype(np.float32).tobytes(),"SFace")); conn.execute("UPDATE criminals SET face_embedding=? WHERE id=?",(emb.astype(np.float32).tobytes(),cid)); conn.commit(); conn.close()
            self.face_status.config(text=f"Enrolled {row[0]} {row[1]} (record #{cid}). Faces detected: {count}.",fg=Theme.SUCCESS)
        except Exception as e: messagebox.showerror("Face Enrollment",str(e)); self._refresh_face_status()

    @staticmethod
    def _cv_window_closed(title):
        if cv2 is None:
            return True
        try:
            return cv2.getWindowProperty(title, cv2.WND_PROP_VISIBLE) < 1
        except Exception:
            return False

    def _camera_capture(self, title="Face Capture"):
        if cv2 is None: raise RuntimeError("OpenCV is not installed.")
        cap=cv2.VideoCapture(0)
        if not cap.isOpened(): raise RuntimeError("Could not open the default camera.")
        result=None
        try:
            while True:
                ok,frame=cap.read()
                if not ok: break
                cv2.putText(frame,"SPACE: capture  •  ESC: cancel  •  ✕: close",(15,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,0),2)
                cv2.imshow(title,frame)
                key=cv2.waitKey(1)&0xFF
                if self._cv_window_closed(title): break
                if key==27: break
                if key==32: result=frame.copy(); break
        finally:
            cap.release()
            try: cv2.destroyWindow(title)
            except Exception: pass
        return result

    def enroll_camera(self):
        if not self._ensure_face_models(self.enroll_camera): return
        try: cid=self._require_target(); frame=self._camera_capture("Enroll Face")
        except Exception as e: messagebox.showerror("Face Enrollment",str(e)); return
        if frame is None:return
        try:
            engine=self._get_face_engine(); emb,_,count=engine.embedding_from_image(frame)
            conn=secure_connect(ENHANCED_DB); conn.execute("INSERT INTO face_embeddings(criminal_id,embedding,model_name) VALUES(?,?,?)",(cid,emb.astype(np.float32).tobytes(),"SFace")); conn.execute("UPDATE criminals SET face_embedding=? WHERE id=?",(emb.astype(np.float32).tobytes(),cid)); conn.commit(); conn.close(); self.face_status.config(text=f"Enrolled record #{cid} from camera. Faces detected: {count}.",fg=Theme.SUCCESS); self._refresh_face_status()
        except Exception as e: messagebox.showerror("Face Enrollment",str(e)); self._refresh_face_status()

    def recognize_image(self):
        if not self._ensure_face_models(self.recognize_image): return
        path=filedialog.askopenfilename(title="Select a photo to identify",filetypes=[("Images","*.jpg *.jpeg *.png *.bmp")])
        if not path:return
        self._ensure_index()
        _, indexed = self._face_index_summary()
        if indexed == 0:
            messagebox.showwarning("No faces on file", "No criminal faces are indexed yet.\nAdd criminals with photos and press 'Build / refresh face database'.")
            return
        try:
            engine = self._get_face_engine()
            self.face_status.config(text="Identifying…", fg=Theme.TEXT_MUTED)
            emb, _, count = engine.embedding_from_path(path)
            match = self._match_embedding(emb)
            if match:
                cid,name,score=match
                self.identity_id.delete(0,tk.END); self.identity_id.insert(0,str(cid)); self.load_identity()
                self.face_status.config(text=f"Found: {name} (record #{cid}) — similarity {score:.3f} | {count} face(s) in photo",fg=Theme.SUCCESS)
                if messagebox.askyesno("Identified", f"Found: {name} (record #{cid}).\nSimilarity: {score:.3f}.\n\nOpen this criminal's record and cases?"):
                    self.notebook.select(self.identity_frame)
            else:
                self.face_status.config(text=f"No match above threshold ({self._match_threshold():.2f}). {count} face(s) in the photo.",fg=Theme.RED)
        except Exception as e: messagebox.showerror("Face Recognition",str(e))

    @staticmethod
    def _match_threshold():
        return 0.45

    def _load_embeddings(self):
        conn=secure_connect(ENHANCED_DB)
        rows=conn.execute("SELECT fe.criminal_id,fe.embedding,c.first_name,c.last_name FROM face_embeddings fe JOIN criminals c ON c.id=fe.criminal_id").fetchall()
        conn.close()
        return rows

    def _match_embedding(self, emb, threshold=None, rows=None):
        if threshold is None: threshold=self._match_threshold()
        if rows is None: rows=self._load_embeddings()
        best=None
        for cid,blob,fn,ln in rows:
            try: score=FaceEngine.cosine_similarity(emb,np.frombuffer(blob,dtype=np.float32))
            except Exception: continue
            if best is None or score>best[2]: best=(cid,f"{fn} {ln}".strip(),score)
        return best if best and best[2]>=threshold else None

    def live_recognition(self):
        if not self._ensure_face_models(self.live_recognition): return
        try: engine=self._get_face_engine()
        except Exception as e: messagebox.showerror("Face AI",str(e)); return
        self._ensure_index()
        _, indexed = self._face_index_summary()
        if indexed == 0:
            messagebox.showwarning("No faces on file", "No criminal faces are indexed yet.\nAdd criminals with photos and press 'Build / refresh face database'.")
            return
        cap=cv2.VideoCapture(0)
        if not cap.isOpened(): messagebox.showerror("Camera","Could not open camera."); return
        indexed_rows=self._load_embeddings()
        try:
            while True:
                ok,frame=cap.read()
                if not ok: break
                try:
                    faces=engine.detect(frame)
                    for face in faces:
                        x, y, w, h = map(int, face[:4])
                        emb = engine.embedding_from_face(frame, face)
                        match = self._match_embedding(emb, rows=indexed_rows)
                        label="Unknown"
                        if match: label=f"{match[1]}  {match[2]:.2f}"
                        else: label=f"Unknown {self._match_threshold():.2f}"
                        cv2.rectangle(frame,(x,y),(x+w,y+h),(0,255,0),2); cv2.putText(frame,label,(x,max(20,y-8)),cv2.FONT_HERSHEY_SIMPLEX,.55,(0,255,0),2)
                except Exception: pass
                cv2.putText(frame,"ESC: close  •  ✕: close",(15,30),cv2.FONT_HERSHEY_SIMPLEX,.7,(0,255,255),2)
                cv2.imshow("Live Face Recognition",frame)
                if cv2.waitKey(1)&0xFF==27: break
                if self._cv_window_closed("Live Face Recognition"): break
        finally:
            cap.release()
            try: cv2.destroyWindow("Live Face Recognition")
            except Exception: pass

    def show_ai_setup(self):
        if FaceEngine is None:
            messagebox.showinfo("AI Setup", "Face AI is disabled: install OpenCV, NumPy and ONNX Runtime.\n\npython -m pip install -r requirements.txt")
            return
        eng=FaceEngine(); missing=eng.status()
        if not missing:
            text="Face AI is ready.\n\nModels found in the models folder:\n  - "+eng.yunet_path+"\n  - "+eng.sface_path
        else:
            text=("Face AI is disabled — missing: "+", ".join(missing)+"\n\n"
                  "The models download automatically on first use.\n"
                  "If this machine is offline, download them manually:\n\n"
                  "1. YuNet (face detection):\n   "+FaceEngine.YUNET_URL+"\n\n"
                  "2. SFace (face recognition):\n   "+FaceEngine.SFACE_URL+"\n\n"
                  "Place both files in the models folder next to the application.")
        messagebox.showinfo("AI Setup", text)

    def _setup_reports_frame(self):
        f=self.reports_frame
        tk.Label(
            f,text="Official reports",font=Theme.F_HEADING,
            fg=Theme.TEXT,bg=Theme.BG
        ).pack(anchor="w")
        tk.Label(
            f,
            text="Generate a printable report for a selected record or export the full case register.",
            font=Theme.F_BODY,fg=Theme.TEXT_MUTED,bg=Theme.BG,
            wraplength=760,justify=tk.LEFT
        ).pack(anchor="w",pady=(3,15))
        actions=tk.LabelFrame(
            f,text="REPORT ACTIONS",font=Theme.F_SUBHEAD,
            padx=14,pady=12,bg=Theme.CARD,fg=Theme.NAVY,
            highlightbackground=Theme.BORDER
        )
        actions.pack(anchor="nw",fill=tk.X)
        self._btn(actions,"Generate selected criminal PDF",self.generate_selected_pdf,"#2980b9").pack(anchor="w",pady=5)
        self._btn(actions,"Generate full register PDF",self.generate_full_pdf,"#27ae60").pack(anchor="w",pady=5)
        self._btn(actions,"Open statistics",lambda:self.notebook.select(self.stats_frame),"#8e44ad").pack(anchor="w",pady=5)
        self.report_status=tk.Label(
            f,text="",fg=Theme.TEXT_MUTED,bg=Theme.BG,font=Theme.F_BODY
        )
        self.report_status.pack(anchor="w",pady=12)

    def _pdf_data(self,cid):
        conn=secure_connect(ENHANCED_DB); c=conn.execute("SELECT id,first_name,last_name,alias,date_of_birth,gender,nationality,last_known_location,crimes,status,arrest_date,release_date,notes,photo_path,cnic,case_number,created_at,updated_at FROM criminals WHERE id=?",(cid,)).fetchone(); cases=conn.execute("SELECT case_number,case_title,crime_type,station,officer,status,opened_date,closed_date,notes FROM cases WHERE criminal_id=? ORDER BY id",(cid,)).fetchall(); conn.close(); return c,cases

    def _build_pdf(self,path,title,rows):
        if pdf_colors is None: raise RuntimeError("ReportLab is not installed. Run pip install -r requirements.txt")
        with secure_output_path(path) as output_path:
            doc=SimpleDocTemplate(output_path,pagesize=A4,rightMargin=15*mm,leftMargin=15*mm,topMargin=15*mm,bottomMargin=15*mm)
            styles=getSampleStyleSheet(); story=[Paragraph(title,styles["Title"]),Spacer(1,8)]
            for heading,data in rows:
                story.append(Paragraph(str(heading),styles["Heading2"]))
                if isinstance(data,list) and data and isinstance(data[0],(list,tuple)):
                    table=Table(data,repeatRows=1,colWidths=None); table.setStyle(TableStyle([("BACKGROUND",(0,0),(-1,0),pdf_colors.HexColor("#1f6feb")),("TEXTCOLOR",(0,0),(-1,0),pdf_colors.white),("GRID",(0,0),(-1,-1),.5,pdf_colors.grey),("FONTNAME",(0,0),(-1,0),"Helvetica-Bold"),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"TOP")])) ; story.append(table)
                else: story.append(Paragraph(str(data).replace("\n","<br/>"),styles["BodyText"]))
                story.append(Spacer(1,8))
            story.append(Paragraph(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | User: {self.current_user['username']}",styles["Normal"]))
            doc.build(story)

    def generate_selected_pdf(self):
        try: cid=self._selected_id()
        except Exception as e: messagebox.showerror("Report",str(e)); return
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile=f"criminal_{cid}_report.pdf")
        if not path:return
        try:
            c,cases=self._pdf_data(cid); label=f"{c[1]} {c[2]}"; details=[
                ["Field","Value"], ["Record ID",c[0]],["Full Name",label],["Alias",c[3] or ""],[national_id_label(c[6]),c[14] or ""],["Primary Case",c[15] or ""],["Date of Birth",c[4] or ""],["Gender",c[5] or ""],["Nationality",c[6] or ""],["Last Location",c[7] or ""],["Crimes",c[8] or ""],["Status",c[9] or ""],["Arrest Date",c[10] or ""],["Release Date",c[11] or ""],["Notes",c[12] or ""]]
            case_rows=[["Case No.","Title","Crime","Station","Officer","Status","Opened","Closed"]]+[list(x[:8]) for x in cases]
            self._build_pdf(path,"Criminal Record Report",[("Criminal Information",details),("Associated Cases",case_rows if len(case_rows)>1 else [["Case No."]])]); messagebox.showinfo("Report",f"PDF saved to:\n{path}")
        except Exception as e: messagebox.showerror("Report",str(e))

    def generate_full_pdf(self):
        path=filedialog.asksaveasfilename(defaultextension=".pdf",filetypes=[("PDF","*.pdf")],initialfile="criminal_register.pdf")
        if not path:return
        try:
            conn=secure_connect(ENHANCED_DB); rows=conn.execute("SELECT id,first_name,last_name,cnic,case_number,status,nationality FROM criminals ORDER BY last_name,first_name").fetchall(); conn.close()
            table=[["ID","Name","National ID","Case No.","Status","Nationality"]]+[[r[0],f"{r[1]} {r[2]}",r[3] or "",r[4] or "",r[5] or "",r[6] or ""] for r in rows]
            self._build_pdf(path,"Criminal Record Register",[("All Records",table)]); messagebox.showinfo("Report",f"PDF saved to:\n{path}")
        except Exception as e: messagebox.showerror("Report",str(e))

    def manage_users(self):
        if not self._require_admin("manage user accounts"):
            return
        win=tk.Toplevel(self.root); win.title("User Management"); win.geometry("700x480"); win.configure(bg=Theme.BG); win.grab_set()
        tree=ttk.Treeview(win,columns=("id","username","role","name","active"),show="headings")
        for c,h,w in zip(tree["columns"],["ID","Username","Role","Full Name","Active"],[50,120,90,220,70]):tree.heading(c,text=h);tree.column(c,width=w)
        tree.pack(fill=tk.BOTH,expand=True,padx=16,pady=(16,8))
        def refresh():
            tree.delete(*tree.get_children()); conn=secure_connect(POLICE_DB); rows=conn.execute("SELECT id,username,role,full_name,active FROM app_users ORDER BY username").fetchall(); conn.close(); [tree.insert("",tk.END,values=r) for r in rows]
        refresh()
        def add_user():
            if not self._require_admin("add user accounts"):
                return
            d=tk.Toplevel(win); d.title("Add User"); d.geometry("430x340"); d.configure(bg=Theme.BG); d.grab_set(); vars=[tk.StringVar(),tk.StringVar(),tk.StringVar(value="Officer"),tk.StringVar()]; labs=["Username","Password","Role","Full Name"]
            for i,(lab,var) in enumerate(zip(labs,vars)):
                tk.Label(
                    d,text=lab,font=Theme.F_BODY,bg=Theme.BG,fg=Theme.TEXT
                ).grid(row=i,column=0,padx=16,pady=9,sticky="w")
                if lab=="Role":
                    ttk.Combobox(
                        d,textvariable=var,values=["Admin","Officer"],
                        state="readonly",width=26,font=Theme.F_BODY
                    ).grid(row=i,column=1,padx=(0,16),sticky="ew")
                else:
                    tk.Entry(
                        d,textvariable=var,show="*" if lab=="Password" else "",
                        width=28,font=Theme.F_BODY,bg=Theme.INPUT,fg=Theme.TEXT,
                        relief=tk.FLAT,highlightthickness=1,
                        highlightbackground=Theme.BORDER,highlightcolor=Theme.BLUE,
                        insertbackground=Theme.TEXT
                    ).grid(row=i,column=1,padx=(0,16),sticky="ew")
            d.grid_columnconfigure(1,weight=1)
            def save():
                if not self._require_admin("add user accounts"):
                    return
                username = vars[0].get().strip()
                password = vars[1].get()
                if not valid_username(username):
                    messagebox.showerror(
                        "User",
                        "Username must be 3-32 characters and use only letters, numbers, '.', '_' or '-'.",
                        parent=d,
                    )
                    return
                issues = password_issues(password, username)
                if issues:
                    messagebox.showerror("User", "\n".join(issues), parent=d)
                    return
                conn=secure_connect(POLICE_DB)
                try: conn.execute("INSERT INTO app_users(username,password_hash,role,full_name) VALUES(?,?,?,?)",(username,hash_password(password),vars[2].get(),vars[3].get().strip())); conn.commit(); d.destroy(); refresh()
                except sqlite3.IntegrityError: messagebox.showerror("User","Username already exists.")
                finally: conn.close()
            self._btn(d, "Create user", save, "#27ae60").grid(
                row=5, column=1, padx=16, pady=18, sticky="e"
            )

        def edit_user():
            if not self._require_admin("edit user accounts"):
                return
            selected = tree.selection()
            if not selected:
                messagebox.showwarning(
                    "User Management", "Select a user to edit.", parent=win
                )
                return
            user_id, username, role, full_name, active = tree.item(
                selected[0], "values"
            )
            dialog = tk.Toplevel(win)
            dialog.title(f"Edit User — {username}")
            dialog.geometry("470x410")
            dialog.configure(bg=Theme.BG)
            dialog.transient(win)
            dialog.grab_set()

            name_var = tk.StringVar(value=full_name or "")
            role_var = tk.StringVar(value=role)
            active_var = tk.BooleanVar(value=str(active).casefold() in {"1", "true"})
            password_var = tk.StringVar()
            fields = (
                ("Username", username),
                ("Full name", name_var),
                ("Role", role_var),
                ("New password (optional)", password_var),
            )
            for index, (label, value) in enumerate(fields):
                tk.Label(
                    dialog, text=label, font=Theme.F_BODY,
                    bg=Theme.BG, fg=Theme.TEXT
                ).grid(row=index, column=0, padx=18, pady=10, sticky="w")
                if label == "Username":
                    widget = tk.Entry(
                        dialog, width=28, font=Theme.F_BODY,
                        bg=Theme.INPUT, fg=Theme.TEXT, relief=tk.FLAT,
                        state="readonly"
                    )
                    widget.configure(state="normal")
                    widget.insert(0, value)
                    widget.configure(state="readonly")
                elif label == "Role":
                    widget = ttk.Combobox(
                        dialog, textvariable=value,
                        values=("Officer", "Admin"), state="readonly",
                        width=26, font=Theme.F_BODY
                    )
                else:
                    widget = tk.Entry(
                        dialog, textvariable=value,
                        show="*" if label.startswith("New password") else "",
                        width=28, font=Theme.F_BODY,
                        bg=Theme.INPUT, fg=Theme.TEXT, relief=tk.FLAT,
                        highlightthickness=1,
                        highlightbackground=Theme.BORDER,
                        highlightcolor=Theme.BLUE,
                        insertbackground=Theme.TEXT
                    )
                widget.grid(row=index, column=1, padx=(0, 18), pady=10, sticky="ew")
            tk.Checkbutton(
                dialog, text="Account active", variable=active_var,
                font=Theme.F_BODY, bg=Theme.BG, fg=Theme.TEXT,
                activebackground=Theme.BG, selectcolor=Theme.CARD
            ).grid(row=4, column=1, padx=18, pady=8, sticky="w")
            tk.Label(
                dialog, text="Leave the password blank to keep it unchanged.",
                font=Theme.F_SMALL, bg=Theme.BG, fg=Theme.TEXT_MUTED
            ).grid(row=5, column=0, columnspan=2, padx=18, sticky="w")
            dialog.grid_columnconfigure(1, weight=1)

            def save_changes():
                if not self._require_admin("edit user accounts"):
                    return
                if username == self.current_user["username"] and (
                    role_var.get() != "Admin" or not active_var.get()
                ):
                    messagebox.showerror(
                        "User Management",
                        "You cannot remove or disable your own active Administrator access.",
                        parent=dialog
                    )
                    return
                new_password = password_var.get()
                if new_password:
                    issues = password_issues(new_password, username)
                    if issues:
                        messagebox.showerror(
                            "User Management", "\n".join(issues), parent=dialog
                        )
                        return
                conn = secure_connect(POLICE_DB)
                try:
                    conn.execute("BEGIN IMMEDIATE")
                    if role_var.get() != "Admin" or not active_var.get():
                        active_admins = conn.execute(
                            "SELECT COUNT(*) FROM app_users WHERE role='Admin' AND active=1"
                        ).fetchone()[0]
                        target_is_active_admin = conn.execute(
                            "SELECT role,active FROM app_users WHERE id=?",
                            (user_id,),
                        ).fetchone()
                        if (
                            active_admins <= 1
                            and target_is_active_admin
                            and target_is_active_admin[0] == "Admin"
                            and target_is_active_admin[1] == 1
                        ):
                            messagebox.showerror(
                                "User Management",
                                "At least one active Administrator account must remain.",
                                parent=dialog
                            )
                            return
                    if new_password:
                        conn.execute(
                            "UPDATE app_users SET full_name=?,role=?,active=?,password_hash=? WHERE id=?",
                            (
                                name_var.get().strip(), role_var.get(),
                                int(active_var.get()), hash_password(new_password),
                                user_id
                            ),
                        )
                    else:
                        conn.execute(
                            "UPDATE app_users SET full_name=?,role=?,active=? WHERE id=?",
                            (
                                name_var.get().strip(), role_var.get(),
                                int(active_var.get()), user_id
                            ),
                        )
                    conn.commit()
                except sqlite3.Error as exc:
                    messagebox.showerror(
                        "User Management", f"Could not update user:\n{exc}",
                        parent=dialog
                    )
                    return
                finally:
                    conn.close()
                if username == self.current_user["username"]:
                    self.current_user["full_name"] = name_var.get().strip()
                    self._refresh_current_user_display()
                dialog.destroy()
                refresh()

            self._btn(
                dialog, "Save changes", save_changes, "#27ae60"
            ).grid(row=6, column=1, padx=18, pady=18, sticky="e")

        button_row = tk.Frame(win, bg=Theme.BG)
        button_row.pack(fill=tk.X, padx=16, pady=(0, 16))
        self._btn(button_row, "Edit selected user", edit_user, "#2980b9").pack(
            side=tk.LEFT
        )
        self._btn(button_row, "Add user", add_user, "#27ae60").pack(
            side=tk.RIGHT
        )

    def _refresh_current_user_display(self):
        user = self.current_user
        name = user.get("full_name") or user.get("username")
        role = user.get("role", "User")
        self.header_user_label.config(
            text=f"{name}  ·  @{user.get('username')}  ·  {role}"
        )
        if hasattr(self, "dashboard_welcome_label"):
            self.dashboard_welcome_label.config(text=f"Welcome back, {name}")
        if hasattr(self, "user_dashboard_name_label"):
            self.user_dashboard_name_label.config(text=name)
        if hasattr(self, "user_dashboard_values"):
            self.user_dashboard_values["Role"].config(text=role)
        if hasattr(self, "root"):
            self.root.title(
                f"Criminal Record Management System — {role}: {name}"
            )

    def change_password(self):
        win=tk.Toplevel(self.root); win.title("Change Password"); win.geometry("430x310"); win.configure(bg=Theme.BG); win.grab_set(); old=tk.StringVar(); new=tk.StringVar(); confirm=tk.StringVar()
        for i,(lab,var) in enumerate([("Current password",old),("New password",new),("Confirm password",confirm)]):
            tk.Label(
                win,text=lab,font=Theme.F_BODY,bg=Theme.BG,fg=Theme.TEXT
            ).grid(row=i,column=0,padx=18,pady=12,sticky="w")
            tk.Entry(
                win,textvariable=var,show="*",width=28,font=Theme.F_BODY,
                bg=Theme.INPUT,fg=Theme.TEXT,relief=tk.FLAT,
                highlightthickness=1,highlightbackground=Theme.BORDER,
                highlightcolor=Theme.BLUE,insertbackground=Theme.TEXT
            ).grid(row=i,column=1,padx=(0,18),pady=12,sticky="ew")
        win.grid_columnconfigure(1,weight=1)
        def save():
            new_password = new.get()
            if new_password != confirm.get():
                messagebox.showerror("Password", "New passwords do not match.", parent=win)
                return
            conn = secure_connect(POLICE_DB)
            try:
                row = conn.execute(
                    "SELECT password_hash FROM app_users WHERE username=?",
                    (self.current_user["username"],),
                ).fetchone()
                if not row or not verify_password(old.get(), row[0]):
                    messagebox.showerror("Password", "Current password is incorrect.", parent=win)
                    return
                issues = password_issues(new_password, self.current_user["username"])
                if issues:
                    messagebox.showerror("Password", "\n".join(issues), parent=win)
                    return
                conn.execute(
                    "UPDATE app_users SET password_hash=?, must_change=0 WHERE username=?",
                    (hash_password(new_password), self.current_user["username"]),
                )
                conn.commit()
            finally:
                conn.close()
            win.destroy()
            messagebox.showinfo("Password", "Password changed successfully.")
        self._btn(win,"Save password",save,"#27ae60").grid(row=4,column=1,padx=18,pady=16,sticky="e")

    def logout(self):
        if messagebox.askyesno("Logout","Sign out of the current account?"):
            session = getattr(self, "_session", None)
            if session is not None:
                session["relaunch"] = True
                session["notice"] = ""
            try:
                self.root.quit()
            except tk.TclError:
                pass

    def delete_criminal(self):
        if not self._require_admin("permanently delete records"):
            return
        super().delete_criminal()

    def clear_all_data(self):
        if not self._require_admin("clear all records"):
            return
        super().clear_all_data()


if __name__ == "__main__":
    _open_login()
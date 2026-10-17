# Criminal Record Management System

**Final Year Project: Project Documentation**

| | |
|---|---|
| Project title | Criminal Record Management System (CRMS) |
| Version | 3.1 |
| Organization context | Balochistan Police (station-level record keeping) |
| Platform | Windows desktop application (also runs on Linux for development) |
| Language | Python 3 |
| Repository | https://github.com/kamranraheel840-wq/FYP |
| Author(s) | _fill in name and registration number_ |
| Supervisor | _fill in_ |
| Submission date | _fill in_ |

---

## Contents

1. [Introduction](#1-introduction)
2. [Objectives](#2-objectives)
3. [Scope](#3-scope)
4. [Technology and design decisions](#4-technology-and-design-decisions)
5. [System architecture](#5-system-architecture)
6. [Database design](#6-database-design)
7. [Security design](#7-security-design)
8. [Face recognition module](#8-face-recognition-module)
9. [Feature walkthrough](#9-feature-walkthrough)
10. [Installation and setup](#10-installation-and-setup)
11. [Building the Windows executable](#11-building-the-windows-executable)
12. [Testing and verification](#12-testing-and-verification)
13. [Known limitations](#13-known-limitations)
14. [Future work](#14-future-work)
15. [Troubleshooting](#15-troubleshooting)
16. [Project file structure](#16-project-file-structure)
17. [References](#17-references)
18. [Appendix A: Database schema](#appendix-a-database-schema)
19. [Appendix B: Constants and default accounts](#appendix-b-constants-and-default-accounts)

---

## 1. Introduction

### 1.1 What this system is

CRMS is a desktop application for keeping criminal records at a single police station. It stores personal details, photos, national ID numbers, case history and status information in a local database, and it provides search, filtering, analytics, PDF reporting and backup tools around that data. It also includes an optional face recognition module that runs fully offline on the same machine.

The application is written in Python with Tkinter and the CustomTkinter theme layer. There is no server, no internet dependency and no cloud component. Everything a station needs runs from one executable on one machine.

### 1.2 Background

Most small police stations in our area still maintain criminal records in physical registers. A few have moved to Excel sheets. Both approaches have the same practical problems:

- Searching for a person means going through pages or scrolling through spreadsheets.
- The same person can be entered twice with slightly different spellings, and nobody notices.
- Photographs are kept separately from written records, if they are kept at all.
- Case files and the criminal record are disconnected, so finding every case involving one person takes manual effort.
- Anybody who has access to the file cabinet has access to everything. There is no separation between an officer's access and an administrator's access.
- Nothing records who changed what.

A web-based system would solve some of this, but many stations do not have reliable internet, and centralizing sensitive records brings its own problems. We decided to stay offline and small on purpose.

### 1.3 Problem statement

Station staff need a way to record, find and update criminal records quickly, attach a photograph to each record, link cases to the right person, and produce reports without retyping data. At the same time, access to the records must be controlled: only signed-in staff should see the data, only administrators should manage user accounts or wipe the database, and each change should leave a trace.

## 2. Objectives

The project set out to:

1. Replace the paper register with a searchable digital record system that works without internet access.
2. Store each criminal record once, with a photograph, national ID (CNIC for Pakistani citizens, Foreign ID otherwise), status and case history attached.
3. Provide role-based login (Admin and Officer) with password hashing, a password policy and automatic lockout after repeated failed attempts.
4. Keep the database and photos encrypted at rest so that copying the files off the machine does not expose the data.
5. Support day-to-day paperwork: PDF reports for one record or the full register, PDF import to move records between stations, CSV statistical summaries and encrypted database backups.
6. Add an offline face recognition aid so a photo can be checked against the stored records.
7. Keep the whole thing simple enough to deploy: one executable, no installer, no server configuration.

## 3. Scope

### 3.1 What the system covers

- Criminal records with personal details, nationality, national ID, status, notes and photo.
- Multiple case records per criminal, with case number, crime type, station, officer, status and dates.
- User accounts with two roles, managed inside the application by an administrator.
- Search, filtering and a dashboard with statistics and a six-month trend chart.
- Face enrollment from a saved photo or a camera capture, and face identification from an image or a live camera window.
- PDF export and import of records, PDF analytics summaries, CSV statistics export, and encrypted database backup/restore.
- Audit logging of every insert, update, delete, import, backup and clear operation.

### 3.2 Out of scope

- No FIR workflow, court dates or legal document generation.
- No fingerprint hardware integration. The database has a `fingerprint_data` column reserved for it, but no reader is implemented.
- No network sync between stations. Data moves manually through exported PDFs and backup files.
- No mobile or web client.
- No multi-user concurrent access in the database-server sense. The app is designed for one operator using the machine at a time.

## 4. Technology and design decisions

| Component | Choice | Why |
|---|---|---|
| Language | Python 3 | Fast to develop, rich library ecosystem, department laptops already run it for the build step |
| GUI | Tkinter + CustomTkinter | Ships with Python, no browser runtime, works fine for form-based desktop tools |
| Database | SQLite (via `sqlite3`), SQLCipher when available | Zero configuration, single-file database, and SQLCipher gives page-level encryption with the same API |
| Face detection | YuNet (ONNX, OpenCV Zoo) | Small model (around 230 KB), fast on CPU, bundled with the build |
| Face embeddings | SFace (ONNX, OpenCV Zoo) | 128-dimensional embeddings with a documented cosine similarity comparison, no training needed |
| Photo handling | Pillow | Resize and format photos for the UI and for PDF embedding |
| Reports | ReportLab (write) and pypdf (read) | ReportLab generates the PDFs; pypdf reads exported PDFs back for the import feature |
| Encryption | `cryptography` (AES-GCM) | Used for photos and backup files, with DPAPI protecting the master key on Windows |
| Country list | `pycountry` | Full ISO country list for the nationality field, plus a few legacy labels for existing data |
| Packaging | PyInstaller | Produces a single Windows executable from `police_system.spec` |

A note on Tkinter: its native theming is dated, so most of the visual design lives in our own widget code (`theme.py` and `ui.py`) rather than in Tk options. That kept the toolchain simple, but it also means the interface code is more verbose than it would be with a web front end.

## 5. System architecture

### 5.1 Modules

The project is around 5,100 lines of Python across seven files. Each file has one clear responsibility:

| File | Lines (approx.) | Responsibility |
|---|---|---|
| `police_system_IT.py` | 3,884 | Entry point. Contains `init_db`, the base `CriminalDatabaseApp`, the enhanced app with tabs and dialogs, login window, CNIC validation, PDF build/read helpers and photo handling |
| `secure_storage.py` | 363 | Master key management (DPAPI on Windows), SQLCipher connection handling, one-time plaintext-to-encrypted migration, AES-GCM photo encryption, per-user file permissions, safe output paths |
| `ui.py` | 360 | Reusable widgets: themed buttons, sidebar buttons, stat cards, header builder, hover animations, global ttk styles |
| `face_engine.py` | 204 | Model download, YuNet detection, SFace embedding extraction, cosine similarity |
| `security.py` | 137 | PBKDF2 hashing and verification, password policy, account lockout, login bookkeeping (`last_login`) |
| `config.py` | 82 | Paths for data, media, models and backups; app constants; legacy database migration; directory hardening |
| `theme.py` | 61 | Color palette and font definitions used across every screen |

### 5.2 Layers

```
Tkinter / CustomTkinter interface        (police_system_IT.py, ui.py, theme.py)
        |
Feature logic: records, cases, PDFs,
analytics, user management               (police_system_IT.py)
        |
Security and storage services            (security.py, secure_storage.py)
        |
Face recognition service                 (face_engine.py)
        |
Encrypted SQLite databases + media folder + model files
```

### 5.3 Startup sequence

1. `config.ensure_directories()` creates `data/`, `media/`, `models/` and `data/backups/` if they are missing, then tightens their file permissions.
2. Any legacy `criminals.db` or `police.db` left next to the script is copied into `data/` through the secure connection layer (it is encrypted during the copy, not before).
3. On first run, `init_db()` creates the tables and adds any columns that newer versions expect. This is additive only; existing rows are untouched.
4. Existing photos in `media/` are encrypted in place, and photos referenced from outside the media folder are copied in.
5. The login window opens. After a successful sign-in, the main window is built for the account's role.
6. A 20-minute idle timer runs in the main window. If it fires, or if the user signs out, the session ends and the login window is shown again without restarting the process.

### 5.4 Roles

| Capability | Admin | Officer |
|---|---|---|
| View records, cases, analytics | Yes | Yes |
| Add / edit / delete records | Yes | Yes |
| Face enrollment and identification | Yes | Yes |
| Export and import, backup | Yes | Yes |
| Manage users (create, edit, deactivate, reset password, assign role) | Yes | No |
| Clear all data | Yes | No |

The requirement is that the administrator account used for user management must also be active. A deactivated admin account cannot manage users.

## 6. Database design

### 6.1 Two databases

The system uses two SQLite files, both inside `data/`:

- **`criminals.db`** holds the operational data: `criminals`, `cases`, `face_embeddings` and `audit_log`.
- **`police.db`** holds authentication data: `app_users`. It also carries two legacy tables (`criminal`, `officer`) that existed in earlier versions; they are kept so old installs do not lose data, but the application no longer writes to them.

Keeping users separate from records means the login layer can open its own small database without touching the main data file, and it keeps the clear line between "who can sign in" and "what is stored".

### 6.2 Main tables

**`criminals`**: one row per person. Core columns: `id`, `first_name`, `last_name`, `alias`, `date_of_birth` (YYYY-MM-DD), `gender`, `nationality`, `last_known_location`, `crimes`, `status`, `arrest_date`, `release_date`, `notes`, `photo_path`, `photo_data` (encrypted blob), `fingerprint_data` (reserved), timestamps, `cnic` (holds either a CNIC or a Foreign ID), `case_number` (primary case) and `face_embedding` (latest embedding, kept for backward compatibility).

**`cases`**: many rows per criminal. Columns: `id`, `criminal_id`, `case_number` (unique), `case_title`, `crime_type`, `station`, `officer`, `status`, `opened_date`, `closed_date`, `notes`, `created_at`. Case status is one of Open, Under Investigation, Closed or Court.

**`face_embeddings`**: one or more embeddings per criminal. Columns: `id`, `criminal_id`, `embedding` (float32 blob), `model_name`, `created_at`. Multiple embeddings per person let a record carry, for example, a webcam capture and a scanned photograph.

**`audit_log`**: `id`, `user_action` (INSERT / UPDATE / DELETE / IMPORT / BACKUP / CLEAR_ALL), `table_name`, `record_id`, `old_values`, `new_values`, `timestamp`.

**`app_users`**: `id`, `username`, `password_hash`, `role`, `full_name`, `active`, `created_at`, plus the login-security columns `failed_attempts`, `locked_until`, `must_change` and `last_login`.

The full column list for every table is in [Appendix A](#appendix-a-database-schema).

### 6.3 Schema migrations

There is no migration framework. On every start, `init_db()` runs `CREATE TABLE IF NOT EXISTS` for the tables and checks `PRAGMA table_info` before adding missing columns. The columns added over the life of the project are `criminals.cnic`, `criminals.case_number`, `criminals.face_embedding`, the whole `cases` and `face_embeddings` tables, and the four security columns on `app_users`. Every one of these steps is additive, so a database from an older build keeps working after an update.

## 7. Security design

The threat model here is modest and worth stating plainly: a single trusted operator on a Windows workstation, with the risk being someone copying the database files, the media folder or a backup off the machine. The design does not attempt to defend against malware running as the same Windows user, and it does not claim to be a hardened evidence system.

### 7.1 Passwords

- Hashes use PBKDF2-HMAC-SHA256 with a random 16-byte salt per user and 180,000 iterations, stored as `base64(salt || digest)`.
- Verification also accepts the older 120,000-iteration format so accounts created before the increase still sign in.
- Password policy: at least 8 characters, must contain a letter and a number, cannot equal the username, and cannot be one of the demo passwords (`password`, `admin123`, `officer123`, `12345678`).
- New accounts and password resets set a `must_change` flag. When the account signs in, the app refuses to continue until the password is changed.
- Demo accounts ship with known passwords (`admin` / `admin123`, `officer` / `officer123`) for evaluation only. The first sign-in forces a change.

### 7.2 Lockout

Five consecutive failed attempts lock the account for 120 seconds. The counter and the lock expiry are stored per account in `app_users`. A successful login clears the counter and writes `last_login`. Failed attempts against usernames that do not exist are not tracked, and the message shown is the same as for a wrong password, so the login screen cannot be used to discover valid usernames.

### 7.3 Sessions

After sign-in, a 20-minute idle timer is reset by keyboard and mouse activity. When it expires, the app shows a warning and returns to the login window. Signing out works the same way, and the main window is torn down so no data stays visible behind the login screen.

### 7.4 Encrypting the database

`secure_storage.py` opens databases through `sqlcipher3` when that package is available. On a fresh install with plain SQLite files, the first secure connection performs a one-time migration: it opens the plaintext file, exports it into an encrypted copy using `sqlcipher_export`, validates that the copy opens with the key, and replaces the original. Backups made by the application go through the same path, so backup files are encrypted too.

If SQLCipher is not installed, the app falls back to Python's standard `sqlite3` and everything still works, just without encryption at rest. The README explains how to install `sqlcipher3-wheels` where a compatible wheel exists.

### 7.5 Key management

The 32-byte master key is generated once with `secrets.token_bytes(32)`.

- On Windows the key is protected with DPAPI (CryptProtectData) and written to a `database.key` file under the current user's profile. Only that Windows account can unprotect it.
- On other platforms (used during development) the key is written to `~/.criminal-record-management-system/database.key` with restrictive permissions.

Losing the protected key means the encrypted databases cannot be opened. That is the intended trade-off, and it is documented for users.

### 7.6 Photos

Photos are encrypted with AES-GCM before they are written to disk, using a fresh nonce per file and the same master key. Saving a photo goes through a staged temporary path so a crash mid-write cannot leave a half-encrypted image. When a record is exported, `secure_output_path` decrypts to a temporary location for the duration of the write and cleans up afterwards, which is why exports work normally even though the stored files are encrypted.

### 7.7 File permissions and backups

`data/`, `media/` and `data/backups/` are restricted to the current user on startup. The backup function writes an encrypted copy of `criminals.db` into `data/backups/` and records a BACKUP entry in the audit log.

### 7.8 Audit trail

Every record insert, update and delete writes to `audit_log` with the affected table and record id, plus old and new values where a change is involved. Imports, backups and the clear-all operation are logged too. There is currently no in-app screen for browsing the audit log; it is queried from the database directly.

## 8. Face recognition module

This module is an identification aid. A similarity score is not proof of identity, and the report should say so wherever the feature is described.

### 8.1 Models

Two ONNX models from the OpenCV Zoo sit in `models/`:

| File | Role | Size |
|---|---|---|
| `face_detection_yunet_2023mar.onnx` | Finds faces and landmarks | ~230 KB |
| `face_recognition_sface_2021dec.onnx` | Produces 128-D face embeddings | ~38.7 MB |

Both are bundled with the PyInstaller build and copied into the app's data directory on first launch. If they are missing in a development checkout, the app downloads them automatically; if the machine is offline, the AI Setup dialog shows the manual download links.

### 8.2 Pipeline

1. **Detect.** YuNet runs on the input at a score threshold of 0.6. We lowered this from the default 0.85 because cropped, face-only images were being rejected even when the face was clearly the subject. Large images are scaled down before detection for speed.
2. **Extract.** SFace produces a 128-dimensional embedding for the aligned face. Embeddings are already L2-normalized by the model, and the code re-normalizes defensively.
3. **Store.** Each enrollment writes a row into `face_embeddings` and also updates `criminals.face_embedding` with the newest vector.
4. **Compare.** Identification computes the cosine similarity between the probe embedding and every stored embedding and returns the best match above a threshold of 0.45. All embeddings for a record are considered, so a person enrolled twice is still matched once.

### 8.3 Enrollment paths

- **Enroll saved photo**: reads the photo already attached to the selected record.
- **Enroll from camera**: opens a camera capture window; the frame is cropped around the detected face and saved.
- **Live recognition**: continuously reads frames, draws boxes around detected faces and shows the best match with its similarity score.

The face screen has a search box, a face database list showing how many embeddings each record has, and a rebuild button that recreates the index from the stored embeddings (used after migrating from an older database).

### 8.4 Practical limits

Accuracy depends heavily on image quality. Front-facing, well-lit photos match reliably in our tests; profiles, low-resolution phone photos and heavy beard/moustache changes are where the similarity score drops. The threshold of 0.45 was picked to favor avoiding false positives, which means some genuine matches are missed. This is a reasonable trade-off for an aid that is only ever supposed to narrow down candidates, and any positive match should be confirmed against the actual record photo.

## 9. Feature walkthrough

### 9.1 Login

The login window shows the app name, the username and password fields, and a notice banner when a session has just expired. Lockout messages appear inline. Accounts that still use a default password are pushed straight into the password change dialog after signing in.

### 9.2 Dashboard

The landing screen after login. Its stat cards show the total number of records, how many are wanted, how many are in custody (arrested or incarcerated) and how many records have a photo attached. Below that are quick action buttons that jump to adding a record, viewing records or the analytics tab. The header carries a live clock and the signed-in account, and the sidebar groups the main screens.

### 9.3 Add Record

The form covers first and last name, alias, date of birth, gender, nationality, national ID, last known location, crimes, status, arrest and release dates, and notes, with a photo panel on the right.

Two fields deserve their own paragraph:

- **Nationality** is a searchable list built from `pycountry`, with a few legacy labels (for example "Pakistani" alongside "Pakistan") kept so older records display correctly.
- **National ID** changes meaning based on nationality. For Pakistani citizens the label becomes CNIC and the value must match `XXXXX-XXXXXXX-X`; if the 13 digits are typed without dashes, they are normalized into the dashed format when the record is saved. For any other nationality the label becomes Foreign ID and the value is required but free-form. The validation runs on the field before the record is saved, and it also runs on imported records.

Date fields accept `YYYY-MM-DD` and are validated before saving.

### 9.4 Records

The main data table with columns for ID, name, alias, date of birth, gender, nationality, location, crimes, status, dates and notes. Features:

- Search across the visible fields, with a placeholder-style search box and a one-click clear button.
- Status filter dropdown that rebuilds the table in place.
- A detail view that opens when a row is double-clicked.
- Edit and delete for the selected record. Delete asks for confirmation and writes an audit entry.
- Export All Records to PDF and Import Records from PDF (see 9.8).

A live status summary above the table shows how many records are in each status bucket.

### 9.5 Identity & Cases

This tab handles one selected criminal at a time. It shows the identity panel, the list of cases for that person, and buttons to add, edit or delete a case. Case numbers are unique across the database, and the dialog validates the date fields before saving. This is where the "one person, many cases" relationship is actually used; the Cases table stores `criminal_id` as a foreign key.

### 9.6 Analytics

The analytics tab shows summary metrics, a status distribution chart, a top-nationalities list and a six-month trend of records added per month. Both charts are drawn with Tkinter primitives rather than an external charting library, which kept the dependency list short. The "Export CSV" button writes a formatted summary (metrics, status breakdown with percentages, top nationalities and monthly counts) with a UTF-8 BOM so Excel opens it correctly.

### 9.7 Face Recognition

Described in section 8. The screen keeps a status line, the search and index list, the three enrollment buttons, image recognition, the live recognition window and an AI Setup dialog that reports model status and can download missing files with a progress bar.

### 9.8 Reports, import and backup

- **Generate report for selected record** produces a PDF with the record's fields and its photo.
- **Generate full register PDF** produces a table of all records.
- **Import Records from PDF** reads a PDF previously exported by this app, extracts the record data and the embedded photo, validates the fields (including status and national ID), and inserts each record as a new entry. Rows that fail validation are skipped and reported rather than silently dropped.
- **Database Backup** writes an encrypted copy of the database into `data/backups/`.

The export helpers also guard against missing photos: if the attached photo file cannot be read, the record is still exported with a placeholder note instead of aborting the whole report.

### 9.9 User Dashboard

A read-only summary for the signed-in account: username, role, account status, when the account was created, last sign-in time and the access level. It also has a sign-out button, and a Change Password button that opens the same dialog as the Security menu.

### 9.10 User management (Admin only)

The Manage Users dialog lists accounts with their role, active state and last login. An active administrator can create accounts (with the password policy enforced), edit names and roles, deactivate or reactivate accounts, and reset passwords (which sets `must_change` again). Officers see the menu item disabled.

### 9.11 Menus

| Menu | Items |
|---|---|
| File | Export All Records to PDF, Import Records from PDF, Database Backup, Exit |
| Tools | Statistics (jumps to Analytics), Clear All Data (Admin only) |
| Security | Signed-in account (label), Manage Users (Admin only), Change My Password, Logout |
| Help | About |

## 10. Installation and setup

Requirements: Python 3.10 or newer with Tkinter available (the standard Windows installer includes it), and pip.

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# Linux / macOS
source .venv/bin/activate

python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

`requirements.txt` pins the runtime packages (CustomTkinter, cryptography, numpy, opencv-python, Pillow, pycountry, pypdf, ReportLab) plus PyInstaller for the build step. SQLCipher is optional and commented out in the file; install `sqlcipher3-wheels` where a compatible wheel exists if you want encrypted databases.

Run the app:

```bash
python police_system_IT.py
```

On first run the app creates `data/`, `media/`, `models/` and `data/backups/`, creates the schemas, and if the machine is online downloads the two face models into `models/`. The demo accounts are created if they do not exist.

During development the app stores its data next to the source files. The packaged executable behaves differently: it stores everything under `%LOCALAPPDATA%\CriminalRecordManagementSystem` so a per-user profile is used on each Windows account.

## 11. Building the Windows executable

The spec file bundles CustomTkinter's assets, the two ONNX models and the Python runtime into one windowed executable.

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm police_system.spec
```

Output: `dist\CriminalRecordManagementSystem.exe`. The executable is single-file and has no console window; the application icon and the face models are embedded. Databases, photos and backups are not bundled; they are created in the user's LocalAppData profile on first launch, and the bundled models are copied there as well. To give the app to another user, copy the executable and let it build its own data directory.

The repository also builds this executable automatically. `.github/workflows/windows-release.yml` runs on every push to `main`: it installs the requirements on a Windows runner, compiles the sources as a quick check, builds the spec, then creates a tag (`v<version>.<build number>`, for example `v3.1.42`) and publishes a GitHub release with the EXE attached. The tag is created from `config.APP_VERSION`, so bumping the version in `config.py` changes the tag prefix on the next build.

## 12. Testing and verification

### 12.1 Approach

Testing was manual and scenario-based, because the app is a desktop tool with very little logic that can be unit-tested in isolation. Each scenario was run against copies of the demo database in a temporary directory, never against the working data. Where a test involved the database, the file was copied first and the copy was inspected afterwards with a direct SQLite connection.

### 12.2 Environment

- Python 3.14 with the dependencies from `requirements.txt` installed in a virtual environment (`customtkinter 6.0.0`, `opencv-python 5.0.0.93`, `numpy 2.5.4`, `Pillow 13.0.0`, `pypdf 6.21.0`, `reportlab 5.0.1`, `cryptography 50.0.2`, `pycountry 26.2.16`).
- Demo data: 4 criminal records, 2 user accounts.
- Two machines were used during the project: a Linux development machine and Windows for packaging.

### 12.3 Test log

| # | Scenario | Expected | Result |
|---|---|---|---|
| 1 | Sign in with correct admin credentials | Main window opens for Admin role | Pass |
| 2 | Sign in with wrong password | Error shown, attempt counter increases | Pass |
| 3 | Five wrong passwords in a row | Account locks for 120 seconds, message shows remaining time | Pass |
| 4 | Correct password while locked | Sign-in refused until the lock expires | Pass |
| 5 | Successful sign-in after lock expiry | Counter reset, `last_login` written | Pass |
| 6 | Set password shorter than 8 characters | Rejected with policy message | Pass |
| 7 | Set password without a number / without a letter | Rejected with the specific rule | Pass |
| 8 | Sign in with a demo password | Change-password dialog forced before the app continues | Pass |
| 9 | Add a record with a Pakistani nationality and malformed CNIC | Save blocked, format hint shown | Pass |
| 10 | Add a record with a foreign nationality, empty ID | Save blocked, Foreign ID required | Pass |
| 11 | Add a record with a photo, then enroll it; then rebuild the index | Embedding row created; rebuild refreshes the record's embeddings instead of stacking duplicates | Pass |
| 12 | Enroll a record with no photo attached | Clear error message, no crash | Pass |
| 13 | Recognize a face from an image against the index | Best match shown with similarity score and record id | Pass |
| 14 | Search and status filter on the Records tab | Table filters correctly; clear button restores all rows | Pass |
| 15 | Add, edit and delete a case | Case saved, `criminal_id` link correct, list refreshes | Pass |
| 16 | Export a record whose photo file is missing | PDF still generated with a placeholder note | Pass |
| 17 | Import a PDF exported by the app | Records inserted as new entries; invalid rows skipped with a report | Pass |
| 18 | Import a record with an unknown status value | Row rejected rather than stored | Pass |
| 19 | Database backup | Encrypted copy appears in `data/backups/`, BACKUP entry in audit log | Pass |
| 20 | Idle timeout expiry (shortened timeout used for the test) | Warning shown, session ends, login screen returns | Pass |
| 21 | Sign out from the menu | Window torn down, login screen returns, no data visible | Pass |
| 22 | Officer account opens Manage Users | Menu item disabled; direct call refused | Pass |
| 23 | Compile all modules (`py_compile`) and import the app package | No syntax or import errors | Pass |
| 24 | Full application construction with all tabs | Main window builds with every tab present | Pass |

### 12.4 Notes from testing

- The lockout test (rows 3–5) was run end to end on a database copy: the fifth failure produced a 120-second lock, the correct password was refused while locked, and after expiry the counter reset and `last_login` was updated.
- The face tests used the bundled models from the OpenCV Zoo and demo photos. Enrolling from an image and from the webcam both produced usable embeddings, and a rebuild of the index refreshed the record's embedding instead of stacking duplicates.
- The PDF round trip (export then import) was checked for both a record with a photo and a record without one.
- The demo database shipped with the repository was not modified during any test.

## 13. Known limitations

These are the things we know are still not ideal, written down so they are not mistaken for oversights:

1. **Live camera loops run on the main thread.** The live recognition window and the webcam capture window pull frames in a loop tied to the UI. On a slow machine the interface can feel unresponsive while the camera window is open. A thread-based capture queue is the obvious fix and is on the list for future work.
2. **Orphaned photos.** Deleting a record or replacing its photo does not remove the old file from `media/`. The files are encrypted and access-controlled, but the folder grows over time and there is no clean-up tool yet.
3. **Face matching threshold.** 0.45 favors precision over recall. Genuine matches will occasionally fall below it. The similarity score should always be treated as a hint, not an identification.
4. **Non-Windows key storage.** The DPAPI protection for the master key is Windows-only. On Linux the key file relies on filesystem permissions (0600), which is weaker.
5. **No audit log viewer.** Audit entries are written but only readable through a SQLite client.
6. **Single operator at a time.** SQLite handles locking, but the interface assumes one person at the keyboard. Two windows editing the same record can still overwrite each other on save.
7. **PDF import expects our own export format.** A PDF from another system will not import; the reader looks for the field layout used by the exporter.
8. **No automated test suite.** Verification was manual and scenario-based.
9. **The legacy `officer` and `criminal` tables** are left in `police.db` for backward compatibility and are no longer used by the application.

## 14. Future work

If the project continues, the order we would tackle things in:

1. Move camera capture to a worker thread with a frame queue, and feed the UI from there.
2. Add a media clean-up routine (find files in `media/` with no database reference and remove them, with a preview list before deletion).
3. Build an audit log viewer for administrators with filters by date, user and table.
4. Replace `hash_password` verification of the legacy 120k format with a transparent upgrade on next successful login.
5. Add a simple sync option: export a signed, encrypted change file that another station's copy can import.
6. Fingerprint reader integration, using the existing `fingerprint_data` column.
7. Optional English/Urdu interface strings, since most station staff would use it in Urdu.
8. Code signing for the executable so Windows SmartScreen stops warning on first run.

## 15. Troubleshooting

| Symptom | Cause and fix |
|---|---|
| "Cannot open encrypted database; its per-user key may be unavailable" | The key file is missing or belongs to another user profile. Restore the `database.key` from the same profile, or the data cannot be recovered. |
| Face recognition says models are missing | The machine is offline on first run. Use the AI Setup dialog or download the two ONNX files manually into `models/`. |
| Camera capture window does not open | No camera detected, or another application holds the device. Close other camera apps and retry. |
| PDF import imports nothing | The PDF was not exported by this app, or the fields do not match the expected layout. Check the status report shown after the import. |
| App opens and immediately asks for a password change | The account is still using a default password. Set a new one that follows the policy. |
| Executable closes with no window | Check `%LOCALAPPDATA%\CriminalRecordManagementSystem`; the app writes its data there. Run the source version from a terminal to see the error text. |
| Interface animations feel slow | Set the environment variable `CRM_REDUCED_MOTION=1` before launching, or enable the reduced-motion accessibility setting in Windows. |

## 16. Project file structure

```
FYP/
├── police_system_IT.py         main application
├── config.py                   paths, constants, legacy DB migration
├── security.py                 hashing, password policy, lockout
├── secure_storage.py           key management, SQLCipher, AES-GCM photos
├── face_engine.py              YuNet + SFace wrapper
├── ui.py                       reusable themed widgets
├── theme.py                    color palette and fonts
├── modern_theme.json           palette reference used while styling
├── police_system.spec          PyInstaller build definition
├── requirements.txt
├── ruff.toml                   linter configuration (pyflakes + syntax rules)
├── README.md
├── DOCUMENTATION.md            this document
├── .github/
│   └── workflows/
│       └── windows-release.yml builds the EXE, tags and releases on every push
├── assets/
│   ├── icon.ico                application icon (EXE, title bars)
│   └── icon.png                icon used on non-Windows platforms
├── data/
│   ├── criminals.db            encrypted records database (created/encrypted on first run)
│   ├── police.db               encrypted auth database
│   └── backups/                encrypted database backups
├── media/                      encrypted record photos
└── models/
    ├── face_detection_yunet_2023mar.onnx
    ├── face_recognition_sface_2021dec.onnx
    └── README.md
```

## 17. References

1. OpenCV Zoo: YuNet face detection model. https://github.com/opencv/opencv_zoo/tree/main/models/face_detection_yunet
2. OpenCV Zoo: SFace face recognition model. https://github.com/opencv/opencv_zoo/tree/main/models/face_recognition_sface
3. OpenCV: Face recognition with YuNet and SFace. https://docs.opencv.org/4.x/d0/dd4/tutorial_dnn_face.html
4. CustomTkinter documentation. https://customtkinter.tomschimansky.com/
5. SQLCipher design and API documentation. https://www.zetetic.net/sqlcipher/
6. Python documentation: `hashlib.pbkdf2_hmac`. https://docs.python.org/3/library/hashlib.html
7. Microsoft: DPAPI (CryptProtectData). https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata
8. ReportLab user guide. https://docs.reportlab.com/
9. pypdf documentation. https://pypdf.readthedocs.io/
10. PyInstaller documentation. https://pyinstaller.org/

---

## Appendix A: Database schema

The schemas below match the current build. Types are SQLite's declared types; dates are stored as `TEXT` in `YYYY-MM-DD` and timestamps as `TEXT`.

### `data/criminals.db`

**criminals**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | primary key |
| first_name | TEXT | |
| last_name | TEXT | |
| alias | TEXT | |
| date_of_birth | TEXT | YYYY-MM-DD |
| gender | TEXT | |
| nationality | TEXT | ISO country name or legacy label |
| last_known_location | TEXT | |
| crimes | TEXT | free text list |
| status | TEXT | Wanted / Arrested / Incarcerated / Released / Deceased |
| arrest_date | TEXT | YYYY-MM-DD |
| release_date | TEXT | YYYY-MM-DD |
| notes | TEXT | |
| photo_path | TEXT | encrypted media path |
| photo_data | BLOB | encrypted photo bytes |
| fingerprint_data | BLOB | reserved, currently unused |
| created_at | TEXT | |
| updated_at | TEXT | |
| cnic | TEXT | CNIC or Foreign ID |
| case_number | TEXT | primary case number |
| face_embedding | BLOB | float32, latest embedding |

**cases**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | primary key |
| criminal_id | INTEGER | references criminals.id |
| case_number | TEXT | unique |
| case_title | TEXT | |
| crime_type | TEXT | |
| station | TEXT | |
| officer | TEXT | |
| status | TEXT | Open / Under Investigation / Closed / Court |
| opened_date | TEXT | YYYY-MM-DD |
| closed_date | TEXT | YYYY-MM-DD |
| notes | TEXT | |
| created_at | TEXT | |

**face_embeddings**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | primary key |
| criminal_id | INTEGER | references criminals.id |
| embedding | BLOB | float32 vector |
| model_name | TEXT | "SFace" |
| created_at | TEXT | |

**audit_log**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | primary key |
| user_action | TEXT | INSERT / UPDATE / DELETE / IMPORT / BACKUP / CLEAR_ALL |
| table_name | TEXT | |
| record_id | INTEGER | |
| old_values | TEXT | |
| new_values | TEXT | |
| timestamp | TEXT | |

### `data/police.db`

**app_users**

| Column | Type | Notes |
|---|---|---|
| id | INTEGER | primary key |
| username | TEXT | 3–32 chars, letters/digits/`.`/`_`/`-` |
| password_hash | TEXT | base64(salt + PBKDF2 digest) |
| role | TEXT | Admin / Officer |
| full_name | TEXT | |
| active | INTEGER | 0/1 |
| created_at | TEXT | |
| failed_attempts | INTEGER | consecutive failures |
| locked_until | REAL | Unix timestamp, 0 when not locked |
| must_change | INTEGER | 0/1 |
| last_login | TEXT | UTC timestamp |

**Legacy tables (kept for old installs, not used by the current code):** `criminal` (id, name, cnic, crime, status) and `officer` (id, username, password).

---

## Appendix B: Constants and default accounts

| Constant | Value |
|---|---|
| App version | 3.1 |
| Idle timeout | 20 minutes |
| Max login attempts | 5 |
| Lockout duration | 120 seconds |
| Minimum password length | 8 characters |
| PBKDF2 iterations | 180,000 (legacy 120,000 accepted) |
| Face match threshold | 0.45 cosine similarity |
| YuNet detection score threshold | 0.6 |
| Username pattern | `^[A-Za-z0-9._-]{3,32}$` |
| CNIC pattern | `\d{5}-\d{7}-\d` |
| Record statuses | Wanted, Arrested, Incarcerated, Released, Deceased |
| Case statuses | Open, Under Investigation, Closed, Court |
| Reduced motion | `CRM_REDUCED_MOTION=1` |

**Default accounts (evaluation only; password change is forced at first sign-in):**

| Username | Password | Role |
|---|---|---|
| admin | admin123 | Admin |
| officer | officer123 | Officer |

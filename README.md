# Criminal Record Management System — Enhanced FYP

Python/Tkinter desktop application for criminal record management with SQLite, secure officer/admin login, case management, PDF reports, and an optional local face-recognition pipeline.

## Technology stack
- Python
- Tkinter
- SQLite; SQLCipher is optional and the app automatically falls back to standard SQLite when unavailable
- OpenCV
- YuNet face detection (ONNX)
- SFace face embeddings (ONNX)
- Pillow and pycountry (complete ISO country list)
- ReportLab and pypdf

## Main features
1. Secure login with Admin and Officer roles
2. Active-administrator-only user creation, account editing, and password change
3. Required nationality and national ID: Pakistani citizens must provide a CNIC in `XXXXX-XXXXXXX-X` format; international records require a Foreign ID. Nationality choices include ISO-listed countries and legacy nationality labels.
4. Criminal CRUD, photos, search, filtering, status and six-month trend analytics with CSV summary export, PDF record export/import and backup
5. Case numbers and a separate multi-case management table
6. PDF reports for one criminal or the full register, plus app-exported record PDFs with embedded photos that can be imported again
7. Audit logging
8. Face enrollment and face identification from an image or webcam
9. Live face recognition window
10. Local/offline AI inference; no cloud API is required
11. Dedicated User Dashboard showing the signed-in account, role, status, and sign-in details, with sign-out controls available on the dashboard and sidebar

## Demo login
- Admin: `admin` / `admin123`
- Officer: `officer` / `officer123`

Change these passwords after first login. Passwords created by the application are stored using PBKDF2-HMAC-SHA256 with a random salt.

## Installation
Create and activate a virtual environment, then run:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

The project is designed to work with SQLCipher when available, but it will automatically fall back to the standard SQLite library if the optional SQLCipher package is not installed. To enable SQLCipher where a compatible wheel is available, install it separately with `python -m pip install sqlcipher3-wheels`.

Tkinter and SQLite are included with standard Windows Python installations and are not installed through `requirements.txt`.

## Face AI models
Face recognition uses two ONNX models placed in `models/`:

- `face_detection_yunet_2023mar.onnx` — YuNet face detector
- `face_recognition_sface_2021dec.onnx` — SFace face embedding model

Both are downloaded **automatically on first use** from the OpenCV Zoo. If the machine is offline, download them manually from the URLs shown in the app's **AI Setup** button (also listed in `models/README.md`) and place them in `models/`.

Source: https://github.com/opencv/opencv_zoo

## Run

```bash
python police_system_IT.py
```

## Build a Windows executable
On Windows, install the requirements, then build the standalone executable:

```powershell
python -m pip install -r requirements.txt
python -m PyInstaller --clean --noconfirm police_system.spec
```

The executable is created at `dist\CriminalRecordManagementSystem.exe`. Send that file to the other Windows user; the databases and photos are not bundled. Each Windows account stores its own app data under `%LOCALAPPDATA%\CriminalRecordManagementSystem`. The face-recognition ONNX models are bundled and copied into that profile on first launch. The recipient should change the demo admin password after signing in.

## Interface and accessibility
The desktop interface uses a dark navigation rail and secure-session header with a responsive records workspace, dashboard metrics, and shared table, form, and button styling. Login, identity and case management, face recognition, reports, user administration, and record dialogs follow the same design system. Hover and dashboard card transitions are intentionally brief. To disable motion effects, set `CRM_REDUCED_MOTION=1` before launching; the application also follows the Windows client-area animation accessibility setting when available.

## Database migration
The first launch automatically adds the following fields/tables without deleting existing records:

- `criminals.cnic`
- `criminals.case_number`
- `criminals.face_embedding`
- `cases`
- `face_embeddings`
- `police.db -> app_users`

## Protecting local data
On first launch, existing SQLite databases are validated and migrated to SQLCipher without exporting plaintext database copies to disk. Database backups made by the application are also SQLCipher-encrypted. Existing photos in `media/` are encrypted in place; photos referenced outside that folder are copied into managed encrypted storage and the record is updated to use that copy. The original external photo files are intentionally left untouched and must be secured or removed separately by their owner.

The database key is protected by Windows DPAPI for the current Windows user and stored under that user's LocalAppData profile. The databases cannot be opened from another Windows account, and losing the profile-protected key makes the encrypted data unrecoverable. Application data, media, and backup directories are restricted to the current Windows user. PDF exports (including embedded record data and photos) remain readable documents and are protected with current-user file permissions; store and share them accordingly. The Records screen can import PDFs exported by this app; imported records are added as new entries.

Enable BitLocker or Windows Device Encryption for the drive containing the application and user profile to protect offline data and filesystem remnants. The application cannot enable device encryption itself. Do not use the same Windows account for multiple operators if they must be isolated from each other; application roles share the account's local file access.

## Important academic note
Face recognition is implemented as an identification aid. A similarity match should not be treated as proof that a person committed a crime. Use representative, consented test images for demonstrations and document the threshold and limitations in the FYP report.

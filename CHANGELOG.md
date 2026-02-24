# Changelog

All notable changes to GSpreadManager will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2026-02-22

### Changed
- **BREAKING:** Migrated from deprecated `oauth2client` to `google-auth` library
  - `oauth2client` has been deprecated by Google since 2017
  - Replaced `oauth2client.service_account.ServiceAccountCredentials` with `google.oauth2.service_account.Credentials`
  - Updated dependency from `oauth2client>=4.0` to `google-auth>=2.0`

### Migration Guide

**For most users:** The change is transparent. The API remains the same:

```python
from gspreadmanager import GoogleSheetConector

# This still works exactly as before
conector = GoogleSheetConector(
    doc_name='My Sheet',
    json_google_file='credentials.json'
)
```

**For advanced users** who may have been using internal authentication methods:

**Before (v0.1.x):**
```python
from oauth2client.service_account import ServiceAccountCredentials
scope = ['https://spreadsheets.google.com/feeds', 
         'https://www.googleapis.com/auth/drive']
creds = ServiceAccountCredentials.from_json_keyfile_name('creds.json', scope)
```

**After (v0.2.0):**
```python
from google.oauth2 import service_account
scope = ['https://spreadsheets.google.com/feeds',
         'https://www.googleapis.com/auth/drive']
creds = service_account.Credentials.from_service_account_file(
    'creds.json',
    scopes=scope
)
```

**Why this change?**
- `oauth2client` was deprecated in 2017 and is no longer maintained
- `google-auth` is the official, actively maintained Google authentication library
- Better security, performance, and future compatibility
- Aligns with Google's recommended authentication practices

**Compatibility:**
- Python 3.7+ (no change)
- All public APIs remain unchanged
- Service account JSON file format unchanged
- No code changes required for standard usage

### Fixed
- Future-proofed authentication against `oauth2client` deprecation warnings

## [0.1.5] - Previous Release
- Stable release with `oauth2client` dependency

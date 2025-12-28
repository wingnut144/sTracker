# File Checklist for GitHub Upload

## Root Directory Files (7 files)

- [ ] `.gitignore` - Prevents committing database files and sensitive data
- [ ] `README.md` - Main project documentation
- [ ] `app.py` - Flask application (main backend)
- [ ] `requirements.txt` - Python dependencies
- [ ] `Dockerfile` - Docker container configuration
- [ ] `docker-compose.yml` - Docker Compose configuration
- [ ] `GITHUB_SETUP.md` - Instructions for GitHub setup (optional)

## templates/ Directory (2 files)

- [ ] `templates/login.html` - Login and registration page
- [ ] `templates/calendar.html` - Main calendar interface

## Total: 9 essential files

## File Sizes (approximate)

- `.gitignore`: ~500 bytes
- `README.md`: ~6.5 KB
- `app.py`: ~8.7 KB
- `requirements.txt`: ~50 bytes
- `Dockerfile`: ~200 bytes
- `docker-compose.yml`: ~200 bytes
- `templates/login.html`: ~8 KB
- `templates/calendar.html`: ~35 KB
- `GITHUB_SETUP.md`: ~3 KB (optional)

**Total size: ~62 KB** (very small, fast upload)

## Directory Structure to Maintain

```
your-repo-name/
├── .gitignore
├── README.md
├── GITHUB_SETUP.md (optional)
├── app.py
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── templates/
    ├── login.html
    └── calendar.html
```

## Quick Verification

After uploading to GitHub, your repository should show:
- 7-8 files in the root directory
- 1 subdirectory: `templates/`
- 2 files in the `templates/` directory
- Repository should be marked as **Private**
- No `.db`, `.sqlite`, or database files visible

## Files That Should NOT Be Uploaded

The `.gitignore` will prevent these from being committed:

- ❌ `*.db` - Database files
- ❌ `*.sqlite` - SQLite databases
- ❌ `.env` - Environment variables
- ❌ `__pycache__/` - Python cache
- ❌ `data/` - Data directory

## Next Step

Download the `intimate-moments.tar.gz` file which contains all files in the correct structure, or upload files individually following this checklist.

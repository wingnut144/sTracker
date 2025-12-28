# GitHub Upload Instructions

## Files to Upload

Your repository should have the following structure:

```
intimate-moments/
├── .gitignore              # Prevents sensitive files from being committed
├── README.md               # Project documentation
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker container configuration
├── docker-compose.yml      # Docker Compose setup
└── templates/
    ├── login.html          # Login/register page
    └── calendar.html       # Main calendar interface
```

## Quick Upload to GitHub

### Option 1: Using GitHub Web Interface

1. Go to github.com and create a new repository named "intimate-moments" (or your preferred name)
2. Choose **Private** repository (IMPORTANT for privacy!)
3. Do NOT initialize with README (we already have one)
4. After creating, you'll see upload options
5. Upload all the files maintaining the directory structure

### Option 2: Using Git Command Line

```bash
# Navigate to the project directory
cd intimate-moments

# Initialize git repository
git init

# Add all files
git add .

# Create initial commit
git commit -m "Initial commit: Intimate Moments tracker"

# Add GitHub remote (replace with your repo URL)
git remote add origin https://github.com/yourusername/intimate-moments.git

# Push to GitHub
git branch -M main
git push -u origin main
```

### Option 3: Using GitHub CLI

```bash
# Navigate to the project directory
cd intimate-moments

# Initialize and create repo in one command
gh repo create intimate-moments --private --source=. --remote=origin --push
```

## Important Privacy Notes

1. **Always use a PRIVATE repository** - this is personal/sensitive data
2. The `.gitignore` file will prevent your database files from being committed
3. Never commit `.env` files with secrets
4. Consider adding a `LICENSE` file if you plan to share (or keep fully private)

## After Upload

Once uploaded to GitHub, you can:

1. Clone to your server:
   ```bash
   git clone https://github.com/yourusername/intimate-moments.git
   cd intimate-moments
   docker-compose up -d
   ```

2. Set up automatic deployments using GitHub Actions (optional)

3. Use git for version control as you make changes:
   ```bash
   git add .
   git commit -m "Description of changes"
   git push
   ```

## Recommended Repository Settings

In your GitHub repository settings:

1. **General**:
   - Keep repository private
   - Enable "Discussions" if you want to track ideas
   
2. **Branches**:
   - Set `main` as default branch
   - Consider requiring pull requests for changes (if working with partner)

3. **Secrets** (for GitHub Actions, if you add CI/CD):
   - Add `SECRET_KEY` environment variable
   - Add any other sensitive configuration

## Next Steps

After uploading to GitHub:

1. Clone the repository to your DigitalOcean server
2. Set up environment variables
3. Configure Caddy reverse proxy
4. Run with Docker Compose
5. Access via your domain (e.g., intimate.yourdomain.com)

---

**Remember**: Keep this repository PRIVATE. This contains personal tracking software.

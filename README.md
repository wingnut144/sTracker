# Intimate Moments - Private Relationship Tracker

A sophisticated, private web application for tracking intimate encounters in relationships. Built with Flask and featuring a beautiful, elegant calendar interface.

## Features

- 📅 **Calendar View**: Elegant calendar interface showing encounters at a glance
- 🔒 **Private & Secure**: Password-protected accounts with encrypted storage
- 📝 **Detailed Tracking**: Log position, duration, rating, and personal notes
- 💬 **Comments System**: Add reflections and feedback on encounters (private to you or shareable with partner)
- 📊 **Statistics**: Track frequency, ratings, and patterns over time
- 🎨 **Beautiful UI**: Refined, tasteful design with smooth animations
- 📱 **Responsive**: Works on desktop, tablet, and mobile devices

## Privacy Notice

This application is designed for **private personal use** or **couples tracking**. All data is stored locally in your database. This is NOT a social networking platform.

### Important Privacy Considerations:

- Keep your database file secure
- Use strong passwords
- Consider encryption for the database file at rest
- Only share access credentials with trusted partners
- Never deploy this publicly without proper security measures
- The commenting feature is designed for personal reflection or private partner communication

## Quick Start

### Option 1: Docker (Recommended)

```bash
# Clone or download the application
cd intimate-moments

# Build and run with Docker Compose
docker-compose up -d

# Access the application at http://localhost:5000
```

### Option 2: Local Python

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py

# Access the application at http://localhost:5000
```

## Usage

### First Time Setup

1. Navigate to `http://localhost:5000`
2. Click "Register" to create your account
3. Choose a strong username and password
4. You're ready to start tracking!

### Adding an Encounter

1. Click the "+ Add Encounter" button in the calendar header
2. Select the date and time
3. Choose the position from the visual grid
4. Add optional details: duration, rating, notes
5. Click "Add Encounter" to save

### Viewing and Commenting

1. Click on any day with encounters on the calendar
2. View the full details of the encounter
3. Add comments, ratings, and suggestions in the comments section
4. Comments are private to your account (or shareable with partner accounts if you choose)

### Statistics

The stats bar at the top shows:
- Total number of encounters
- Encounters this month
- Average rating across all encounters

## Database

The application uses SQLite by default, creating a file called `intimate_tracker.db` in the application directory.

### Database Schema

- **Users**: Account information and authentication
- **Encounters**: Date, time, position, duration, rating, notes
- **Comments**: Feedback, ratings, and suggestions on encounters

## Customization

### Adding New Positions

Edit the `POSITIONS` dictionary in `app.py`:

```python
POSITIONS = {
    'your_position': {'icon': '🔥', 'name': 'Your Position'},
    # ... other positions
}
```

### Styling

All CSS is embedded in the HTML templates:
- `templates/login.html` - Login/register page styling
- `templates/calendar.html` - Main calendar interface styling

Modify the `:root` CSS variables to change the color scheme:

```css
:root {
    --primary: #d4a5a5;     /* Main brand color */
    --secondary: #9c7a7a;   /* Secondary brand color */
    --accent: #c98686;      /* Accent color */
    --bg: #faf8f6;          /* Background */
    --surface: #ffffff;     /* Card/surface color */
    --text: #4a3838;        /* Primary text */
    --text-light: #8b7373;  /* Secondary text */
}
```

## Security Recommendations

For production deployment:

1. **Environment Variables**: Store secret keys in environment variables
   ```python
   app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', os.urandom(24))
   ```

2. **HTTPS**: Always use HTTPS in production (use Caddy/nginx as reverse proxy)

3. **Database Encryption**: Consider encrypting the database file at rest

4. **Strong Passwords**: Enforce strong password requirements

5. **Session Security**: Configure secure session cookies

6. **Rate Limiting**: Add rate limiting to prevent brute force attacks

7. **Backups**: Regularly backup your database file

## Deployment with Caddy (Recommended for you)

Create a `Caddyfile`:

```
intimate.yourdomain.com {
    reverse_proxy localhost:5000
    
    # Enable HSTS
    header Strict-Transport-Security "max-age=31536000;"
    
    # Additional security headers
    header X-Content-Type-Options "nosniff"
    header X-Frame-Options "DENY"
}
```

Update your `docker-compose.yml` to work with Caddy:

```yaml
version: '3.8'

services:
  web:
    build: .
    ports:
      - "127.0.0.1:5000:5000"  # Only expose to localhost
    volumes:
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
      - SECRET_KEY=${SECRET_KEY}
    restart: unless-stopped
    networks:
      - caddy_network

networks:
  caddy_network:
    external: true
```

## Technical Stack

- **Backend**: Flask 3.0 (Python)
- **Database**: SQLAlchemy with SQLite
- **Frontend**: Vanilla JavaScript, Custom CSS
- **Typography**: Playfair Display & Cormorant (Google Fonts)
- **Authentication**: Werkzeug password hashing

## File Structure

```
intimate-moments/
├── app.py                  # Main Flask application
├── requirements.txt        # Python dependencies
├── Dockerfile             # Docker configuration
├── docker-compose.yml     # Docker Compose configuration
├── templates/
│   ├── login.html        # Login/register page
│   └── calendar.html     # Main calendar interface
└── README.md             # This file
```

## Future Enhancements

Potential features to add:

- Export data to CSV/PDF
- Photo attachments
- Location tracking
- Mood tracking
- Partner synchronization
- Mobile app
- End-to-end encryption
- Biometric authentication

## Support

This is a personal project. For questions or issues, refer to the code comments or Flask documentation.

## License

This is a personal application. Use responsibly and privately.

## Disclaimer

This application is designed for consenting adults in private relationships. Always respect privacy, consent, and local laws. The developers are not responsible for misuse of this software.

---

**Remember**: This is a private tool. Keep your data secure and only share access with trusted partners.

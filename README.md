# ProspectPulse Discord Bot

Automated community management, leveling, and market intelligence for the ProspectPulse platform.

## Features
- **XP & Leveling**: Engagement-based XP system with automated role rewards ("The Diamond" at Level 50).
- **Admin Tools**: Professional moderation commands including `!purge` for bulk deletion and `!whois` for user intelligence.
- **Security**: Automated "Link Guard" to prevent unauthorized Discord invite poaching.
- **Support Hub**: Integrated ticket system with persistent numbering.
- **Market Intelligence**: Automated reaction logic for pricing polls and sentiment analysis.
- **Cloud Ready**: Configured for 24/7 hosting with persistent data volumes.

## Hosting (Railway.app)
1. Link this repository to a Railway project.
2. Add the following Variables:
   - `DISCORD_BOT_TOKEN`
   - `GUILD_ID`
   - `DATA_DIR` (set to `/app/data`)
3. Add a **Volume** mounted at `/app/data` to persist XP and ticket data.

## Deployment
The bot uses a `Procfile` for process management on cloud workers.
`worker: python run_bot.py`

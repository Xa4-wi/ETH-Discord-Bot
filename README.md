# ETH Discord Bot

## Running the bot securely

Never paste the Discord bot token into source code, configuration committed to Git, a command-line argument, or a chat message. `bot.py` reads it only from the `DISCORD_TOKEN` environment variable.

From the repository directory, use the provided PowerShell launcher on Windows or macOS:

```powershell
./start-bot.ps1
```

The launcher prompts for the token with masked input, runs the bot, and removes `DISCORD_TOKEN` when the bot exits, crashes, or is stopped with Ctrl+C.

If script execution is disabled on Windows, run the launcher for the current session without changing the system policy:

```powershell
powershell -ExecutionPolicy Bypass -File ./start-bot.ps1
```

Do not save the token in the launcher. Local `.env` files are ignored by Git as an additional safeguard, but this project does not require one.

## Website

The temporary ETH Battlecode website used for Discord application verification is located in `/docs`.

GitHub Pages can publish it using:

Settings → Pages → Deploy from a branch → main → /docs

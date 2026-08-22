# ETH Discord Bot

## Running the bot securely

Never paste the Discord bot token into source code, configuration committed to Git, a command-line argument, or a chat message. `main.py` reads it only from the `DISCORD_TOKEN` environment variable.

Install the bot dependencies once in the active Python environment:

```powershell
python -m pip install -r requirements.txt
```

From the repository directory, use the provided PowerShell launcher on Windows or macOS:

```powershell
./scripts/start-bot.ps1
```

The launcher prompts for the token with masked input, runs the bot, and removes `DISCORD_TOKEN` when the bot exits, crashes, or is stopped with Ctrl+C.

If script execution is disabled on Windows, run the launcher for the current session without changing the system policy:

```powershell
powershell -ExecutionPolicy Bypass -File ./scripts/start-bot.ps1
```

Do not save the token in the launcher. Local `.env` files are ignored by Git as an additional safeguard, but this project does not require one.

## Cody message style

Cody speaks as a concise network/interface AI. Traditional user-facing embeds should use `cody_embed` from `cody/shared/components.py` so titles, footer text, and colors remain consistent. Rich interfaces such as the welcome message use Discord Components V2 layouts from `cody/features/welcome/views.py`.

| Message type | Color | Intended use |
| --- | --- | --- |
| System | Gold `#E8A13C` | Welcome and general information |
| Success | Green `#7BD389` | Completed actions and healthy status |
| Warning | Rust `#D8A14A` | Deadlines and recoverable issues |
| Error | Dark rust `#8C3F22` | Invalid actions and failures |
| Umbral | Deep green `#244D3B` | Umbral rank messages |
| Midlevels | Amber-gray `#8F8066` | Midlevel rank messages |
| Citadels | Gold `#F1C75B` | Citadel rank messages |

Prefer short interface-style titles such as `ARRIVAL REGISTERED`, `TEAM REGISTERED`, `RANK UPDATED`, and `SYSTEM NOTICE`. Keep functional text clear and restrained, with occasional in-world flavor.

### Testing Discord messages

Administrators can run `/test_welcome` inside the server to send the real welcome card using their own member profile. The command invokes the same `send_welcome_message` function as the member-join event, so the test and production behavior stay identical. Its status response is visible only to the administrator. Welcome cards are generated in memory and are not stored on disk.

## Repository structure

- `main.py` is the only executable entry point.
- `cody/bot.py` configures the Discord client and loads active extensions.
- `cody/config.py` owns environment configuration and channel IDs.
- `cody/features/` separates Discord triggers, services, views, and renderers by feature.
- `cody/shared/` contains the palette, reusable components, permissions, errors, and logging.
- `assets/` contains runtime branding, fonts, and welcome artwork.
- `content/` contains structured lore and rank content.
- `tests/` mirrors the feature packages.
- `reference/` contains internal material that Cody does not load at runtime.
- `scripts/` contains local developer utilities.
- `docs/` contains only the static GitHub Pages website.

Runtime artwork uses descriptive, role-based names:

- `assets/branding/cody-icon.png` — Cody's master icon.
- `assets/branding/cody-banner.png` — current master Battlecode banner.
- `assets/welcome/umbral-background.png` — background consumed by the welcome renderer.
- `assets/fonts/play-display.ttf` — display/body typeface.
- `assets/fonts/share-tech-system.ttf` — system-interface typeface.
- `docs/assets/cody-icon.png` and `docs/assets/cody-banner.png` — website-only copies.
- `reference/game-design/cody-banner-original.png` — retained original concept banner.

Run the automated checks from the repository root with:

```powershell
python -m unittest discover
```

## Website

The temporary ETH Battlecode website used for Discord application verification is located in `/docs`.

GitHub Pages can publish it using:

Settings → Pages → Deploy from a branch → main → /docs

# PT88B88_Bot
Telegram username: [@PT88_B88_Bot](https://t.me/PT88_B88_Bot).

Three persistent buttons: **Clean Text**, **Word Counter**, **Case Converter**.
Choose a tool and send text. The selected tool stays active until changed or reset.
Results too long for a Telegram message are returned as a UTF-8 text file.
Works without AI keys, a database, paid APIs or external redirects.

## Run
Use Python 3.12. Install `pip install -r requirements.txt`, configure the `BOT_TOKEN`
environment variable using the token for @PT88_B88_Bot from BotFather, then run
`python bot.py`. The example environment file is documentation only; it is not loaded automatically.
Never commit your actual token.

## Hosting
Deploy the included Dockerfile as an always-running background worker. Set BOT_TOKEN
in your host's secret environment settings. This is a polling bot, with no HTTP port.
Run exactly one instance with this token; stop any older deployment to avoid polling conflicts.
A sleeping/free web service is unsuitable for reliable polling.

Name, About (short description), full description and commands are configured in bot.py
and applied at startup. Temporary profile-update network errors are retried without
blocking the bot indefinitely. Check the profile after deployment; a rejected setting
must be corrected in BotFather. The token must belong to the expected username.

## Before advertising
Add a profile photo in BotFather. Test /start and all three buttons on mobile and
desktop with ordinary text, emoji and long text. Check both About and description.
Keep the advertised service consistent with its real features. No implementation or
bot category guarantees approval or a faster review. Telegram requires functioning,
complete destinations and matching ad content: https://ads.telegram.org/guidelines

## Privacy
Text is processed in memory and is not persisted or logged by this application.
Only the selected tool is retained in memory. Telegram retains chat messages according
to its own policies. The /privacy command explains this to users.

## Verification
`python -m unittest discover -s tests -v`

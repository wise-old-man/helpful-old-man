# HOM

The Helpful Old Man!

A discord bot used in the Wise Old Man Discord server for facilitating support tickets.

## Contributing

Commands shown here are unix compatible and may need to be altered for Windows users.

Create a new virtual environment and activate it

```bash
$ python -m venv .venv
$ source ./.venv/bin/activate
```

Install dependencies

```bash
$ pip install -r requirements.dev.txt
```

Copy the example `.env` file

```bash
$ cp .example.env .env
```

Update the values in `.env` for your development bot

Ensure the bot has the proper permissions and intents (all)

Run the bot

```bash
$ python -m hom
```

Once the bot is running, make sure to run the `!sync` command in your dev server.
This syncs the bots application commands with Discord.

## GitHub Issue Command

The bot can expose a moderator-only slash command for creating issues:

```text
/github create repository:<repo> title:<title> body:<body> image:<optional attachment>
```

It also adds a message-only right-click action:

```text
Apps > Create GitHub Issue
```

That context-menu flow opens a modal with a prefilled title of
`UserDisplayName - Suggestion` and a body that starts with the Discord message
link, followed by the message content so a moderator can edit it before
submitting. The modal starts with a required repository dropdown and also
includes an optional attachment upload field.

To enable it, set these optional values in `.env`:

```bash
HOM_GITHUB_REPOSITORIES=wise-old-man/wise-old-man,wise-old-man/wiseoldman-discord-bot,wise-old-man/wiseoldman-runelite-plugin,wise-old-man/helpful-old-man
HOM_GITHUB_APP_ID=1234567
HOM_GITHUB_PRIVATE_KEY_PATH=.secrets/hom-github-app.pem
```

If `HOM_GITHUB_REPOSITORIES` is blank, the GitHub issue commands stay disabled and
the bot will prompt you to configure it instead of falling back to defaults.

Create a private GitHub App for the repos listed in `HOM_GITHUB_REPOSITORIES`,
disable webhooks, grant repository `Issues: Read and write`, generate a private
key, and install the app on the target repos. The bot resolves the installation
automatically per repository, so you do not need to store an installation ID in
`.env`. Keep the PEM file out of git and mount it into Docker at runtime instead
of copying it into the image.

If an image attachment is supplied, the bot adds the Discord attachment URL to the
issue body and renders it inline when GitHub can display it.

## Contributing with Docker

You can also run the bot inside docker with hot reloading. It is still
recommended to have have python and the bot's dependencies installed for
compatibility with your linter.

Still make sure to copy the `.env` file and that your discord bot application
has proper perms in the developer dashboard.

If `HOM_BASE_API_URL` is set to `http://localhost:5000`, the bot will
automatically use `host.docker.internal` when it is running inside Docker so it
can still reach an API running on your host machine.

For the GitHub App private key, keep the file in `.secrets/` locally and mount
that directory into the container. In production, mount the PEM from the host or
your secret manager to the same in-container path referenced by
`HOM_GITHUB_PRIVATE_KEY_PATH`.

```sh
$ docker compose up
```

Every time you save a python file in the `hom` directory, the bot will restart.

## License

Helpful Old Man is licensed under the [MIT License]
(https://github.com/wise-old-man/helpful-old-man/blob/main/LICENSE).

## Link API key developers

Moderators can run `/link-user-api-keys developers:<devs.csv> api_consumer_role:<role>`
and select the server's API Consumer role directly in the command. No role ID
environment variable is needed. Upload a UTF-8 CSV containing a `developer` column.
The bot fetches the server's members and
matches exact, case-sensitive usernames or legacy `name#1234` tags. It does not
match nicknames, display names, or guess old usernames. Duplicate CSV values are
processed once. Ambiguous matches are skipped. The bot re-fetches each matched
member and adds the API Consumer role if missing before sending the key update.
If adding the role fails, that member's keys are not updated. The bot needs
Manage Roles permission and a role above the API Consumer role to assign it.

The command defaults to `dry_run:True`: it makes no API update requests or role changes and
reports how many users would be linked, along with names and reasons for those
who would not. It also reports how many users would receive the missing role and
attaches the full results CSV. The preview checks Discord matches and roles; it cannot
verify database key counts. Use `dry_run:False` explicitly to apply the updates.
Developer names are sorted alphabetically (ignoring case for sorting, preserving
case for matching). Set `counts_only:True` to show one category-count summary
instead of individual username messages; the full sorted CSV is still attached.

The command calls the admin-only `PUT /api-keys/developer/:developer` endpoint,
URL-encoding the developer name and sending the member's ID as
`developerDiscordId`. This updates all matching API key rows, including revoked
keys, and replaces previous links. The backend migration and endpoint must be
available at `HOM_BASE_API_URL`. The bot needs Server Members Intent enabled.
The ephemeral results CSV lists linked, skipped, failed, and unprocessed rows.
A failed/unconfirmed API request stops the run; earlier updates remain applied.
The summary counts unique users given the role (or needing it in dry run), and
the CSV's `roleAction` column records each developer's role outcome. Successfully
added roles remain assigned if a later API update fails or finds no matching keys.

For this one-time backfill, the command also reads member-role audit entries
before changing any roles or keys. It uses each matched user's earliest retained
addition of the selected API Consumer role as an estimate of key creation time,
and sends that UTC timestamp as `createdAt` alongside `developerDiscordId`.
The backend PUT endpoint is assumed to accept `createdAt`. The same date applies
to all API key rows matching that developer. If no date is found, `createdAt` is
omitted from the request and left unchanged. Audit entries are retained for only
45 days; older dates cannot be recovered this way. The bot requires View Audit
Log permission. Failed audit retrieval aborts before making any changes.
Dry runs show date counts and include the proposed `createdAt` in the results CSV.

## Audit API moderator logs

Moderators can run `/audit-mod-logs channel:<channel>` to scan bot messages in
the selected text channel, up to the time the command was invoked. A message
matches if its content or any embed title/description contains `api`, and none
of those contain `channel` or `for user` (all comparisons ignore case).
The public response in the channel where the command was invoked includes the
match count, scan duration in minutes and seconds, the earliest and latest matching
messages with timestamps and links, and a text attachment containing matching
messages in chronological order. Each entry includes the message link, timestamp,
bot identity, full message content, and each embed's title, description, fields,
URL, author, and footer where present. The attachment is built in memory and
is not saved to disk. Both the moderator and bot need View Channel and Read
Message History permissions. Interrupted scans or scans exceeding 12 minutes
are explicitly reported as incomplete.
One private status message updates every 2,500 processed messages with the
processed and matching counts, then updates once more when the scan finishes.
Discord does not provide the total channel message count, so progress has no denominator.
The final summary, attachments, and any upload-failure notices are public so they
remain accessible after the command finishes; progress updates remain private.
The summary is sent separately from attachments. Reports exceeding Discord's
interaction upload limit are split into numbered text files at complete line
boundaries, with each part uploaded separately. If an upload is rejected, the
bot reports which part failed and how many parts were delivered; the summary
remains available. All parts are built in memory and never saved to disk.

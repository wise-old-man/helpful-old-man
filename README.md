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
HOM_GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----"
```

If `HOM_GITHUB_REPOSITORIES` is blank, the GitHub issue commands stay disabled and
the bot will prompt you to configure it instead of falling back to defaults.

Create a private GitHub App for the repos listed in `HOM_GITHUB_REPOSITORIES`,
disable webhooks, grant repository `Issues: Read and write`, generate a private
key, and install the app on the target repos. The bot resolves the installation
automatically per repository, so you do not need to store an installation ID in
`.env`.

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

```sh
$ docker compose up
```

Every time you save a python file in the `hom` directory, the bot will restart.

## License

Helpful Old Man is licensed under the [MIT License]
(https://github.com/wise-old-man/helpful-old-man/blob/main/LICENSE).

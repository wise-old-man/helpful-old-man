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

## Contributing with Docker

You can also run the bot inside docker with hot reloading. It is still
recommended to have have python and the bot's dependencies installed for
compatibility with your linter.

Still make sure to copy the `.env` file and that your discord bot application
has proper perms in the developer dashboard.

```sh
$ docker-compose up
```

Every time you save a python file in the `hom` directory, the bot will restart.

## License

Helpful Old Man is licensed under the [MIT License]
(https://github.com/wise-old-man/helpful-old-man/blob/main/LICENSE).

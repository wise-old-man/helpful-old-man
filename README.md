# HOM

The helpful old man!

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
$ cp .env.example .env
```

Update the values in `.env` for your development bot

Ensure the bot has the proper permissions and intents (all) 

Run the bot

```bash
$ python -m hom
```

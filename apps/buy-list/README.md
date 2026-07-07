# Example app: `buy-list` (full CRUD)

A shopping list. Add items with a quantity, check them off (done), delete. Works on your phone
and on the glasses; edits sync through the Worker and are offline‑tolerant (queued locally,
flushed when back online).

## Run it
The Worker serves this app inside the launcher — just open your Worker URL and pick **Buy List**.
For a standalone / local‑dev view, open the dev launcher with the config:
```
app/index.html?config=../apps/buy-list/app.config.json
app/index.html?config=../apps/buy-list/app.config.json#glass   (pin glasses layout)
```
First open on the phone asks once for your password (the Worker's `API_SECRET`); it's stored
in the browser only.

## Glasses controls
▲▼ move · Enter detail · Space/c check off · Del delete. Adding items is done on the phone.

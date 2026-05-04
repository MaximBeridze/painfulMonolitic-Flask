# GameHub — Legacy Backend

You've just joined a team. This is the codebase they left you.

It's a social platform for gamers. Users can track what they're playing, follow friends,
log activities, and receive notifications. It was built fast, it works, and nobody has
touched it in two years. Your job is to make a few changes.

---

## Setup

```bash
pip install -r requirements.txt
python seed.py
python app.py
```

The app runs on `http://localhost:5000`.

> If you need to reset the database, delete `gamehub.db` and run `python seed.py` again.

---

## Files

| File            | Description                                              |
|-----------------|----------------------------------------------------------|
| `app.py`        | The entire application — routes, logic, DB queries       |
| `models.py`     | Database schema — all tables and constraints             |
| `seed.py`       | Populates the database with pre-built data               |
| `reference.md`  | Page-by-page guide to the UI and what each form does     |
| `questions.md`  | 10 questions to test your understanding of the system    |

---

## What's in the app

A web UI is available at `http://localhost:5000` — use it to browse users, games,
activities, and notifications.

The same app also exposes a JSON API if you prefer to use curl or Postman:

| Method | Route                      | Description                   |
|--------|----------------------------|-------------------------------|
| GET    | /users                     | List all users                |
| GET    | /users/\<id\>              | Get a user                    |
| POST   | /users                     | Create a user                 |
| PUT    | /users/\<id\>              | Update a user                 |
| DELETE | /users/\<id\>              | Delete a user                 |
| GET    | /games                     | List all games                |
| GET    | /games/\<id\>              | Get a game                    |
| POST   | /games                     | Create a game                 |
| PUT    | /games/\<id\>              | Update a game                 |
| GET    | /activities                | List all activities           |
| POST   | /activities                | Log an activity               |
| GET    | /notifications/\<user_id\> | Get notifications for a user  |
| DELETE | /notifications/\<id\>      | Delete a notification         |
| GET    | /friends/\<user_id\>       | Get friends of a user         |
| POST   | /friends                   | Add a friendship              |

---

## Your tasks

### Task 1 — Delete the user `alex_g`

He left the platform. Remove him from the system entirely.
He should no longer appear anywhere in the app.

---

### Task 2 — Rename `username` to `display_name`

The product team decided the field `username` is confusing to end users.
They want it renamed to `display_name` everywhere.

---

### Task 3 — Add an opt-out privacy flag

Users should be able to opt out of activity tracking.
If a user has opted out, logging an activity anywhere in the app should have no effect for them.

---

### Task 4 — Make notifications optional

The notification system is causing performance issues under load.
Disable it without affecting any other part of the app.

---

### Task 5 — Fix a game title

The game `Disco Elysium` should be listed as `Disco Elysium: The Final Cut`.
It's a simple fix — ship it as fast as you can.

---

Good luck.

---

## Resources

- `reference.md` — explains what each page and form does
- `questions.md` — 10 questions to check your understanding before attempting the tasks

# GameHub — Understanding the system

10 questions to test your understanding of the data flow and architecture.
Work through them in order: read the code first, then run the app, then try to break things.

---

## How to investigate

You will need three things:

**1. Read the source code**
Start with `models.py` (the schema), then `seed.py` (the data), then `app.py` (the logic).
Many questions are answered entirely by reading carefully.

**2. Run the app and interact with it**
Use the UI at `http://localhost:5000` or send requests with curl or Postman.
Observe what actually happens — don't just reason about it.

```bash
# Example: log an activity for nova (id=1) on Hollow Knight (id=1)
curl -X POST http://localhost:5000/activities \
  -H "Content-Type: application/json" \
  -d '{"user_id": 1, "game_id": 1, "action": "started"}'
```

**3. Query the database directly**
Open `gamehub.db` with a SQLite tool and inspect the actual rows.

```bash
sqlite3 gamehub.db
.tables
SELECT COUNT(*) FROM notifications;
SELECT * FROM notifications WHERE user_id = 1;
```

Or use a GUI: **DB Browser for SQLite** (free, recommended).

---

## Suggested approach

| Phase | Questions | What you are doing |
|-------|-----------|-------------------|
| Read first | 1, 4, 8, 10 | Understand the code before touching anything |
| Then run it | 3, 6, 9    | Observe actual behaviour                     |
| Then break it | 2, 5, 7  | Try things, hit walls, reason about why      |

---

## Questions

**1.** When a user logs a new activity, how many database tables are written to?
List them and explain why each one is affected.

---

**2.** You call `DELETE FROM users WHERE id = 3` directly in SQLite.
What happens, and why? What would you need to do instead?

---

**3.** User `nova` changes her username to `nova_2`.
She then checks her friends' notification feeds.
What do they see — the old name or the new one? Why?

---

**4.** Trace the full journey of a `POST /activities` request.
Starting from the HTTP call, list every operation that happens before the response is returned.

---

**5.** `pixel_queen` opts out of activity tracking.
A teammate adds an `opted_out` boolean column to the `users` table and updates the `POST /activities` API route to check it.
Is the feature fully implemented? What did they miss?

---

**6.** How many rows are created in the database when `nova` logs one activity, given the current seed data?
Show your working.

---

**7.** You need to delete `maya_r`.
In what order must you delete rows across the tables, and why does the order matter?

---

**8.** The `notifications` table has a foreign key pointing to `activities`.
What happens if you try to delete an activity that has notifications attached to it?

---

**9.** A bug is found in the game catalog — wrong genre for one game.
You fix it and restart the app to ship the change.
What else just went down, and for how long?

---

**10.** A teammate says: *"let's just move the notification logic into its own function in `app.py`"*.
Does that solve the problem described in Task 4?
What is the actual architectural issue?

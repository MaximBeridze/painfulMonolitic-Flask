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

`activities` and `notifications`
The route first inserts one row into `activities` for the user/game/action. It then looks up the actor, game, and the actor's friends, and inserts one row into `notifications` for each friend. It also reads from `users`, `games`, and `friends`,

---

**2.** You call `DELETE FROM users WHERE id = 3` directly in SQLite.

What happens, and why? What would you need to do instead?
`DELETE FROM users WHERE id = 3` fails with a foreign key constraint error if SQLite foreign keys are enabled.

`maya_r` is referenced by other tables: `activities.user_id`, `user_games.user_id`, `friends.user_id`, `friends.friend_id`, `notifications.user_id`, and `notifications.triggered_by`. The schema does not use `ON DELETE CASCADE`, so SQLite will not delete dependent rows automatically. You must delete the dependent rows first, in a safe order, then delete the user.
---

**3.** User `nova` changes her username to `nova_2`.
She then checks her friends' notification feeds.
What do they see — the old name or the new one? Why?

If the message is before the name change, they will see `nova`, if it is after the name change, they will see `nova_2`

The `notifications` query joins `notifications.triggered_by` back to `users.id`, so the `From` column uses the current username and will show `nova_2`. But notification `message` is plain text created at the time the activity was logged. If the message was created before the rename and contained `nova`, that message will still contain the old name.

---

**4.** Trace the full journey of a `POST /activities` request.
Starting from the HTTP call, list every operation that happens before the response is returned.

1. Flask receives JSON at `POST /activities`.
2. `create_activity()` reads `request.json`.
3. The app opens a SQLite connection with foreign keys enabled.
4. It inserts a row into `activities` with `user_id`, `game_id`, `action`, and `created_at`.
5. It commits that activity insert.
6. It queries the most recent activity for that user to get the inserted activity row.
7. It queries `users` to get the actor's username.
8. It queries `games` to get the game title.
9. It queries `friends` for all `friend_id` rows where `user_id` is the actor.
10. For each friend, it builds a text message.
11. For each friend, it inserts a row into `notifications`.
12. It commits the notification inserts.
13. It closes the database connection.
14. It returns the activity as JSON with HTTP `201`.

---

**5.** `pixel_queen` opts out of activity tracking.
A teammate adds an `opted_out` boolean column to the `users` table and updates the `POST /activities` API route to check it.
Is the feature fully implemented? What did they miss?

No, the feature is not fully implemented. They updated only the JSON API route. The app has another activity creation path in `POST /view/activities`, and that route also inserts into `activities` and creates notifications. They also need to update the schema, seed data/defaults, user create/update forms or APIs as needed, and every path that logs activity. Otherwise `pixel_queen` can still be tracked through the HTML UI.

---

**6.** How many rows are created in the database when `nova` logs one activity, given the current seed data?
Show your working.

The seed data gives `nova` three outgoing friend rows: `alex_g`, `maya_r`, and `pixel_queen`. Logging one activity creates one `activities` row plus one `notifications` row for each of those three friends. So the total is 4 new rows. (3 if we exclude alex_g, as we removed him from the original seed)

---

**7.** You need to delete `maya_r`.
In what order must you delete rows across the tables, and why does the order matter?

1. Delete notifications where `user_id = maya_r`.
2. Delete notifications where `triggered_by = maya_r`.
3. Delete `maya_r`'s activities.
4. Delete `maya_r`'s `user_games` rows.
5. Delete friendships where `user_id = maya_r` or `friend_id = maya_r`.
6. Delete the `users` row for `maya_r`.

The order matters because the database has foreign keys but no cascading deletes. `notifications` must be removed before `activities`, because `notifications.activity_id` points at `activities.id`. Other rows that point at the user must be removed before the user row can be deleted.

---

**8.** The `notifications` table has a foreign key pointing to `activities`.
What happens if you try to delete an activity that has notifications attached to it?

Deleting an activity that has notifications attached fails with a foreign key constraint error. `notifications.activity_id` references `activities.id`, and there is no `ON DELETE CASCADE`. You must delete the attached notification rows first, then delete the activity.

---

**9.** A bug is found in the game catalog — wrong genre for one game.
You fix it and restart the app to ship the change.
What else just went down, and for how long?

The whole Flask app goes down during the restart. Because users, games, activities, notifications, API routes, and HTML pages all run in the same process, shipping a catalog fix by restarting the app also takes down user browsing, activity logging, notification feeds, and every other route. It is down for however long the restart takes.

---

**10.** A teammate says: *"let's just move the notification logic into its own function in `app.py`"*.
Does that solve the problem described in Task 4?
What is the actual architectural issue?

Moving the notification logic into another function in `app.py` does not solve Task 4. That would make the route tidier, but notifications would still be synchronously called from activity creation inside the same application, same deployment, and same database transaction flow. The architectural issue is coupling: activity logging and notification delivery are not separated by a real boundary. There is no independent notification service, queue, feature flag, or configuration switch that lets the team disable notifications without editing and redeploying the core activity route.

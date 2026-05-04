# GameHub — Quick Reference

A page-by-page guide to what the app shows and what each form does.

---

## Users — `/view/users`

### What the page shows
A table of all registered users with their username, email, bio, and join date.
Each row has a delete button.

### Delete button (per row)
Removes the user from the system.
Triggers a confirmation dialog before submitting.
Sends a `POST` to `/view/users/<id>/delete`.

### Add a new user form
| Field      | Required | Description                  |
|------------|----------|------------------------------|
| Username   | Yes      | Unique identifier for the user |
| Email      | Yes      | Must be a valid email format |
| Bio        | No       | Short profile description    |

Submits to `POST /view/users`. Redirects back to the users list on success.

---

## User detail — `/view/users/<id>`

### What the page shows
- The user's profile (username, email, bio, join date)
- A table of games they own and how many hours they've played
- A table of their recent activities (game + action + date)
- A table of their friends, with a link to each friend's notifications
- A link to the user's own notification feed

### Edit profile form
| Field      | Required | Description                                                      |
|------------|----------|------------------------------------------------------------------|
| Username   | Yes      | Changing this does NOT update old notification messages — they store the name as plain text at the time they were created |
| Email      | Yes      | Updated immediately                                              |
| Bio        | No       | Updated immediately                                              |

Submits to `POST /view/users/<id>/update`. Redirects back to the same profile page.

### Delete user button
Removes the user and all data linked to them (activities, notifications, friendships, game library).
Sends a `POST` to `/view/users/<id>/delete`. Redirects to the users list on success.

---

## Games — `/view/games`

### What the page shows
A table of all games in the catalog with their title, genre, description, and creation date.
Each row has an Edit button that reveals an inline edit form.

### Inline edit form (per game)
Appears below the game row when Edit is clicked.

| Field       | Required | Description             |
|-------------|----------|-------------------------|
| Title       | Yes      | Name of the game        |
| Genre       | Yes      | e.g. RPG, Platformer    |
| Description | No       | Short summary           |

Submits to `POST /view/games/<id>/update`. Redirects back to the games list on success.
> Note: saving a change here requires no code change — but shipping a code change to this route requires restarting the entire app.

### Add a new game form
| Field       | Required | Description             |
|-------------|----------|-------------------------|
| Title       | Yes      | Must be unique          |
| Genre       | Yes      | e.g. RPG, Platformer    |
| Description | No       | Short summary           |

Submits to `POST /view/games`. Redirects back to the games list on success.

---

## Activities — `/view/activities`

### What the page shows
A global feed of all activities across all users, ordered newest first.
Each row shows the username, game title, action, and date.

### Log an activity form
| Field  | Required | Description                                                        |
|--------|----------|--------------------------------------------------------------------|
| User   | Yes      | Dropdown of all users                                              |
| Game   | Yes      | Dropdown of all games                                              |
| Action | Yes      | One of: `started`, `completed`, `replaying`, `dropped`            |

Submits to `POST /view/activities`. Redirects back to the feed on success.

> **What happens behind the scenes when this form is submitted:**
> 1. A new row is inserted into `activities`
> 2. The app fetches the user's friend list
> 3. For every friend, a new row is inserted into `notifications`
>
> Logging one activity for a user with 2 friends creates 3 database writes minimum.
> This logic lives inside the route — there is no separate notification service.

---

## Notifications — `/view/notifications/<user_id>`

### What the page shows
All notifications for a specific user, ordered newest first.
Each row shows who triggered it, the message, the date, and a Dismiss button.

Reached via the friends table on a user's detail page, or directly by URL.

### Dismiss button (per row)
Deletes the notification permanently.
Sends a `POST` to `/view/notifications/<id>/delete`.
Redirects back to the same notification feed.

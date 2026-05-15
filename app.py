from flask import Flask, jsonify, request, render_template, redirect, url_for
from datetime import datetime, timezone
from models import init_db, get_db

app = Flask(__name__)

ENABLE_NOTIFICATIONS = False


def now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# Run DB setup on startup
init_db()


# =============================================================================
# USERS
# =============================================================================

@app.route("/users", methods=["GET"])
def list_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return jsonify([dict(u) for u in users])


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify(dict(user))


@app.route("/users", methods=["POST"])
def create_user():
    data = request.json
    conn = get_db()
    opted_out = 1 if data.get("opted_out") else 0
    notifications = 1 if data.get("notifications", True) else 0
    conn.execute(
        "INSERT INTO users (display_name, email, password_hash, bio, created_at, opted_out, notifications) VALUES (?,?,?,?,?,?,?)",
        (data["display_name"], data["email"], data.get("password", "hashed"), data.get("bio", ""), now(), opted_out, notifications)
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE display_name = ?", (data["display_name"],)).fetchone()
    conn.close()
    return jsonify(dict(user)), 201


@app.route("/users/<int:user_id>", methods=["PUT"])
def update_user(user_id):
    data = request.json
    conn = get_db()
    # Note: display_name is used as identifier in activity messages and notifications.
    # Changing it here does NOT update those references — they're stored as plain text.
    opted_out = 1 if data.get("opted_out") else 0
    notifications = 1 if data.get("notifications", True) else 0
    conn.execute(
        "UPDATE users SET display_name = ?, email = ?, bio = ?, opted_out = ?, notifications = ? WHERE id = ?",
        (data["display_name"], data["email"], data.get("bio", ""), opted_out, notifications, user_id)
    )
    conn.commit()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return jsonify(dict(user))


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_db()

    # To delete a user, you must manually remove every row that references them.
    # The order matters — notifications reference activities, so activities can't
    # be deleted before notifications. Friends reference users twice. Good luck.

    # Step 1 — remove notifications where user is the receiver
    conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))

    # Step 2 — remove notifications where user is the one who triggered them
    conn.execute("DELETE FROM notifications WHERE triggered_by = ?", (user_id,))

    # Step 3 — remove activities
    conn.execute("DELETE FROM activities WHERE user_id = ?", (user_id,))

    # Step 4 — remove from user_games
    conn.execute("DELETE FROM user_games WHERE user_id = ?", (user_id,))

    # Step 5 — remove friendships (both directions)
    conn.execute("DELETE FROM friends WHERE user_id = ? OR friend_id = ?", (user_id, user_id))

    # Step 6 — finally, remove the user
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))

    conn.commit()
    conn.close()
    return jsonify({"message": "User deleted"}), 200


# =============================================================================
# GAMES
# =============================================================================

@app.route("/games", methods=["GET"])
def list_games():
    conn = get_db()
    games = conn.execute("SELECT * FROM games").fetchall()
    conn.close()
    return jsonify([dict(g) for g in games])


@app.route("/games/<int:game_id>", methods=["GET"])
def get_game(game_id):
    conn = get_db()
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    conn.close()
    if not game:
        return jsonify({"error": "Game not found"}), 404
    return jsonify(dict(game))


@app.route("/games", methods=["POST"])
def create_game():
    data = request.json
    conn = get_db()
    conn.execute(
        "INSERT INTO games (title, genre, description, created_at) VALUES (?,?,?,?)",
        (data["title"], data["genre"], data.get("description", ""), now())
    )
    conn.commit()
    game = conn.execute("SELECT * FROM games WHERE title = ?", (data["title"],)).fetchone()
    conn.close()
    return jsonify(dict(game)), 201


@app.route("/games/<int:game_id>", methods=["PUT"])
def update_game(game_id):
    # Fixing a typo in a game title? Correcting a genre?
    # You'll need to restart the entire app to ship this change.
    # Users, auth, notifications — all go down with it.
    data = request.json
    conn = get_db()
    conn.execute(
        "UPDATE games SET title = ?, genre = ?, description = ? WHERE id = ?",
        (data["title"], data["genre"], data.get("description", ""), game_id)
    )
    conn.commit()
    game = conn.execute("SELECT * FROM games WHERE id = ?", (game_id,)).fetchone()
    conn.close()
    return jsonify(dict(game))


# =============================================================================
# ACTIVITIES
# =============================================================================

@app.route("/activities", methods=["GET"])
def list_activities():
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, u.display_name, g.title as game_title
        FROM activities a
        JOIN users u ON a.user_id = u.id
        JOIN games g ON a.game_id = g.id
        ORDER BY a.created_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/activities", methods=["POST"])
def create_activity():
    data = request.json
    conn = get_db()

    # Check if user has opted out of logging activities before inserting activity
    user = conn.execute("SELECT * FROM users WHERE id = ?", (data["user_id"],)).fetchone()
    if user["opted_out"]:
        conn.close()
        return jsonify({"error": "User has opted out of logging activities"}), 403

    # Insert the activity
    conn.execute(
        "INSERT INTO activities (user_id, game_id, action, created_at) VALUES (?,?,?,?)",
        (data["user_id"], data["game_id"], data["action"], now())
    )
    conn.commit()

    activity = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY id DESC LIMIT 1",
        (data["user_id"],)
    ).fetchone()

    actor = conn.execute("SELECT display_name FROM users WHERE id = ?", (data["user_id"],)).fetchone()
    game  = conn.execute("SELECT title FROM games WHERE id = ?", (data["game_id"],)).fetchone()

    # Notification logic lives here — because where else would it go?
    # This means you cannot disable notifications without touching this route.
    if ENABLE_NOTIFICATIONS:
        friends = conn.execute(
            "SELECT friend_id FROM friends WHERE user_id = ?", (data["user_id"],)
        ).fetchall()

        for f in friends:
            msg = f"{actor['display_name']} just {data['action']} playing {game['title']}!"
            conn.execute(
                "INSERT INTO notifications (user_id, triggered_by, message, activity_id, created_at) VALUES (?,?,?,?,?)",
                (f["friend_id"], data["user_id"], msg, activity["id"], now())
            )

    conn.commit()
    conn.close()
    return jsonify(dict(activity)), 201


# =============================================================================
# NOTIFICATIONS
# =============================================================================

@app.route("/notifications/<int:user_id>", methods=["GET"])
def get_notifications(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT n.*, u.display_name as triggered_by_display_name
        FROM notifications n
        JOIN users u ON n.triggered_by = u.id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/notifications/<int:notif_id>", methods=["DELETE"])
def delete_notification(notif_id):
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Notification deleted"})


# =============================================================================
# FRIENDS
# =============================================================================

@app.route("/friends/<int:user_id>", methods=["GET"])
def get_friends(user_id):
    conn = get_db()
    rows = conn.execute("""
        SELECT u.id, u.display_name, u.email, u.bio
        FROM friends f
        JOIN users u ON f.friend_id = u.id
        WHERE f.user_id = ?
    """, (user_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@app.route("/friends", methods=["POST"])
def add_friend():
    data = request.json
    conn = get_db()
    # Friendship is bidirectional — two rows required
    conn.execute("INSERT INTO friends (user_id, friend_id) VALUES (?,?)", (data["user_id"], data["friend_id"]))
    conn.execute("INSERT INTO friends (user_id, friend_id) VALUES (?,?)", (data["friend_id"], data["user_id"]))
    conn.commit()
    conn.close()
    return jsonify({"message": "Friends added"}), 201


# =============================================================================
# VIEWS — HTML pages served by the same app, same process, same restart
# =============================================================================

@app.route("/")
def index():
    return redirect(url_for("view_users"))


@app.route("/view/users", methods=["GET"])
def view_users():
    conn = get_db()
    users = conn.execute("SELECT * FROM users").fetchall()
    conn.close()
    return render_template("users.html", users=users)


@app.route("/view/users", methods=["POST"])
def view_create_user():
    conn = get_db()
    opted_out = 1 if request.form.get("opted_out") else 0
    notifications = 1 if request.form.get("notifications") else 0
    conn.execute(
        "INSERT INTO users (display_name, email, password_hash, bio, created_at, opted_out, notifications) VALUES (?,?,?,?,?,?,?)",
        (request.form["display_name"], request.form["email"], "hashed", request.form.get("bio", ""), now(), opted_out, notifications)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("view_users"))


@app.route("/view/users/<int:user_id>", methods=["GET"])
def view_user_detail(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if not user:
        conn.close()
        return "User not found", 404
    games = conn.execute("""
        SELECT g.*, ug.hours_played FROM games g
        JOIN user_games ug ON g.id = ug.game_id
        WHERE ug.user_id = ?
    """, (user_id,)).fetchall()
    activities = conn.execute("""
        SELECT a.*, g.title as game_title FROM activities a
        JOIN games g ON a.game_id = g.id
        WHERE a.user_id = ? ORDER BY a.created_at DESC
    """, (user_id,)).fetchall()
    friends = conn.execute("""
        SELECT u.* FROM users u
        JOIN friends f ON u.id = f.friend_id
        WHERE f.user_id = ?
    """, (user_id,)).fetchall()
    all_games = conn.execute("SELECT * FROM games").fetchall()
    conn.close()
    return render_template("user_detail.html", user=user, games=games,
                           activities=activities, friends=friends, all_games=all_games)


@app.route("/view/users/<int:user_id>/update", methods=["POST"])
def view_update_user(user_id):
    conn = get_db()
    # Note: display_name is used as identifier in activity messages and notifications.
    # Changing it here does NOT update those references — they're stored as plain text.
    opted_out = 1 if request.form.get("opted_out") else 0
    notifications = 1 if request.form.get("notifications") else 0
    conn.execute(
        "UPDATE users SET display_name = ?, email = ?, bio = ?, opted_out = ?, notifications = ? WHERE id = ?",
        (request.form["display_name"], request.form["email"], request.form.get("bio", ""), opted_out, notifications, user_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("view_user_detail", user_id=user_id))


@app.route("/view/users/<int:user_id>/delete", methods=["POST"])
def view_delete_user(user_id):
    conn = get_db()
    # Same ordering problem as the API — remove all FK references manually first
    conn.execute("DELETE FROM notifications WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM notifications WHERE triggered_by = ?", (user_id,))
    conn.execute("DELETE FROM activities WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM user_games WHERE user_id = ?", (user_id,))
    conn.execute("DELETE FROM friends WHERE user_id = ? OR friend_id = ?", (user_id, user_id))
    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_users"))


@app.route("/view/games", methods=["GET"])
def view_games():
    conn = get_db()
    games = conn.execute("SELECT * FROM games").fetchall()
    conn.close()
    return render_template("games.html", games=games)


@app.route("/view/games", methods=["POST"])
def view_create_game():
    conn = get_db()
    conn.execute(
        "INSERT INTO games (title, genre, description, created_at) VALUES (?,?,?,?)",
        (request.form["title"], request.form["genre"], request.form.get("description", ""), now())
    )
    conn.commit()
    conn.close()
    return redirect(url_for("view_games"))


@app.route("/view/games/<int:game_id>/update", methods=["POST"])
def view_update_game(game_id):
    # A one-line fix to a game title still requires restarting the whole app to ship.
    # While it's down: users can't log in, activities stop, notifications stop.
    conn = get_db()
    conn.execute(
        "UPDATE games SET title = ?, genre = ?, description = ? WHERE id = ?",
        (request.form["title"], request.form["genre"], request.form.get("description", ""), game_id)
    )
    conn.commit()
    conn.close()
    return redirect(url_for("view_games"))


@app.route("/view/activities", methods=["GET"])
def view_activities():
    conn = get_db()
    rows = conn.execute("""
        SELECT a.*, u.display_name, g.title as game_title
        FROM activities a
        JOIN users u ON a.user_id = u.id
        JOIN games g ON a.game_id = g.id
        ORDER BY a.created_at DESC
    """).fetchall()
    users = conn.execute("SELECT * FROM users").fetchall()
    games = conn.execute("SELECT * FROM games").fetchall()
    conn.close()
    return render_template("activities.html", activities=rows, users=users, games=games, error=None)


@app.route("/view/activities", methods=["POST"])
def view_create_activity():
    conn = get_db()
    user_id = int(request.form["user_id"])
    game_id = int(request.form["game_id"])
    action  = request.form["action"]

    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    if user["opted_out"]:
        rows = conn.execute("""
            SELECT a.*, u.display_name, g.title as game_title
            FROM activities a
            JOIN users u ON a.user_id = u.id
            JOIN games g ON a.game_id = g.id
            ORDER BY a.created_at DESC
        """).fetchall()
        users = conn.execute("SELECT * FROM users").fetchall()
        games = conn.execute("SELECT * FROM games").fetchall()
        conn.close()
        return render_template(
            "activities.html",
            activities=rows,
            users=users,
            games=games,
            error="This user has opted out of activity tracking."
        )

    conn.execute(
        "INSERT INTO activities (user_id, game_id, action, created_at) VALUES (?,?,?,?)",
        (user_id, game_id, action, now())
    )
    conn.commit()

    activity = conn.execute(
        "SELECT * FROM activities WHERE user_id = ? ORDER BY id DESC LIMIT 1", (user_id,)
    ).fetchone()
    actor = conn.execute("SELECT display_name FROM users WHERE id = ?", (user_id,)).fetchone()
    game  = conn.execute("SELECT title FROM games WHERE id = ?", (game_id,)).fetchone()

    # Notification logic lives here — because where else would it go?
    if ENABLE_NOTIFICATIONS:
        friends = conn.execute("SELECT friend_id FROM friends WHERE user_id = ?", (user_id,)).fetchall()
        for f in friends:
            msg = f"{actor['display_name']} just {action} playing {game['title']}!"
            conn.execute(
                "INSERT INTO notifications (user_id, triggered_by, message, activity_id, created_at) VALUES (?,?,?,?,?)",
                (f["friend_id"], user_id, msg, activity["id"], now())
            )

    conn.commit()
    conn.close()
    return redirect(url_for("view_activities"))


@app.route("/view/notifications/<int:user_id>", methods=["GET"])
def view_notifications(user_id):
    conn = get_db()
    user = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    rows = conn.execute("""
        SELECT n.*, u.display_name as triggered_by_display_name
        FROM notifications n
        JOIN users u ON n.triggered_by = u.id
        WHERE n.user_id = ?
        ORDER BY n.created_at DESC
    """, (user_id,)).fetchall()
    conn.close()
    return render_template("notifications.html", notifications=rows, user=user)


@app.route("/view/notifications/<int:notif_id>/delete", methods=["POST"])
def view_delete_notification(notif_id):
    user_id = request.form["user_id"]
    conn = get_db()
    conn.execute("DELETE FROM notifications WHERE id = ?", (notif_id,))
    conn.commit()
    conn.close()
    return redirect(url_for("view_notifications", user_id=user_id))


# =============================================================================

if __name__ == "__main__":
    app.run(debug=True, port=5000)

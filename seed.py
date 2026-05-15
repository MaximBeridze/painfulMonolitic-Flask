from datetime import datetime, timezone
from models import init_db, get_db

# Fake password hash — students don't need real bcrypt for this exercise
FAKE_HASH = "hashed_password"

def ts(day):
    return f"2024-01-{day:02d}T10:00:00Z"


def seed():
    init_db()
    conn = get_db()
    c = conn.cursor()

    # -------------------------------------------------------------------------
    # Users — canonical GameHub users, reused across all course materials
    # -------------------------------------------------------------------------
    users = [
        ("nova",        "nova@gamehub.io",    FAKE_HASH, "Explorer of virtual worlds.",      ts(1), 0),
        ("alex_g",      "alex@gamehub.io",    FAKE_HASH, "Speedrunner. Coffee addict.",       ts(2), 0),
        ("maya_r",      "maya@gamehub.io",    FAKE_HASH, "RPG lover, lore hunter.",           ts(3), 0),
        ("thunderbyte", "thunder@gamehub.io", FAKE_HASH, "FPS main, occasional cozy gamer.",  ts(4), 0),
        ("pixel_queen", "pixel@gamehub.io",   FAKE_HASH, "Completionist. 100% or nothing.",   ts(5), 0),
    ]
    c.executemany(
        "INSERT INTO users (display_name, email, password_hash, bio, created_at, opted_out) VALUES (?,?,?,?,?,?)",
        users
    )

    # -------------------------------------------------------------------------
    # Games — canonical GameHub catalog
    # -------------------------------------------------------------------------
    games = [
        ("Hollow Knight",              "Metroidvania", "A challenging underground adventure.",          ts(1)),
        ("Celeste",                    "Platformer",   "Climb the mountain. Face yourself.",            ts(1)),
        ("Hades",                      "Roguelite",    "Defy the god of the dead.",                     ts(1)),
        ("Stardew Valley",             "Simulation",   "Build your farm. Build your life.",             ts(1)),
        ("Dead Cells",                 "Roguelite",    "Die. Adapt. Grow stronger.",                    ts(1)),
        ("Ori and the Blind Forest",   "Platformer",   "A breathtaking forest journey.",                ts(1)),
        ("Disco Elysium",              "RPG",          "A detective RPG unlike any other.",             ts(1)),
        ("Outer Wilds",                "Adventure",    "Explore a solar system stuck in a time loop.",  ts(1)),
    ]
    c.executemany(
        "INSERT INTO games (title, genre, description, created_at) VALUES (?,?,?,?)",
        games
    )

    conn.commit()

    # Fetch IDs now that rows are inserted
    users_db = {row["display_name"]: row["id"] for row in c.execute("SELECT id, display_name FROM users")}
    games_db = {row["title"]: row["id"] for row in c.execute("SELECT id, title FROM games")}

    nova        = users_db["nova"]
    alex        = users_db["alex_g"]
    maya        = users_db["maya_r"]
    thunder     = users_db["thunderbyte"]
    pixel       = users_db["pixel_queen"]

    hk    = games_db["Hollow Knight"]
    cel   = games_db["Celeste"]
    hades = games_db["Hades"]
    sdv   = games_db["Stardew Valley"]
    dc    = games_db["Dead Cells"]
    ori   = games_db["Ori and the Blind Forest"]
    disco = games_db["Disco Elysium"]
    ow    = games_db["Outer Wilds"]

    # -------------------------------------------------------------------------
    # user_games — who owns what
    # -------------------------------------------------------------------------
    c.executemany(
        "INSERT INTO user_games (user_id, game_id, hours_played) VALUES (?,?,?)",
        [
            (nova,    hk,    42),  (nova,    cel,  18),  (nova,    ow,   31),
            (alex,    hk,   120),  (alex,    dc,   88),  (alex,    cel,  55),
            (maya,    disco, 74),  (maya,    sdv,  200), (maya,    ori,  22),
            (thunder, hades, 60),  (thunder, dc,   45),  (thunder, hk,   10),
            (pixel,   cel,  300),  (pixel,   hk,  250),  (pixel,   hades,90),
        ]
    )

    # -------------------------------------------------------------------------
    # friends — a web, not isolated pairs
    # nova <-> alex, nova <-> maya, alex <-> thunder, maya <-> pixel, thunder <-> pixel, pixel <-> nova
    # -------------------------------------------------------------------------
    friendships = [
        (nova, alex),    (alex, nova),
        (nova, maya),    (maya, nova),
        (alex, thunder), (thunder, alex),
        (maya, pixel),   (pixel, maya),
        (thunder, pixel),(pixel, thunder),
        (pixel, nova),   (nova, pixel),
    ]
    c.executemany("INSERT INTO friends (user_id, friend_id) VALUES (?,?)", friendships)

    # -------------------------------------------------------------------------
    # activities — each user logs several actions
    # -------------------------------------------------------------------------
    activities_data = [
        (nova,    hk,    "started",   ts(10)),
        (nova,    cel,   "completed", ts(11)),
        (nova,    ow,    "started",   ts(12)),
        (alex,    hk,    "completed", ts(10)),
        (alex,    dc,    "started",   ts(11)),
        (alex,    cel,   "started",   ts(13)),
        (maya,    disco, "started",   ts(10)),
        (maya,    sdv,   "completed", ts(12)),
        (maya,    ori,   "started",   ts(14)),
        (thunder, hades, "started",   ts(11)),
        (thunder, dc,    "completed", ts(13)),
        (thunder, hk,    "started",   ts(15)),
        (pixel,   cel,   "completed", ts(10)),
        (pixel,   hk,    "completed", ts(12)),
        (pixel,   hades, "started",   ts(14)),
    ]
    c.executemany(
        "INSERT INTO activities (user_id, game_id, action, created_at) VALUES (?,?,?,?)",
        activities_data
    )

    conn.commit()

    activity_rows = c.execute("SELECT id, user_id FROM activities ORDER BY id").fetchall()

    # -------------------------------------------------------------------------
    # notifications — each activity notifies at least one friend
    # This is the kind of logic that should NOT live in seed, but here we are.
    # -------------------------------------------------------------------------
    friend_map = {}
    for u, f in friendships:
        friend_map.setdefault(u, []).append(f)

    notifications = []
    for row in activity_rows:
        act_id  = row["id"]
        actor   = row["user_id"]
        targets = friend_map.get(actor, [])
        for target in targets:
            msg = f"Your friend did something new — check their activity!"
            notifications.append((target, actor, msg, act_id, ts(15)))

    c.executemany(
        "INSERT INTO notifications (user_id, triggered_by, message, activity_id, created_at) VALUES (?,?,?,?,?)",
        notifications
    )

    conn.commit()
    conn.close()

    print("Database seeded. Good luck.")


if __name__ == "__main__":
    seed()

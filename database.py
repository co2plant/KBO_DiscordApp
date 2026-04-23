import pymysql
import settings


def _require_setting(name, value):
    if not isinstance(value, str) or value == '':
        raise RuntimeError(f'Invalid DB setting: {name}')
    return value


HOST = _require_setting('DB_HOST', settings.DB_HOST)
USER = _require_setting('DB_USER', settings.DB_USER)
PASSWORD = _require_setting('DB_PASSWORD', settings.DB_PASSWORD)
DB = _require_setting('DB_NAME', settings.DB_NAME)

_SCHEMA_READY = False

_SCHEMA_STATEMENTS = (
    """
    CREATE TABLE IF NOT EXISTS Standings (
        id VARCHAR(16) NOT NULL,
        team VARCHAR(32) PRIMARY KEY,
        win INT NOT NULL,
        lose INT NOT NULL,
        draw INT NOT NULL,
        rate DECIMAL(5,3) NOT NULL,
        last_10 VARCHAR(32) NOT NULL,
        streak VARCHAR(32) NOT NULL,
        home VARCHAR(32) NOT NULL,
        away VARCHAR(32) NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Games (
        id VARCHAR(16) PRIMARY KEY,
        time VARCHAR(16) NOT NULL,
        away VARCHAR(32) NOT NULL,
        home VARCHAR(32) NOT NULL,
        stadium VARCHAR(64) NOT NULL,
        remarks VARCHAR(64) NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS Scores (
        id VARCHAR(16) PRIMARY KEY,
        away_score INT NOT NULL,
        home_score INT NOT NULL,
        CONSTRAINT fk_scores_game FOREIGN KEY (id) REFERENCES Games(id) ON DELETE CASCADE
    )
    """,
)


def _ensure_schema(conn):
    global _SCHEMA_READY

    if _SCHEMA_READY:
        return

    cursor = conn.cursor()
    try:
        for statement in _SCHEMA_STATEMENTS:
            cursor.execute(statement)
        cursor.execute("SHOW INDEX FROM Standings WHERE Key_name = 'PRIMARY'")
        primary_columns = [row[4] for row in cursor.fetchall()]
        if primary_columns != ['team']:
            cursor.execute("ALTER TABLE Standings DROP PRIMARY KEY, ADD PRIMARY KEY (team)")
        conn.commit()
        _SCHEMA_READY = True
    finally:
        cursor.close()


def _connect():
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, db=DB, charset='utf8')
    _ensure_schema(conn)
    return conn


def ensure_schema():
    conn = _connect()
    conn.close()


def has_standings_data():
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM Standings")
        row = cursor.fetchone()
        return bool(row) and row[0] >= 10
    finally:
        cursor.close()
        conn.close()


def has_schedule_data():
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT 1 FROM Games LIMIT 1")
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def insert_standings(game_info):
    # Connect to the database
    conn = _connect()
    cursor = conn.cursor()

    # Insert into Standings table
    insert_standings_query = """
    INSERT INTO Standings (id, team, win, lose, draw, rate, last_10, streak, home, away)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        id = VALUES(id),
        win = VALUES(win),
        lose = VALUES(lose),
        draw = VALUES(draw),
        rate = VALUES(rate),
        last_10 = VALUES(last_10),
        streak = VALUES(streak),
        home = VALUES(home),
        away = VALUES(away)
    """
    standings_values = (game_info[0], game_info[1], game_info[2], game_info[3], game_info[4], game_info[5], game_info[6], game_info[7], game_info[8], game_info[9])
    try:
        cursor.execute(insert_standings_query, standings_values)
    except Exception as exc:
        print(f"Error inserting standings: {standings_values} ({exc})")

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

def update_standings(game_info):
    # Connect to the database
    conn = _connect()
    cursor = conn.cursor()

    update_standings_query = """
    INSERT INTO Standings (id, team, win, lose, draw, rate, last_10, streak, home, away)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        id = VALUES(id),
        win = VALUES(win),
        lose = VALUES(lose),
        draw = VALUES(draw),
        rate = VALUES(rate),
        last_10 = VALUES(last_10),
        streak = VALUES(streak),
        home = VALUES(home),
        away = VALUES(away)
    """
    standings_values = (game_info[0], game_info[1], game_info[2], game_info[3], game_info[4], game_info[5], game_info[6], game_info[7], game_info[8], game_info[9])
    try:
        cursor.execute(update_standings_query, standings_values)
    except Exception as exc:
        print(f"Error updating standings: {standings_values} ({exc})")

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

def select_standings():
    conn = _connect()
    cursor = conn.cursor()

    select_query = """
    SELECT * FROM Standings ORDER BY CAST(id AS UNSIGNED), team
    """

    try:
        cursor.execute(select_query)
        result = cursor.fetchall()
    except:
        result = None

    cursor.close()
    conn.close()

    return result


def insert_game_and_score(game_info):
    # Connect to the database
    conn = _connect()
    cursor = conn.cursor()

    # Insert into Games table
    insert_game_query = """
    INSERT INTO Games (id, time, away, home, stadium, remarks)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    game_values = (game_info[0],  game_info[1], game_info[2],game_info[5], game_info[6], game_info[7])
    try:
        cursor.execute(insert_game_query, game_values)
    except:
        print(f"Error inserting game: {game_values}")


    # Insert into Scores table
    insert_score_query = """
    INSERT INTO Scores (id, away_score, home_score)
    VALUES (%s, %s, %s)
    """
    score_values = (game_info[0], game_info[3], game_info[4])
    try:
        cursor.execute(insert_score_query, score_values)
    except:
        print(f"Error inserting score: {score_values}")

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()


def update_game_and_score(game_info):
    conn = _connect()
    cursor = conn.cursor()

    upsert_game_query = """
    INSERT INTO Games (id, time, away, home, stadium, remarks)
    VALUES (%s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        time = VALUES(time),
        away = VALUES(away),
        home = VALUES(home),
        stadium = VALUES(stadium),
        remarks = VALUES(remarks)
    """
    game_values = (game_info[0], game_info[1], game_info[2], game_info[5], game_info[6], game_info[7])
    try:
        cursor.execute(upsert_game_query, game_values)
    except Exception as exc:
        print(f"Error updating game: {game_values} ({exc})")

    upsert_score_query = """
    INSERT INTO Scores (id, away_score, home_score)
    VALUES (%s, %s, %s)
    ON DUPLICATE KEY UPDATE
        away_score = VALUES(away_score),
        home_score = VALUES(home_score)
    """
    score_values = (game_info[0], game_info[3], game_info[4])
    try:
        cursor.execute(upsert_score_query, score_values)
    except Exception as exc:
        print(f"Error updating score: {score_values} ({exc})")

    conn.commit()
    cursor.close()
    conn.close()

def select_game_and_scord(selected_date):
    conn = _connect()
    cursor = conn.cursor()

    select_query = """
    SELECT * FROM Games LEFT JOIN Scores ON Games.id = Scores.id WHERE Games.id LIKE CONCAT('%%', %s, '%%');
    """

    try:
        cursor.execute(select_query, str(selected_date))
        result = cursor.fetchall()
    except:
        result = None

    cursor.close()
    conn.close()

    return result

import pymysql
import settings
from datetime import datetime
from decimal import Decimal
from pathlib import Path


def _require_setting(name, value):
    if not isinstance(value, str) or value == '':
        raise RuntimeError(f'Invalid DB setting: {name}')
    return value


HOST = _require_setting('DB_HOST', settings.DB_HOST)
USER = _require_setting('DB_USER', settings.DB_USER)
PASSWORD = _require_setting('DB_PASSWORD', settings.DB_PASSWORD)
DB = _require_setting('DB_NAME', settings.DB_NAME)

_SCHEMA_READY = False

SQL_DUMP_DIR = Path('data/sql_dumps')

_DUMP_TABLES = (
    ('Standings', ('id', 'team', 'win', 'lose', 'draw', 'rate', 'last_10', 'streak', 'home', 'away')),
    ('Games', ('id', 'time', 'away', 'home', 'stadium', 'remarks')),
    ('Scores', ('id', 'away_score', 'home_score')),
    ('players', ('player_id', 'team_name', 'name', 'position', 'born', 'height_weight', 'salary', 'debut', 'updated_at')),
    ('situational_stats', (
        'id', 'season', 'entity_type', 'entity_id', 'team_name', 'split_type', 'split_key', 'pa', 'ab', 'h',
        'double_hits', 'triple_hits', 'hr', 'rbi', 'bb', 'hbp', 'so', 'gidp', 'wp', 'bk', 'avg', 'obp', 'slg',
        'ops', 'source_updated_at', 'created_at', 'updated_at',
    )),
)

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
    """
    CREATE TABLE IF NOT EXISTS players (
        player_id VARCHAR(32) PRIMARY KEY,
        team_name VARCHAR(32) NOT NULL,
        name VARCHAR(64) NOT NULL,
        position VARCHAR(32),
        born VARCHAR(32),
        height_weight VARCHAR(32),
        salary VARCHAR(32),
        debut VARCHAR(32),
        updated_at DATETIME NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS situational_stats (
        id BIGINT AUTO_INCREMENT PRIMARY KEY,
        season SMALLINT NOT NULL,
        entity_type VARCHAR(16) NOT NULL,
        entity_id VARCHAR(64) NOT NULL,
        team_name VARCHAR(32) NOT NULL,
        split_type VARCHAR(32) NOT NULL,
        split_key VARCHAR(64) NOT NULL,
        pa INT,
        ab INT,
        h INT,
        double_hits INT,
        triple_hits INT,
        hr INT,
        rbi INT,
        bb INT,
        hbp INT,
        so INT,
        gidp INT,
        wp INT,
        bk INT,
        avg DECIMAL(5,3),
        obp DECIMAL(5,3),
        slg DECIMAL(5,3),
        ops DECIMAL(5,3),
        source_updated_at DATETIME,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        UNIQUE KEY uq_situational_stats (season, entity_type, entity_id, split_type, split_key)
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
        for column_name in ('wp', 'bk'):
            cursor.execute("""
            SELECT COUNT(*) FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = %s AND TABLE_NAME = 'situational_stats' AND COLUMN_NAME = %s
            """, (DB, column_name))
            row = cursor.fetchone()
            if row is None or row[0] == 0:
                cursor.execute(f"ALTER TABLE situational_stats ADD COLUMN {column_name} INT AFTER gidp")
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


def _quote_identifier(value):
    return f"`{str(value).replace('`', '``')}`"


def _sql_literal(value):
    if value is None:
        return 'NULL'
    if isinstance(value, bool):
        return '1' if value else '0'
    if isinstance(value, (int, float, Decimal)):
        return str(value)
    if hasattr(value, 'strftime'):
        return f"'{value.strftime('%Y-%m-%d %H:%M:%S')}'"
    text = str(value).replace('\\', '\\\\').replace("'", "''")
    return f"'{text}'"


def export_sql_snapshot(output_dir=None, filename=None):
    target_dir = Path(output_dir) if output_dir is not None else SQL_DUMP_DIR
    target_dir.mkdir(parents=True, exist_ok=True)
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f'kbo_snapshot_{timestamp}.sql'
    dump_path = target_dir / filename

    conn = _connect()
    cursor = conn.cursor()
    try:
        lines = [
            '-- KBO DiscordApp crawler snapshot',
            f'-- Generated at {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}',
            'SET FOREIGN_KEY_CHECKS=0;',
            '',
        ]
        for table_name, _columns in reversed(_DUMP_TABLES):
            lines.append(f'DELETE FROM {_quote_identifier(table_name)};')
        lines.append('')

        for table_name, columns in _DUMP_TABLES:
            column_sql = ', '.join(_quote_identifier(column) for column in columns)
            cursor.execute(f"SELECT {column_sql} FROM {_quote_identifier(table_name)}")
            rows = cursor.fetchall()
            if not rows:
                continue
            lines.append(f'-- {table_name}')
            for row in rows:
                if isinstance(row, dict):
                    values = [row.get(column) for column in columns]
                else:
                    values = list(row)
                value_sql = ', '.join(_sql_literal(value) for value in values)
                lines.append(f'INSERT INTO {_quote_identifier(table_name)} ({column_sql}) VALUES ({value_sql});')
            lines.append('')

        lines.append('SET FOREIGN_KEY_CHECKS=1;')
        dump_path.write_text('\n'.join(lines) + '\n', encoding='utf-8')
        return str(dump_path)
    finally:
        cursor.close()
        conn.close()


def _normalize_name(value):
    return ''.join(str(value).split()).lower()


def _fetchall_as_dicts(cursor, columns):
    rows = cursor.fetchall()
    result = []
    for row in rows:
        if isinstance(row, dict):
            result.append(row)
        else:
            result.append({column: row[index] for index, column in enumerate(columns)})
    return result


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


def upsert_player(player_row):
    conn = _connect()
    cursor = conn.cursor()
    query = """
    INSERT INTO players (player_id, team_name, name, position, born, height_weight, salary, debut, updated_at)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        team_name = VALUES(team_name),
        name = VALUES(name),
        position = VALUES(position),
        born = VALUES(born),
        height_weight = VALUES(height_weight),
        salary = VALUES(salary),
        debut = VALUES(debut),
        updated_at = VALUES(updated_at)
    """
    values = (
        player_row['player_id'],
        player_row['team_name'],
        player_row['name'],
        player_row.get('position'),
        player_row.get('born'),
        player_row.get('height_weight'),
        player_row.get('salary'),
        player_row.get('debut'),
        player_row['updated_at'],
    )
    try:
        cursor.execute(query, values)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def upsert_situational_stat(stat_row):
    conn = _connect()
    cursor = conn.cursor()
    query = """
    INSERT INTO situational_stats (
        season, entity_type, entity_id, team_name, split_type, split_key,
        pa, ab, h, double_hits, triple_hits, hr, rbi, bb, hbp, so, gidp,
        wp, bk, avg, obp, slg, ops, source_updated_at
    )
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON DUPLICATE KEY UPDATE
        team_name = VALUES(team_name),
        pa = VALUES(pa),
        ab = VALUES(ab),
        h = VALUES(h),
        double_hits = VALUES(double_hits),
        triple_hits = VALUES(triple_hits),
        hr = VALUES(hr),
        rbi = VALUES(rbi),
        bb = VALUES(bb),
        hbp = VALUES(hbp),
        so = VALUES(so),
        gidp = VALUES(gidp),
        wp = VALUES(wp),
        bk = VALUES(bk),
        avg = VALUES(avg),
        obp = VALUES(obp),
        slg = VALUES(slg),
        ops = VALUES(ops),
        source_updated_at = VALUES(source_updated_at)
    """
    values = (
        stat_row['season'], stat_row['entity_type'], stat_row['entity_id'], stat_row['team_name'],
        stat_row['split_type'], stat_row['split_key'], stat_row.get('pa'), stat_row.get('ab'),
        stat_row.get('h'), stat_row.get('double_hits'), stat_row.get('triple_hits'), stat_row.get('hr'),
        stat_row.get('rbi'), stat_row.get('bb'), stat_row.get('hbp'), stat_row.get('so'),
        stat_row.get('gidp'), stat_row.get('wp'), stat_row.get('bk'), stat_row.get('avg'), stat_row.get('obp'), stat_row.get('slg'),
        stat_row.get('ops'), stat_row.get('source_updated_at'),
    )
    try:
        cursor.execute(query, values)
        conn.commit()
    finally:
        cursor.close()
        conn.close()


def search_players_by_name(name_query):
    conn = _connect()
    cursor = conn.cursor()
    columns = ['player_id', 'team_name', 'name', 'position', 'born', 'height_weight', 'salary', 'debut', 'updated_at']
    try:
        cursor.execute("""
        SELECT player_id, team_name, name, position, born, height_weight, salary, debut, updated_at
        FROM players
        WHERE name = %s OR REPLACE(LOWER(name), ' ', '') = %s
        ORDER BY CASE WHEN name = %s THEN 0 ELSE 1 END, team_name, name
        """, (name_query, _normalize_name(name_query), name_query))
        return _fetchall_as_dicts(cursor, columns)
    finally:
        cursor.close()
        conn.close()


def get_player_situational_stats(player_id, season, split_key, split_type='runner_state'):
    conn = _connect()
    cursor = conn.cursor()
    columns = [
        'season', 'entity_type', 'entity_id', 'team_name', 'split_type', 'split_key', 'pa', 'ab', 'h',
        'double_hits', 'triple_hits', 'hr', 'rbi', 'bb', 'hbp', 'so', 'gidp', 'wp', 'bk', 'avg', 'obp', 'slg', 'ops',
        'source_updated_at',
    ]
    try:
        cursor.execute("""
        SELECT season, entity_type, entity_id, team_name, split_type, split_key, pa, ab, h,
               double_hits, triple_hits, hr, rbi, bb, hbp, so, gidp, wp, bk, avg, obp, slg, ops, source_updated_at
        FROM situational_stats
        WHERE entity_type = 'player' AND entity_id = %s AND season = %s AND split_type = %s AND split_key = %s
        """, (player_id, season, split_type, split_key))
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return row
        return {column: row[index] for index, column in enumerate(columns)}
    finally:
        cursor.close()
        conn.close()


def _safe_rate(numerator, denominator):
    if denominator in (None, 0):
        return None
    return round(numerator / denominator, 3)


def _calculate_slash_line(totals):
    singles = totals['h'] - totals['double_hits'] - totals['triple_hits'] - totals['hr']
    total_bases = singles + (2 * totals['double_hits']) + (3 * totals['triple_hits']) + (4 * totals['hr'])
    avg = _safe_rate(totals['h'], totals['ab'])
    obp_denominator = totals['ab'] + totals['bb'] + totals['hbp']
    obp = _safe_rate(totals['h'] + totals['bb'] + totals['hbp'], obp_denominator)
    slg = _safe_rate(total_bases, totals['ab'])
    ops = None if obp is None or slg is None else round(obp + slg, 3)
    return avg, obp, slg, ops


def get_team_situational_aggregate(team_name, season, split_key):
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT COUNT(*), COALESCE(SUM(pa), 0), COALESCE(SUM(ab), 0), COALESCE(SUM(h), 0),
               COALESCE(SUM(double_hits), 0), COALESCE(SUM(triple_hits), 0), COALESCE(SUM(hr), 0),
               COALESCE(SUM(rbi), 0), COALESCE(SUM(bb), 0), COALESCE(SUM(hbp), 0),
               COALESCE(SUM(so), 0), COALESCE(SUM(gidp), 0)
        FROM situational_stats
        WHERE entity_type = 'player' AND team_name = %s AND season = %s AND split_type = 'runner_state' AND split_key = %s
        """, (team_name, season, split_key))
        row = cursor.fetchone()
        if row is None or row[0] == 0:
            return None
        totals = {
            'team_name': team_name,
            'season': season,
            'split_key': split_key,
            'pa': row[1], 'ab': row[2], 'h': row[3], 'double_hits': row[4], 'triple_hits': row[5],
            'hr': row[6], 'rbi': row[7], 'bb': row[8], 'hbp': row[9], 'so': row[10], 'gidp': row[11],
        }
        totals['avg'], totals['obp'], totals['slg'], totals['ops'] = _calculate_slash_line(totals)
        return totals
    finally:
        cursor.close()
        conn.close()


def get_team_situational_leaders(team_name, season, split_key, limit=3):
    conn = _connect()
    cursor = conn.cursor()
    columns = ['player_id', 'name', 'team_name', 'pa', 'ab', 'h', 'hr', 'rbi', 'avg', 'ops']
    try:
        cursor.execute("""
        SELECT p.player_id, p.name, s.team_name, s.pa, s.ab, s.h, s.hr, s.rbi, s.avg, s.ops
        FROM situational_stats s
        JOIN players p ON p.player_id = s.entity_id
        WHERE s.entity_type = 'player' AND s.team_name = %s AND s.season = %s AND s.split_type = 'runner_state' AND s.split_key = %s
        ORDER BY s.ops DESC, s.pa DESC, p.name
        LIMIT %s
        """, (team_name, season, split_key, limit))
        return _fetchall_as_dicts(cursor, columns)
    finally:
        cursor.close()
        conn.close()


def get_last_situational_stats_update():
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT MAX(source_updated_at) FROM situational_stats")
        row = cursor.fetchone()
        if row is None:
            return None
        return row[0]
    finally:
        cursor.close()
        conn.close()


def has_situational_stats(split_type):
    conn = _connect()
    cursor = conn.cursor()
    try:
        cursor.execute("""
        SELECT 1 FROM situational_stats
        WHERE entity_type = 'player' AND split_type = %s
        LIMIT 1
        """, (split_type,))
        return cursor.fetchone() is not None
    finally:
        cursor.close()
        conn.close()


def should_refresh_situational_stats(now):
    last_update = get_last_situational_stats_update()
    if last_update is None:
        return True
    if hasattr(last_update, 'date'):
        return last_update.date() < now.date()
    return True


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

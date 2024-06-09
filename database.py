import pymysql
import json

with open('config.json') as f:
    data = json.load(f)
    HOST= data['MARIA']['HOST']
    USER = data['MARIA']['USER']
    PASSWORD = data['MARIA']['PASSWORD']
    DB = data['MARIA']['DB']
def insert_standings(game_info):
    # Connect to the database
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, db=DB, charset='utf8')
    cursor = conn.cursor()

    # Insert into Standings table
    insert_standings_query = """
    INSERT INTO Standings (id, team, win, lose, draw, rate, last_10, streak, home, away)
    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    standings_values = (game_info[0], game_info[1], game_info[2], game_info[3], game_info[4], game_info[5], game_info[6], game_info[7], game_info[8], game_info[9])
    try:
        cursor.execute(insert_standings_query, standings_values)
    except:
        print(f"Error inserting standings: {standings_values}")

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

def update_standings(game_info):
    # Connect to the database
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, db=DB, charset='utf8')
    cursor = conn.cursor()

    # Insert into Standings table
    update_standings_query = """
    UPDATE Standings SET team = %s, win = %s, lose = %s, draw = %s, rate = %s, last_10 = %s, streak = %s, home = %s, away = %s WHERE id = %s
    """
    standings_values = (game_info[1], game_info[2], game_info[3], game_info[4], game_info[5], game_info[6], game_info[7], game_info[8], game_info[9]. game_info[0])
    try:
        cursor.execute(update_standings_query, standings_values)
    except:
        print(f"Error inserting standings: {standings_values}")

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()

def select_standings():
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, db=DB, charset='utf8')
    cursor = conn.cursor()

    select_query = """
    SELECT * FROM Standings
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
    conn = pymysql.connect(host=HOST, user=USER, password=PASSWORD, db=DB, charset='utf8')
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

def select_game_and_scord(selected_date):
    conn =pymysql.connect(host=HOST, user=USER, password=PASSWORD, db=DB, charset='utf8')
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
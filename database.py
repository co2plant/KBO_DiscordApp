import pymysql
import json

with open('config.json') as f:
    data = json.load(f)
    HOST= data['MARIA']['HOST']
    USER = data['MARIA']['USER']
    PASSWORD = data['MARIA']['PASSWORD']
    DB = data['MARIA']['DB']

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
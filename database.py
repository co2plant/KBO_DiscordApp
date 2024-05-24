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
    conn = pymysql.connect(host='localhost', user=USER, password=PASSWORD, db=DB, charset='utf8')
    cursor = conn.cursor()

    game_info

    # Prepare game_id from game_date and game_number
    game_date = game_info['game_date']
    game_number = game_info['game_number']
    game_id = f"{game_date.month}{game_date.day}{game_number}"

    # Insert into Games table
    insert_game_query = """
    INSERT INTO Games (id, time, away, home, stadium, remarks)
    VALUES (%s, %s, %s, %s, %s, %s)
    """
    game_values = (game_id,  game_info['game_time'], game_info['away_team'],
                   game_info['home_team'], game_info['stadium'], game_info['remarks'])
    cursor.execute(insert_game_query, game_values)

    # Insert into Scores table
    insert_score_query = """
    INSERT INTO Scores (game_id, away_score, home_score)
    VALUES (%s, %s, %s)
    """
    score_values = (game_id, away_score, home_score)
    cursor.execute(insert_score_query, score_values)

    # Commit and close
    conn.commit()
    cursor.close()
    conn.close()
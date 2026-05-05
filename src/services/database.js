import { config } from '../config.js';

let pool;
let schemaReady = false;

async function getPool() {
  if (!pool) {
    const mysql = await import('mysql2/promise');
    pool = mysql.createPool({
      host: config.db.host,
      user: config.db.user,
      password: config.db.password,
      database: config.db.database,
      charset: 'utf8mb4',
      waitForConnections: true,
      connectionLimit: 10
    });
  }

  return pool;
}

async function execute(sql, params = []) {
  const db = await getPool();
  return db.execute(sql, params);
}

export async function closePool() {
  if (pool) {
    await pool.end();
    pool = undefined;
    schemaReady = false;
  }
}

export async function ensureSchema() {
  if (schemaReady) {
    return;
  }

  await execute(`
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
  `);
  await execute(`
    CREATE TABLE IF NOT EXISTS Games (
      id VARCHAR(16) PRIMARY KEY,
      time VARCHAR(16) NOT NULL,
      away VARCHAR(32) NOT NULL,
      home VARCHAR(32) NOT NULL,
      stadium VARCHAR(64) NOT NULL,
      remarks VARCHAR(64) NOT NULL
    )
  `);
  await execute(`
    CREATE TABLE IF NOT EXISTS Scores (
      id VARCHAR(16) PRIMARY KEY,
      away_score INT NOT NULL,
      home_score INT NOT NULL,
      CONSTRAINT fk_scores_game FOREIGN KEY (id) REFERENCES Games(id) ON DELETE CASCADE
    )
  `);
  await execute(`
    CREATE TABLE IF NOT EXISTS Players (
      player_id VARCHAR(16) PRIMARY KEY,
      name VARCHAR(32) NOT NULL,
      team VARCHAR(32) NOT NULL,
      team_name VARCHAR(64) NOT NULL,
      back_no VARCHAR(16) NOT NULL,
      position VARCHAR(64) NOT NULL,
      birthday VARCHAR(32) NOT NULL,
      height_weight VARCHAR(64) NOT NULL,
      career TEXT NOT NULL,
      payment VARCHAR(64) NOT NULL,
      salary VARCHAR(64) NOT NULL,
      draft VARCHAR(128) NOT NULL,
      join_info VARCHAR(64) NOT NULL,
      profile_image_url VARCHAR(512) NOT NULL,
      detail_url VARCHAR(512) NOT NULL,
      detail_type VARCHAR(16) NOT NULL,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_players_name_team (name, team)
    )
  `);
  await execute(`
    CREATE TABLE IF NOT EXISTS UserAlerts (
      id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
      discord_user_id VARCHAR(32) NOT NULL,
      alert_type VARCHAR(32) NOT NULL,
      team VARCHAR(32) NOT NULL,
      notify_before_minutes INT NOT NULL DEFAULT 10,
      enabled TINYINT(1) NOT NULL DEFAULT 1,
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      UNIQUE KEY uq_user_alert (discord_user_id, alert_type, team),
      INDEX idx_user_alerts_enabled (enabled, team, alert_type)
    )
  `);
  await execute(`
    CREATE TABLE IF NOT EXISTS AlertDeliveries (
      delivery_key VARCHAR(128) PRIMARY KEY,
      discord_user_id VARCHAR(32) NOT NULL,
      alert_type VARCHAR(32) NOT NULL,
      game_id VARCHAR(32) NOT NULL,
      status VARCHAR(16) NOT NULL DEFAULT 'pending',
      error_message VARCHAR(512) NOT NULL DEFAULT '',
      created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
      sent_at TIMESTAMP NULL DEFAULT NULL,
      INDEX idx_alert_deliveries_user (discord_user_id, created_at),
      INDEX idx_alert_deliveries_game (game_id, alert_type)
    )
  `);
  await execute(`
    CREATE TABLE IF NOT EXISTS ScoreSnapshots (
      snapshot_key VARCHAR(64) PRIMARY KEY,
      game_date VARCHAR(10) NOT NULL,
      game_id VARCHAR(32) NOT NULL,
      time VARCHAR(16) NOT NULL,
      away VARCHAR(32) NOT NULL,
      home VARCHAR(32) NOT NULL,
      stadium VARCHAR(64) NOT NULL,
      remarks VARCHAR(64) NOT NULL,
      away_score INT NOT NULL,
      home_score INT NOT NULL,
      leader_team VARCHAR(32) NOT NULL,
      updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      INDEX idx_score_snapshots_game_id (game_id),
      INDEX idx_score_snapshots_game_date (game_date)
    )
  `);
  const [indexes] = await execute("SHOW INDEX FROM Standings WHERE Key_name = 'PRIMARY'");
  const primaryColumns = indexes.map((row) => row.Column_name);
  if (primaryColumns.length > 0 && !(primaryColumns.length === 1 && primaryColumns[0] === 'team')) {
    await execute('ALTER TABLE Standings DROP PRIMARY KEY, ADD PRIMARY KEY (team)');
  }

  schemaReady = true;
}

export async function hasStandingsData() {
  await ensureSchema();
  const [rows] = await execute('SELECT COUNT(*) AS count FROM Standings');
  return Number(rows[0]?.count ?? 0) >= 10;
}

export async function hasScheduleDataForDate(selectedDate) {
  await ensureSchema();
  const [rows] = await execute(
    "SELECT 1 FROM Games WHERE id LIKE CONCAT(?, '%') LIMIT 1",
    [String(selectedDate)]
  );
  return rows.length > 0;
}

export async function upsertStandings(row) {
  await ensureSchema();
  await execute(
    `
      INSERT INTO Standings (id, team, win, lose, draw, rate, last_10, streak, home, away)
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
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
    `,
    [row.id, row.team, row.win, row.lose, row.draw, row.rate, row.last10, row.streak, row.home, row.away]
  );
}

export async function selectStandings() {
  await ensureSchema();
  const [rows] = await execute('SELECT * FROM Standings ORDER BY CAST(id AS UNSIGNED), team');
  return rows.map((row) => ({
    id: String(row.id),
    team: row.team,
    win: row.win,
    lose: row.lose,
    draw: row.draw,
    rate: String(row.rate),
    last10: row.last_10,
    streak: row.streak,
    home: row.home,
    away: row.away
  }));
}

function mapPlayer(row) {
  return {
    playerId: row.player_id,
    name: row.name,
    team: row.team,
    teamName: row.team_name,
    backNo: row.back_no,
    position: row.position,
    birthday: row.birthday,
    heightWeight: row.height_weight,
    career: row.career,
    payment: row.payment,
    salary: row.salary,
    draft: row.draft,
    joinInfo: row.join_info,
    profileImageUrl: row.profile_image_url,
    detailUrl: row.detail_url,
    detailType: row.detail_type
  };
}

export async function selectPlayerById(playerId) {
  await ensureSchema();
  const [rows] = await execute('SELECT * FROM Players WHERE player_id = ? LIMIT 1', [String(playerId)]);
  return rows[0] ? mapPlayer(rows[0]) : null;
}

export async function selectPlayersByName(name) {
  await ensureSchema();
  const [rows] = await execute(
    'SELECT * FROM Players WHERE name = ? ORDER BY team, CAST(back_no AS UNSIGNED), player_id',
    [String(name)]
  );
  return rows.map(mapPlayer);
}

export async function selectPlayerByNameAndTeam(name, team) {
  await ensureSchema();
  const [rows] = await execute(
    'SELECT * FROM Players WHERE name = ? AND UPPER(team) = UPPER(?) ORDER BY player_id LIMIT 1',
    [String(name), String(team)]
  );
  return rows[0] ? mapPlayer(rows[0]) : null;
}

export async function upsertPlayer(player) {
  await ensureSchema();
  await execute(
    `
      INSERT INTO Players (
        player_id,
        name,
        team,
        team_name,
        back_no,
        position,
        birthday,
        height_weight,
        career,
        payment,
        salary,
        draft,
        join_info,
        profile_image_url,
        detail_url,
        detail_type
      )
      VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
        name = VALUES(name),
        team = VALUES(team),
        team_name = VALUES(team_name),
        back_no = VALUES(back_no),
        position = VALUES(position),
        birthday = VALUES(birthday),
        height_weight = VALUES(height_weight),
        career = VALUES(career),
        payment = VALUES(payment),
        salary = VALUES(salary),
        draft = VALUES(draft),
        join_info = VALUES(join_info),
        profile_image_url = VALUES(profile_image_url),
        detail_url = VALUES(detail_url),
        detail_type = VALUES(detail_type)
    `,
    [
      player.playerId,
      player.name,
      player.team,
      player.teamName,
      player.backNo,
      player.position,
      player.birthday,
      player.heightWeight,
      player.career,
      player.payment,
      player.salary,
      player.draft,
      player.joinInfo,
      player.profileImageUrl,
      player.detailUrl,
      player.detailType
    ]
  );
}

function mapUserAlert(row) {
  return {
    id: Number(row.id),
    discordUserId: row.discord_user_id,
    alertType: row.alert_type,
    team: row.team,
    notifyBeforeMinutes: Number(row.notify_before_minutes),
    enabled: Boolean(row.enabled)
  };
}

export async function upsertUserAlert(alert) {
  await ensureSchema();
  await execute(
    `
      INSERT INTO UserAlerts (discord_user_id, alert_type, team, notify_before_minutes, enabled)
      VALUES (?, ?, ?, ?, 1)
      ON DUPLICATE KEY UPDATE
        notify_before_minutes = VALUES(notify_before_minutes),
        enabled = 1
    `,
    [
      String(alert.discordUserId),
      alert.alertType,
      alert.team,
      alert.notifyBeforeMinutes
    ]
  );
}

export async function deleteUserAlert(alert) {
  await ensureSchema();
  const [result] = await execute(
    `
      DELETE FROM UserAlerts
      WHERE discord_user_id = ?
        AND alert_type = ?
        AND team = ?
    `,
    [String(alert.discordUserId), alert.alertType, alert.team]
  );
  return Number(result.affectedRows ?? 0) > 0;
}

export async function selectUserAlerts(discordUserId) {
  await ensureSchema();
  const [rows] = await execute(
    `
      SELECT *
      FROM UserAlerts
      WHERE discord_user_id = ?
      ORDER BY team, alert_type
    `,
    [String(discordUserId)]
  );
  return rows.map(mapUserAlert);
}

export async function selectEnabledUserAlerts() {
  await ensureSchema();
  const [rows] = await execute(
    `
      SELECT *
      FROM UserAlerts
      WHERE enabled = 1
      ORDER BY team, alert_type, discord_user_id
    `
  );
  return rows.map(mapUserAlert);
}

export async function claimAlertDelivery(delivery) {
  await ensureSchema();
  try {
    await execute(
      `
        INSERT INTO AlertDeliveries (
          delivery_key,
          discord_user_id,
          alert_type,
          game_id,
          status
        )
        VALUES (?, ?, ?, ?, 'pending')
      `,
      [
        delivery.deliveryKey,
        String(delivery.discordUserId),
        delivery.alertType,
        delivery.gameId
      ]
    );
    return true;
  } catch (error) {
    if (error.code === 'ER_DUP_ENTRY') {
      return false;
    }

    throw error;
  }
}

export async function markAlertDeliverySent(deliveryKey) {
  await ensureSchema();
  await execute(
    `
      UPDATE AlertDeliveries
      SET status = 'sent',
          error_message = '',
          sent_at = CURRENT_TIMESTAMP
      WHERE delivery_key = ?
    `,
    [deliveryKey]
  );
}

export async function markAlertDeliveryFailed(deliveryKey, errorMessage) {
  await ensureSchema();
  await execute(
    `
      UPDATE AlertDeliveries
      SET status = 'failed',
          error_message = ?
      WHERE delivery_key = ?
    `,
    [String(errorMessage ?? '').slice(0, 512), deliveryKey]
  );
}

function mapScoreSnapshot(row) {
  return {
    snapshotKey: row.snapshot_key,
    gameDate: row.game_date,
    gameId: row.game_id,
    time: row.time,
    away: row.away,
    home: row.home,
    stadium: row.stadium,
    remarks: row.remarks,
    awayScore: Number(row.away_score),
    homeScore: Number(row.home_score),
    leaderTeam: row.leader_team
  };
}

export async function selectScoreSnapshots(selectedDateKey) {
  await ensureSchema();
  const [rows] = await execute(
    `
      SELECT *
      FROM ScoreSnapshots
      WHERE game_id LIKE CONCAT(?, '%')
      ORDER BY game_id
    `,
    [String(selectedDateKey)]
  );
  return rows.map(mapScoreSnapshot);
}

export async function upsertScoreSnapshots(snapshots) {
  await ensureSchema();
  for (const snapshot of snapshots ?? []) {
    await execute(
      `
        INSERT INTO ScoreSnapshots (
          snapshot_key,
          game_date,
          game_id,
          time,
          away,
          home,
          stadium,
          remarks,
          away_score,
          home_score,
          leader_team
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ON DUPLICATE KEY UPDATE
          time = VALUES(time),
          away = VALUES(away),
          home = VALUES(home),
          stadium = VALUES(stadium),
          remarks = VALUES(remarks),
          away_score = VALUES(away_score),
          home_score = VALUES(home_score),
          leader_team = VALUES(leader_team)
      `,
      [
        snapshot.snapshotKey,
        snapshot.gameDate,
        snapshot.gameId,
        snapshot.time,
        snapshot.away,
        snapshot.home,
        snapshot.stadium,
        snapshot.remarks,
        snapshot.awayScore,
        snapshot.homeScore,
        snapshot.leaderTeam
      ]
    );
  }
}

export async function upsertGameAndScore(game) {
  await ensureSchema();
  await execute(
    `
      INSERT INTO Games (id, time, away, home, stadium, remarks)
      VALUES (?, ?, ?, ?, ?, ?)
      ON DUPLICATE KEY UPDATE
        time = VALUES(time),
        away = VALUES(away),
        home = VALUES(home),
        stadium = VALUES(stadium),
        remarks = VALUES(remarks)
    `,
    [game.id, game.time, game.away, game.home, game.stadium, game.remarks]
  );
  await execute(
    `
      INSERT INTO Scores (id, away_score, home_score)
      VALUES (?, ?, ?)
      ON DUPLICATE KEY UPDATE
        away_score = VALUES(away_score),
        home_score = VALUES(home_score)
    `,
    [game.id, game.awayScore, game.homeScore]
  );
}

export async function updateLiveGameScore(game) {
  await ensureSchema();
  const [rows] = await execute(
    `
      SELECT id FROM Games
      WHERE id LIKE CONCAT(?, '%')
        AND away = ?
        AND home = ?
        AND time = ?
      LIMIT 1
    `,
    [String(game.selectedDate), game.away, game.home, game.time]
  );

  if (rows.length === 0) {
    console.log(`[crawl:live-score] DB target not found ${game.selectedDate} ${game.time} ${game.away}-${game.home}`);
    return false;
  }

  const id = rows[0].id;
  await execute('UPDATE Games SET remarks = ? WHERE id = ?', [game.remarks, id]);
  await execute(
    `
      INSERT INTO Scores (id, away_score, home_score)
      VALUES (?, ?, ?)
      ON DUPLICATE KEY UPDATE
        away_score = VALUES(away_score),
        home_score = VALUES(home_score)
    `,
    [id, game.awayScore, game.homeScore]
  );
  return true;
}

export async function selectGamesAndScores(selectedDate) {
  await ensureSchema();
  const [rows] = await execute(
    `
      SELECT
        Games.id,
        Games.time,
        Games.away,
        Games.home,
        Games.stadium,
        Games.remarks,
        Scores.away_score AS awayScore,
        Scores.home_score AS homeScore
      FROM Games
      LEFT JOIN Scores ON Games.id = Scores.id
      WHERE Games.id LIKE CONCAT(?, '%')
      ORDER BY Games.time, Games.id
    `,
    [String(selectedDate)]
  );

  return rows.map((row) => ({
    id: row.id,
    time: row.time,
    away: row.away,
    home: row.home,
    stadium: row.stadium,
    remarks: row.remarks,
    awayScore: row.awayScore,
    homeScore: row.homeScore
  }));
}

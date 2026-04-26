const mysql = require('mysql2/promise');

const { config } = require('./config');

let schemaReady = false;

const schemaStatements = [
  `
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
  `,
  `
  CREATE TABLE IF NOT EXISTS Games (
    id VARCHAR(16) PRIMARY KEY,
    time VARCHAR(16) NOT NULL,
    away VARCHAR(32) NOT NULL,
    home VARCHAR(32) NOT NULL,
    stadium VARCHAR(64) NOT NULL,
    remarks VARCHAR(64) NOT NULL
  )
  `,
  `
  CREATE TABLE IF NOT EXISTS Scores (
    id VARCHAR(16) PRIMARY KEY,
    away_score INT NOT NULL,
    home_score INT NOT NULL,
    CONSTRAINT fk_scores_game FOREIGN KEY (id) REFERENCES Games(id) ON DELETE CASCADE
  )
  `,
];

async function createConnection() {
  const connection = await mysql.createConnection({
    host: config.dbHost,
    user: config.dbUser,
    password: config.dbPassword,
    database: config.dbName,
    charset: 'utf8',
  });
  await ensureSchema(connection);
  return connection;
}

async function ensureSchema(existingConnection) {
  if (schemaReady) {
    return;
  }

  const connection = existingConnection || await mysql.createConnection({
    host: config.dbHost,
    user: config.dbUser,
    password: config.dbPassword,
    database: config.dbName,
    charset: 'utf8',
  });

  try {
    for (const statement of schemaStatements) {
      await connection.execute(statement);
    }

    const [indexes] = await connection.execute("SHOW INDEX FROM Standings WHERE Key_name = 'PRIMARY'");
    const primaryColumns = indexes.map(row => row.Column_name);
    if (primaryColumns.length > 0 && (primaryColumns.length !== 1 || primaryColumns[0] !== 'team')) {
      await connection.execute('ALTER TABLE Standings DROP PRIMARY KEY, ADD PRIMARY KEY (team)');
    }

    schemaReady = true;
  } finally {
    if (!existingConnection) {
      await connection.end();
    }
  }
}

async function hasStandingsData() {
  const connection = await createConnection();
  try {
    const [rows] = await connection.execute('SELECT COUNT(*) AS count FROM Standings');
    return rows.length > 0 && rows[0].count >= 10;
  } finally {
    await connection.end();
  }
}

async function hasScheduleData() {
  const connection = await createConnection();
  try {
    const [rows] = await connection.execute('SELECT 1 FROM Games LIMIT 1');
    return rows.length > 0;
  } finally {
    await connection.end();
  }
}

async function upsertStandings(gameInfo) {
  const connection = await createConnection();
  const query = `
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
  `;

  try {
    await connection.execute(query, gameInfo);
  } finally {
    await connection.end();
  }
}

async function selectStandings() {
  const connection = await createConnection();
  try {
    const [rows] = await connection.execute('SELECT * FROM Standings ORDER BY CAST(id AS UNSIGNED), team');
    return rows;
  } finally {
    await connection.end();
  }
}

async function insertGameAndScore(gameInfo) {
  const connection = await createConnection();
  try {
    await connection.execute(
      'INSERT INTO Games (id, time, away, home, stadium, remarks) VALUES (?, ?, ?, ?, ?, ?)',
      [gameInfo[0], gameInfo[1], gameInfo[2], gameInfo[5], gameInfo[6], gameInfo[7]],
    );
    await connection.execute(
      'INSERT INTO Scores (id, away_score, home_score) VALUES (?, ?, ?)',
      [gameInfo[0], gameInfo[3], gameInfo[4]],
    );
  } finally {
    await connection.end();
  }
}

async function updateGameAndScore(gameInfo) {
  const connection = await createConnection();
  try {
    await connection.execute(
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
      [gameInfo[0], gameInfo[1], gameInfo[2], gameInfo[5], gameInfo[6], gameInfo[7]],
    );
    await connection.execute(
      `
      INSERT INTO Scores (id, away_score, home_score)
      VALUES (?, ?, ?)
      ON DUPLICATE KEY UPDATE
        away_score = VALUES(away_score),
        home_score = VALUES(home_score)
      `,
      [gameInfo[0], gameInfo[3], gameInfo[4]],
    );
  } finally {
    await connection.end();
  }
}

async function selectGameAndScore(selectedDate) {
  const connection = await createConnection();
  try {
    const [rows] = await connection.execute(
      "SELECT * FROM Games LEFT JOIN Scores ON Games.id = Scores.id WHERE Games.id LIKE CONCAT('%', ?, '%')",
      [String(selectedDate)],
    );
    return rows;
  } finally {
    await connection.end();
  }
}

module.exports = {
  ensureSchema,
  hasScheduleData,
  hasStandingsData,
  insertGameAndScore,
  selectGameAndScore,
  selectStandings,
  updateGameAndScore,
  upsertStandings,
};

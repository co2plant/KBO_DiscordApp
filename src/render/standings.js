const { EMOJI, LOGO_EMOJI } = require('../constants');

function normalizeTeamName(teamName) {
  return teamName.trim().toUpperCase();
}

function findStandingsTeam(rows, teamName) {
  const normalizedTeamName = normalizeTeamName(teamName);
  return rows.find(row => normalizeTeamName(row.team) === normalizedTeamName);
}

function isHotStreak(streak) {
  const trimmedStreak = String(streak).trim();
  if (!trimmedStreak.endsWith('승')) {
    return false;
  }

  const winCount = trimmedStreak.slice(0, -1);
  return /^\d+$/.test(winCount) && Number.parseInt(winCount, 10) >= 3;
}

function buildStandingsLines(rows) {
  const lines = ['순위 | 팀 | 승 | 패 | 무 | 승률'];
  rows.forEach((row, index) => {
    const hotStreak = isHotStreak(row.streak) ? ' 🔥' : '';
    lines.push(`${EMOJI[index + 1]} | ${LOGO_EMOJI[row.team]} ${row.team}${hotStreak} | ${row.win} | ${row.lose} | ${row.draw} | ${row.rate}`);
  });
  return lines;
}

module.exports = { buildStandingsLines, findStandingsTeam, isHotStreak, normalizeTeamName };

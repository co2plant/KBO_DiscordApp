const { DAYS, EMOJI, LOGO_EMOJI } = require('../constants');
const { formatIsoDate, formatKoreanMonthDay, getKoreanWeekday, nowKst } = require('../time');

function parseScheduleScore(score) {
  if (score === -1 || score === '-1') {
    return 0;
  }
  return Number.parseInt(score, 10);
}

function shouldHideScheduleScore(selectedDate, gameTime, remarks, awayScore, homeScore, now = nowKst()) {
  if (remarks !== '' && remarks !== '-') {
    return false;
  }

  if (awayScore !== 0 || homeScore !== 0) {
    return false;
  }

  const timeParts = String(gameTime).split(':');
  if (timeParts.length !== 2) {
    return false;
  }

  const scheduledDate = new Date(selectedDate.getTime());
  scheduledDate.setUTCHours(Number.parseInt(timeParts[0], 10), Number.parseInt(timeParts[1], 10), 0, 0);

  return selectedDate.toISOString().slice(0, 10) >= now.toISOString().slice(0, 10) && now < scheduledDate;
}

function formatScheduleMatchup(selectedDate, row, now = new Date()) {
  const awayScore = parseScheduleScore(row.away_score);
  const homeScore = parseScheduleScore(row.home_score);
  const scoreText = shouldHideScheduleScore(selectedDate, row.time, row.remarks, awayScore, homeScore, now)
    ? 'vs'
    : `${awayScore} vs ${homeScore}`;

  return `${row.away.padEnd(10)} ${LOGO_EMOJI[row.away]} ${scoreText} ${LOGO_EMOJI[row.home]} ${row.home.padEnd(10)}`;
}

function buildScheduleEmbedData(selectedDate, rows) {
  const weekday = getKoreanWeekday(selectedDate);
  const title = `${formatKoreanMonthDay(selectedDate)} ${DAYS[weekday]}요일 KBO 경기 일정`;
  const url = `https://m.sports.naver.com/kbaseball/schedule/index?date=${formatIsoDate(selectedDate)}`;

  const columns = ['', '', ''];
  rows.forEach((row, index) => {
    columns[0] += `${EMOJI[index + 1]} ${row.time}\n`;
    columns[1] += `${formatScheduleMatchup(selectedDate, row)}\n`;
    columns[2] += `${row.stadium}${row.remarks}\n`;
  });

  return { columns, title, url };
}

module.exports = { buildScheduleEmbedData, formatScheduleMatchup, parseScheduleScore, shouldHideScheduleScore };

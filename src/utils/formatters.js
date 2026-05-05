import { logoEmoji } from '../constants.js';

const FINAL_GAME_REMARKS = ['경기종료', '종료', '취소'];
const LIVE_SCORE_REFRESH_LEAD_MINUTES = 10;

export function normalizeTeamName(teamName) {
  return String(teamName ?? '').trim().toUpperCase();
}

export function isHotStreak(streak) {
  const match = String(streak ?? '').trim().match(/^(\d+)연승$/);
  return Boolean(match) && Number.parseInt(match[1], 10) >= 3;
}

export function findTeamGames(games, teamName) {
  const normalized = normalizeTeamName(teamName);
  return games.filter((game) => (
    normalizeTeamName(game.away) === normalized || normalizeTeamName(game.home) === normalized
  ));
}

export function findStandingsTeam(standings, teamName) {
  const normalized = normalizeTeamName(teamName);
  return standings.find((team) => normalizeTeamName(team.team) === normalized) ?? null;
}

function normalizeScore(score) {
  return score === null || score === undefined || score === '' || Number(score) === -1 ? 0 : Number(score);
}

function getGameDateTime(selectedDate, gameTime) {
  const match = String(gameTime ?? '').match(/^(\d{1,2}):(\d{2})$/);
  if (!match) {
    return null;
  }

  const date = new Date(selectedDate.getTime());
  date.setUTCHours(Number.parseInt(match[1], 10), Number.parseInt(match[2], 10), 0, 0);
  return date;
}

export function isFinalGameStatus(remarks) {
  const value = String(remarks ?? '');
  return FINAL_GAME_REMARKS.some((finalStatus) => value.includes(finalStatus));
}

export function shouldHideScheduleScore(selectedDate, game, options = {}) {
  const awayScore = normalizeScore(game.awayScore);
  const homeScore = normalizeScore(game.homeScore);
  if (!['', '-'].includes(String(game.remarks ?? ''))) {
    return false;
  }

  if (awayScore !== 0 || homeScore !== 0) {
    return false;
  }

  const scheduledDate = getGameDateTime(selectedDate, game.time);
  if (!scheduledDate) {
    return false;
  }

  const now = options.now ?? new Date();
  if (selectedDate.toISOString().slice(0, 10) > now.toISOString().slice(0, 10)) {
    return true;
  }
  if (selectedDate.toISOString().slice(0, 10) < now.toISOString().slice(0, 10)) {
    return false;
  }

  return now < scheduledDate;
}

export function formatScheduleMatchup(selectedDate, game, options = {}) {
  const awayScore = normalizeScore(game.awayScore);
  const homeScore = normalizeScore(game.homeScore);
  const scoreText = shouldHideScheduleScore(selectedDate, game, options) ? 'vs' : `${awayScore} vs ${homeScore}`;
  const awayLogo = logoEmoji[game.away] ?? '';
  const homeLogo = logoEmoji[game.home] ?? '';
  return `${game.away} ${awayLogo} ${scoreText} ${homeLogo} ${game.home}`;
}

export function formatScoreLine(selectedDate, game, options = {}) {
  const awayScore = normalizeScore(game.awayScore);
  const homeScore = normalizeScore(game.homeScore);
  let scoreText = `${awayScore} vs ${homeScore}`;
  let statusText = game.remarks && game.remarks !== '-' ? game.remarks : '진행/종료';

  if (shouldHideScheduleScore(selectedDate, game, options)) {
    scoreText = 'vs';
    statusText = '경기 전';
  }

  const awayLogo = logoEmoji[game.away] ?? '';
  const homeLogo = logoEmoji[game.home] ?? '';
  return `${game.time} | ${awayLogo} ${game.away} ${scoreText} ${homeLogo} ${game.home} | ${game.stadium} | ${statusText}`;
}

export function shouldRefreshLiveScores(selectedDate, games, options = {}) {
  if (!games?.length) {
    return false;
  }

  const now = options.now ?? new Date();
  if (selectedDate.toISOString().slice(0, 10) !== now.toISOString().slice(0, 10)) {
    return false;
  }

  return games.some((game) => {
    if (isFinalGameStatus(game.remarks)) {
      return false;
    }

    const scheduledDate = getGameDateTime(selectedDate, game.time);
    if (!scheduledDate) {
      return false;
    }

    return now >= new Date(scheduledDate.getTime() - LIVE_SCORE_REFRESH_LEAD_MINUTES * 60 * 1000);
  });
}

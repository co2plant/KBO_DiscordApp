import { logoEmoji } from '../constants.js';
import {
  isFinalGameStatus,
  normalizeTeamName
} from '../utils/formatters.js';

function normalizeScore(score) {
  return score === null || score === undefined || score === '' || Number(score) === -1 ? 0 : Number(score);
}

function isCancelledStatus(remarks) {
  return String(remarks ?? '').includes('취소');
}

function findDisplayTeam(game, requestedTeam) {
  const requested = normalizeTeamName(requestedTeam);
  if (normalizeTeamName(game.away) === requested) {
    return game.away;
  }
  if (normalizeTeamName(game.home) === requested) {
    return game.home;
  }
  return requestedTeam;
}

function buildScoreLine(game) {
  const awayLogo = logoEmoji[game.away] ?? '';
  const homeLogo = logoEmoji[game.home] ?? '';
  return `${awayLogo} ${game.away} ${normalizeScore(game.awayScore)} vs ${normalizeScore(game.homeScore)} ${homeLogo} ${game.home}`.trim();
}

function winnerSummary(game) {
  const awayScore = normalizeScore(game.awayScore);
  const homeScore = normalizeScore(game.homeScore);
  if (awayScore === homeScore) {
    return `${game.away}와 ${game.home}가 ${awayScore} vs ${homeScore} 무승부로 경기를 마쳤습니다.`;
  }

  const winner = awayScore > homeScore ? game.away : game.home;
  const diff = Math.abs(awayScore - homeScore);
  return `${winner}가 ${diff}점 차로 승리했습니다.`;
}

function liveSummary(game) {
  const awayScore = normalizeScore(game.awayScore);
  const homeScore = normalizeScore(game.homeScore);
  if (awayScore === 0 && homeScore === 0 && ['', '-'].includes(String(game.remarks ?? ''))) {
    return `${game.time} ${game.stadium} 경기 시작 전입니다.`;
  }
  if (awayScore === homeScore) {
    return `${game.away}와 ${game.home}가 ${awayScore} vs ${homeScore} 동점입니다.`;
  }

  const leader = awayScore > homeScore ? game.away : game.home;
  const diff = Math.abs(awayScore - homeScore);
  return `${leader}가 ${diff}점 차로 앞서고 있습니다.`;
}

export function buildGameSummary(game, requestedTeam) {
  const teamName = findDisplayTeam(game, requestedTeam);
  const remarks = game.remarks && game.remarks !== '-' ? game.remarks : '경기 전';
  const context = `${game.time} | ${game.stadium} | ${remarks}`;
  let summary;

  if (isCancelledStatus(game.remarks)) {
    summary = `${game.time} ${game.stadium} 경기는 ${game.remarks} 상태입니다.`;
  } else if (isFinalGameStatus(game.remarks)) {
    summary = winnerSummary(game);
  } else {
    summary = liveSummary(game);
  }

  return {
    title: `${teamName} 경기 요약`,
    teamName,
    scoreLine: buildScoreLine(game),
    context,
    summary
  };
}

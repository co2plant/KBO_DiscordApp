import { logoEmoji, toYmd } from '../constants.js';
import {
  isFinalGameStatus,
  normalizeTeamName
} from '../utils/formatters.js';

export const ALERT_TYPES = Object.freeze({
  GAME_START: 'game_start',
  GAME_RESULT: 'game_result',
  SCORE_CHANGE: 'score_change',
  LEAD_CHANGE: 'lead_change',
  GAME_CANCELLED: 'game_cancelled'
});

export const ALERT_TYPE_LABELS = Object.freeze({
  [ALERT_TYPES.GAME_START]: '경기 시작',
  [ALERT_TYPES.GAME_RESULT]: '경기 종료',
  [ALERT_TYPES.SCORE_CHANGE]: '득점',
  [ALERT_TYPES.LEAD_CHANGE]: '역전',
  [ALERT_TYPES.GAME_CANCELLED]: '경기 취소'
});

export const DEFAULT_NOTIFY_BEFORE_MINUTES = 10;
export const MIN_NOTIFY_BEFORE_MINUTES = 1;
export const MAX_NOTIFY_BEFORE_MINUTES = 60;

const EVENT_ALERT_TYPES = new Set([
  ALERT_TYPES.SCORE_CHANGE,
  ALERT_TYPES.LEAD_CHANGE,
  ALERT_TYPES.GAME_CANCELLED
]);

function getGameDateTime(selectedDate, gameTime) {
  const match = String(gameTime ?? '').match(/^(\d{1,2}):(\d{2})$/);
  if (!match) {
    return null;
  }

  const date = new Date(selectedDate.getTime());
  date.setUTCHours(Number.parseInt(match[1], 10), Number.parseInt(match[2], 10), 0, 0);
  return date;
}

function normalizeScore(score) {
  return score === null || score === undefined || score === '' || Number(score) === -1 ? 0 : Number(score);
}

function isTeamInGame(team, game) {
  const normalized = normalizeTeamName(team);
  return normalizeTeamName(game.away) === normalized || normalizeTeamName(game.home) === normalized;
}

export function normalizeAlertTeam(teamName) {
  const normalized = normalizeTeamName(teamName);
  return Object.keys(logoEmoji).find((team) => normalizeTeamName(team) === normalized) ?? null;
}

export function normalizeNotifyBeforeMinutes(value) {
  const parsed = Number.parseInt(value, 10);
  if (!Number.isFinite(parsed)) {
    return DEFAULT_NOTIFY_BEFORE_MINUTES;
  }

  return Math.min(MAX_NOTIFY_BEFORE_MINUTES, Math.max(MIN_NOTIFY_BEFORE_MINUTES, parsed));
}

export function buildDeliveryKey(alert, game, selectedDate, event = null) {
  if (event) {
    return `${alert.discordUserId}:${alert.alertType}:${event.eventKey}`;
  }

  return `${alert.discordUserId}:${alert.alertType}:${toYmd(selectedDate)}:${game.id}`;
}

function isGameStartDue(alert, game, selectedDate, now) {
  if (isFinalGameStatus(game.remarks)) {
    return false;
  }

  const gameDateTime = getGameDateTime(selectedDate, game.time);
  if (!gameDateTime) {
    return false;
  }

  const beforeMinutes = normalizeNotifyBeforeMinutes(alert.notifyBeforeMinutes);
  const alertAt = new Date(gameDateTime.getTime() - beforeMinutes * 60 * 1000);
  return now >= alertAt && now < gameDateTime;
}

function isResultDue(game) {
  return isFinalGameStatus(game.remarks);
}

function buildEventAlertMessage(alert, event) {
  const teamLogo = logoEmoji[alert.team] ?? '';
  const awayLogo = logoEmoji[event.away] ?? '';
  const homeLogo = logoEmoji[event.home] ?? '';
  const scoreText = `${normalizeScore(event.awayScore)} vs ${normalizeScore(event.homeScore)}`;
  const matchup = `${awayLogo} ${event.away} ${scoreText} ${homeLogo} ${event.home}`.trim();

  if (event.alertType === ALERT_TYPES.SCORE_CHANGE) {
    return [
      `${teamLogo} ${alert.team} 득점 알림입니다. ${event.scoreDelta ? `+${event.scoreDelta}점` : ''}`.trim(),
      `${event.time} | ${matchup} | ${event.stadium} | ${event.remarks}`.trim()
    ].join('\n');
  }

  if (event.alertType === ALERT_TYPES.LEAD_CHANGE) {
    return [
      `${teamLogo} ${alert.team} 역전 알림입니다.`.trim(),
      `${event.time} | ${matchup} | ${event.stadium} | ${event.remarks}`.trim()
    ].join('\n');
  }

  return [
    `${teamLogo} ${alert.team} 경기 취소 알림입니다.`.trim(),
    `${event.time} | ${awayLogo} ${event.away} vs ${homeLogo} ${event.home} | ${event.stadium} | ${event.remarks}`.trim()
  ].join('\n');
}

export function buildAlertMessage(alert, game, event = null) {
  if (event) {
    return buildEventAlertMessage(alert, event);
  }

  const teamLogo = logoEmoji[alert.team] ?? '';
  const awayLogo = logoEmoji[game.away] ?? '';
  const homeLogo = logoEmoji[game.home] ?? '';
  const beforeMinutes = normalizeNotifyBeforeMinutes(alert.notifyBeforeMinutes);
  const scoreText = `${normalizeScore(game.awayScore)} vs ${normalizeScore(game.homeScore)}`;
  const matchup = `${awayLogo} ${game.away} ${scoreText} ${homeLogo} ${game.home}`.trim();

  if (alert.alertType === ALERT_TYPES.GAME_START) {
    return [
      `${teamLogo} ${alert.team} 경기 시작 ${beforeMinutes}분 전입니다.`.trim(),
      `${game.time} | ${awayLogo} ${game.away} vs ${homeLogo} ${game.home} | ${game.stadium}`.trim()
    ].join('\n');
  }

  return [
    `${teamLogo} ${alert.team} 경기 종료 알림입니다.`.trim(),
    `${game.time} | ${matchup} | ${game.stadium} | ${game.remarks}`.trim()
  ].join('\n');
}

export function buildDueAlertDeliveries(alerts, games, selectedDate, options = {}) {
  const now = options.now ?? new Date();
  const events = options.events ?? [];
  const deliveries = [];

  for (const alert of alerts ?? []) {
    const normalizedTeam = normalizeAlertTeam(alert.team);
    if (!normalizedTeam) {
      continue;
    }

    const normalizedAlert = {
      ...alert,
      team: normalizedTeam,
      notifyBeforeMinutes: normalizeNotifyBeforeMinutes(alert.notifyBeforeMinutes)
    };

    if (EVENT_ALERT_TYPES.has(normalizedAlert.alertType)) {
      for (const event of events) {
        if (
          normalizedAlert.alertType !== event.alertType
          || normalizeTeamName(normalizedTeam) !== normalizeTeamName(event.team)
        ) {
          continue;
        }

        deliveries.push({
          deliveryKey: buildDeliveryKey(normalizedAlert, null, selectedDate, event),
          discordUserId: normalizedAlert.discordUserId,
          alertType: normalizedAlert.alertType,
          gameId: event.gameId,
          message: buildAlertMessage(normalizedAlert, null, event)
        });
      }
      continue;
    }

    for (const game of games ?? []) {
      if (!isTeamInGame(normalizedTeam, game)) {
        continue;
      }

      const due = normalizedAlert.alertType === ALERT_TYPES.GAME_START
        ? isGameStartDue(normalizedAlert, game, selectedDate, now)
        : normalizedAlert.alertType === ALERT_TYPES.GAME_RESULT && isResultDue(game);

      if (!due) {
        continue;
      }

      deliveries.push({
        deliveryKey: buildDeliveryKey(normalizedAlert, game, selectedDate),
        discordUserId: normalizedAlert.discordUserId,
        alertType: normalizedAlert.alertType,
        gameId: game.id,
        message: buildAlertMessage(normalizedAlert, game)
      });
    }
  }

  return deliveries;
}

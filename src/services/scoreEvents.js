import { toYmd } from '../constants.js';
import { ALERT_TYPES } from './alerts.js';

function normalizeScore(score) {
  return score === null || score === undefined || score === '' || Number(score) === -1 ? 0 : Number(score);
}

function leaderTeam(snapshot) {
  if (snapshot.awayScore > snapshot.homeScore) {
    return snapshot.away;
  }
  if (snapshot.homeScore > snapshot.awayScore) {
    return snapshot.home;
  }
  return '';
}

function isCancelledStatus(remarks) {
  return String(remarks ?? '').includes('취소');
}

function snapshotMap(snapshots) {
  return new Map((snapshots ?? []).map((snapshot) => [snapshot.snapshotKey, snapshot]));
}

export function buildScoreSnapshot(game, selectedDate) {
  const snapshot = {
    snapshotKey: `${toYmd(selectedDate)}:${game.id}`,
    gameDate: toYmd(selectedDate),
    gameId: game.id,
    time: game.time,
    away: game.away,
    home: game.home,
    stadium: game.stadium,
    remarks: game.remarks ?? '-',
    awayScore: normalizeScore(game.awayScore),
    homeScore: normalizeScore(game.homeScore)
  };

  return {
    ...snapshot,
    leaderTeam: leaderTeam(snapshot)
  };
}

function eventBase(snapshot) {
  return {
    snapshotKey: snapshot.snapshotKey,
    gameDate: snapshot.gameDate,
    gameId: snapshot.gameId,
    time: snapshot.time,
    away: snapshot.away,
    home: snapshot.home,
    stadium: snapshot.stadium,
    remarks: snapshot.remarks,
    awayScore: snapshot.awayScore,
    homeScore: snapshot.homeScore
  };
}

function scoreChangeEvents(previous, current) {
  const events = [];
  const awayDelta = current.awayScore - previous.awayScore;
  const homeDelta = current.homeScore - previous.homeScore;

  if (awayDelta > 0) {
    events.push({
      ...eventBase(current),
      alertType: ALERT_TYPES.SCORE_CHANGE,
      team: current.away,
      scoreDelta: awayDelta,
      eventKey: `${current.snapshotKey}:score_change:${current.away}:${current.awayScore}-${current.homeScore}`
    });
  }

  if (homeDelta > 0) {
    events.push({
      ...eventBase(current),
      alertType: ALERT_TYPES.SCORE_CHANGE,
      team: current.home,
      scoreDelta: homeDelta,
      eventKey: `${current.snapshotKey}:score_change:${current.home}:${current.awayScore}-${current.homeScore}`
    });
  }

  return events;
}

function leadChangeEvent(previous, current) {
  if (!previous.leaderTeam || !current.leaderTeam || previous.leaderTeam === current.leaderTeam) {
    return null;
  }

  return {
    ...eventBase(current),
    alertType: ALERT_TYPES.LEAD_CHANGE,
    team: current.leaderTeam,
    previousLeaderTeam: previous.leaderTeam,
    eventKey: `${current.snapshotKey}:lead_change:${current.leaderTeam}:${current.awayScore}-${current.homeScore}`
  };
}

function cancellationEvents(previous, current) {
  if (isCancelledStatus(previous.remarks) || !isCancelledStatus(current.remarks)) {
    return [];
  }

  return [current.away, current.home].map((team) => ({
    ...eventBase(current),
    alertType: ALERT_TYPES.GAME_CANCELLED,
    team,
    eventKey: `${current.snapshotKey}:game_cancelled:${team}:${current.remarks}`
  }));
}

export function buildScoreEvents(previousSnapshots, games, selectedDate) {
  const previousByKey = snapshotMap(previousSnapshots);
  const events = [];

  for (const game of games ?? []) {
    const current = buildScoreSnapshot(game, selectedDate);
    const previous = previousByKey.get(current.snapshotKey);
    if (!previous) {
      continue;
    }

    events.push(...scoreChangeEvents(previous, current));
    const leadEvent = leadChangeEvent(previous, current);
    if (leadEvent) {
      events.push(leadEvent);
    }
    events.push(...cancellationEvents(previous, current));
  }

  return events;
}

export function buildScoreSnapshots(games, selectedDate) {
  return (games ?? []).map((game) => buildScoreSnapshot(game, selectedDate));
}

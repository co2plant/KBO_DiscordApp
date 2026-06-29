import { nowKst, toMmdd, toYmd } from '../constants.js';
import {
  refreshLiveScoresForCommand,
  ensureScheduleDataForDate
} from './dataReady.js';
import {
  ALERT_TYPES,
  buildDueAlertDeliveries
} from './alerts.js';
import {
  buildScoreEvents,
  buildScoreSnapshots
} from './scoreEvents.js';

const STORED_EVENT_TYPES = new Set([
  ALERT_TYPES.SCORE_CHANGE,
  ALERT_TYPES.LEAD_CHANGE
]);

async function storeGameEvents(database, scoreEvents) {
  if (!database.insertGameEvent) {
    return;
  }

  for (const event of scoreEvents.filter((scoreEvent) => STORED_EVENT_TYPES.has(scoreEvent.alertType))) {
    try {
      await database.insertGameEvent(event);
    } catch (error) {
      console.log(`[alert:event] failed event=${event.eventKey}: ${error.message}`);
    }
  }
}

function groupEventsByGameId(events) {
  const grouped = new Map();
  for (const event of events ?? []) {
    const existing = grouped.get(event.gameId) ?? [];
    existing.push(event);
    grouped.set(event.gameId, existing);
  }
  return grouped;
}

async function loadResultLeadChangeEvents(database, selectedDate, resultGameIds) {
  if (!database.selectGameEventsByGameIds || resultGameIds.length === 0) {
    return new Map();
  }

  try {
    const events = await database.selectGameEventsByGameIds(
      toYmd(selectedDate),
      resultGameIds,
      ALERT_TYPES.LEAD_CHANGE
    );
    return groupEventsByGameId(events);
  } catch (error) {
    console.log(`Failed to load lead change events for result summary: ${error.message}`);
    return new Map();
  }
}

export async function runAlertCheck(dependencies, options = {}) {
  const { client, database, crawler } = dependencies;
  const selectedDate = options.selectedDate ?? nowKst();
  const selectedDateKey = options.selectedDateKey ?? toMmdd(selectedDate);
  const now = options.now ?? selectedDate;

  await ensureScheduleDataForDate(database, crawler, selectedDateKey);
  const games = await refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate, { now });
  const previousSnapshots = database.selectScoreSnapshots
    ? await database.selectScoreSnapshots(selectedDateKey)
    : [];
  const scoreEvents = buildScoreEvents(previousSnapshots, games, selectedDate);
  await storeGameEvents(database, scoreEvents);
  const alerts = await database.selectEnabledUserAlerts();
  const baseDeliveries = buildDueAlertDeliveries(alerts, games, selectedDate, { now, events: scoreEvents });
  const resultGameIds = [
    ...new Set(
      baseDeliveries
        .filter((delivery) => delivery.alertType === ALERT_TYPES.GAME_RESULT)
        .map((delivery) => delivery.gameId)
    )
  ];
  const resultEventHistoryByGameId = await loadResultLeadChangeEvents(database, selectedDate, resultGameIds);
  const deliveries = resultGameIds.length
    ? buildDueAlertDeliveries(alerts, games, selectedDate, {
      now,
      events: scoreEvents,
      resultEventHistoryByGameId
    })
    : baseDeliveries;

  let sent = 0;
  let skipped = 0;
  let failed = 0;

  for (const delivery of deliveries) {
    const claimed = await database.claimAlertDelivery(delivery);
    if (!claimed) {
      skipped += 1;
      continue;
    }

    try {
      const user = await client.users.fetch(delivery.discordUserId);
      await user.send(delivery.message);
      await database.markAlertDeliverySent(delivery.deliveryKey);
      sent += 1;
      console.log(`[alert:dm] type=${delivery.alertType} user=${delivery.discordUserId} game=${delivery.gameId}`);
    } catch (error) {
      failed += 1;
      await database.markAlertDeliveryFailed(delivery.deliveryKey, error.message);
      console.log(`[alert:dm] failed type=${delivery.alertType} user=${delivery.discordUserId} game=${delivery.gameId}: ${error.message}`);
    }
  }

  if (database.upsertScoreSnapshots) {
    await database.upsertScoreSnapshots(buildScoreSnapshots(games, selectedDate));
  }

  return {
    checked: deliveries.length,
    sent,
    skipped,
    failed
  };
}

export function scheduleAlertWorker(dependencies, options = {}) {
  const intervalMs = options.intervalMs ?? 5 * 60 * 1000;
  let running = false;

  const run = async () => {
    if (running) {
      return;
    }

    running = true;
    try {
      await runAlertCheck(dependencies);
    } catch (error) {
      console.log(`Alert worker failed: ${error.message}`);
    } finally {
      running = false;
    }
  };

  const timer = setInterval(run, intervalMs);
  run();
  return timer;
}

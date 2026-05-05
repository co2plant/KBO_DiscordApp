import { nowKst, toMmdd } from '../constants.js';
import {
  refreshLiveScoresForCommand,
  ensureScheduleDataForDate
} from './dataReady.js';
import { buildDueAlertDeliveries } from './alerts.js';

export async function runAlertCheck(dependencies, options = {}) {
  const { client, database, crawler } = dependencies;
  const selectedDate = options.selectedDate ?? nowKst();
  const selectedDateKey = options.selectedDateKey ?? toMmdd(selectedDate);
  const now = options.now ?? selectedDate;

  await ensureScheduleDataForDate(database, crawler, selectedDateKey);
  const games = await refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate, { now });
  const alerts = await database.selectEnabledUserAlerts();
  const deliveries = buildDueAlertDeliveries(alerts, games, selectedDate, { now });

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

import { nowKst, toMmdd } from '../constants.js';
import { shouldRefreshLiveScores } from '../utils/formatters.js';

let readyPromise;

export async function ensureDataReady(database, crawler) {
  if (!readyPromise) {
    readyPromise = (async () => {
      await database.ensureSchema();

      if (!await database.hasStandingsData()) {
        console.log('Bootstrapping standings data...');
        await crawler.insertStandings(database);
      }

      const todayKey = toMmdd(nowKst());
      if (!await database.hasScheduleDataForDate(todayKey)) {
        console.log(`Bootstrapping schedule data for ${todayKey}...`);
        await crawler.updateScheduleOnce(todayKey, database);
      }
    })();
  }

  return readyPromise;
}

export async function refreshStandingsForCommand(database, crawler) {
  try {
    await crawler.updateStandings(database);
  } catch (error) {
    console.log(`Failed to refresh standings: ${error.message}`);
  }
}

export async function ensureScheduleDataForDate(database, crawler, selectedDateKey) {
  if (await database.hasScheduleDataForDate(selectedDateKey)) {
    return;
  }

  try {
    await crawler.updateScheduleOnce(selectedDateKey, database);
  } catch (error) {
    console.log(`Failed to refresh schedule for ${selectedDateKey}: ${error.message}`);
  }
}

export async function refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate, options = {}) {
  const games = await database.selectGamesAndScores(selectedDateKey);
  const now = options.now ?? nowKst();
  if (!shouldRefreshLiveScores(selectedDate, games, { now })) {
    return games;
  }

  try {
    const count = await crawler.updateLiveScores(selectedDateKey, database);
    console.log(`Refreshed live scores for ${selectedDateKey}: ${count}`);
  } catch (error) {
    console.log(`Failed to refresh live scores for ${selectedDateKey}: ${error.message}`);
    return games;
  }

  return database.selectGamesAndScores(selectedDateKey);
}

export async function selectScheduleRowsForCommand(database, crawler, selectedDateKey, selectedDate, options = {}) {
  await ensureScheduleDataForDate(database, crawler, selectedDateKey);
  return refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate, options);
}

export function resetDataReadyForTests() {
  readyPromise = undefined;
}

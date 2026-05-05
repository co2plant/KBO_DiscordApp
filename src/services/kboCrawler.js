import { config } from '../config.js';
import { nowKst, toMmdd } from '../constants.js';
import { parseScoreValue, updateLiveScores as updateLiveScoresFromKbo } from './liveScore.js';
import {
  fetchPlayerDetail as fetchKboPlayerDetail,
  searchPlayers as searchKboPlayers
} from './playerCrawler.js';

const STANDINGS_URL = 'https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx';
const SCHEDULE_URL = 'https://www.koreabaseball.com/Schedule/Schedule.aspx';

function normalizeScheduleDate(value) {
  const text = String(value ?? '').trim();
  const match = text.match(/(\d{1,2})\D+(\d{1,2})/);
  if (match) {
    return `${String(Number(match[1])).padStart(2, '0')}${String(Number(match[2])).padStart(2, '0')}`;
  }

  return text.replace(/\D/g, '');
}

function buildGameId(selectedDate, index) {
  return `${selectedDate}${String(index).padStart(2, '0')}`;
}

function parseMatchup(value) {
  const [awayRaw = '', homeRaw = ''] = String(value ?? '').split('vs');
  const parseSide = (side) => {
    const chars = [...side];
    return {
      team: chars.filter((char) => !/\d/.test(char)).join('').trim(),
      score: parseScoreValue(chars.filter((char) => /\d/.test(char)).join(''))
    };
  };

  const away = parseSide(awayRaw);
  const home = parseSide(homeRaw);
  return {
    away: away.team,
    awayScore: away.score,
    home: home.team,
    homeScore: home.score
  };
}

async function withPage(work) {
  const puppeteer = await import('puppeteer-core');
  const browser = await puppeteer.launch({
    executablePath: config.chromiumPath,
    args: ['--headless=new', '--no-sandbox', '--disable-dev-shm-usage']
  });

  try {
    const page = await browser.newPage();
    await page.setUserAgent('Mozilla/5.0 (compatible; KBO-DiscordBot/1.0)');
    return await work(page);
  } finally {
    await browser.close();
  }
}

export async function updateStandings(database) {
  return withPage(async (page) => {
    await page.goto(STANDINGS_URL, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('#cphContents_cphContents_cphContents_udpRecord table tbody tr', { timeout: 15000 });
    const rows = await page.$$eval('#cphContents_cphContents_cphContents_udpRecord table tbody tr', (trs) => (
      trs.map((tr) => [...tr.querySelectorAll('td')].map((td) => td.textContent.trim()))
    ));

    console.log(`[crawl:standings] rows=${rows.length}`);
    for (const cells of rows) {
      if (cells.length < 12) {
        continue;
      }

      await database.upsertStandings({
        id: cells[0],
        team: cells[1],
        win: Number.parseInt(cells[2], 10),
        lose: Number.parseInt(cells[3], 10),
        draw: Number.parseInt(cells[4], 10),
        rate: cells[6],
        last10: cells[8],
        streak: cells[9],
        home: cells[10],
        away: cells[11]
      });
    }

    return rows.length;
  });
}

export async function insertStandings(database) {
  return updateStandings(database);
}

export async function updateScheduleOnce(selectedDate, database) {
  const normalizedDate = normalizeScheduleDate(selectedDate);
  return withPage(async (page) => {
    await page.goto(SCHEDULE_URL, { waitUntil: 'networkidle2', timeout: 30000 });
    await page.waitForSelector('#tblScheduleList tbody tr', { timeout: 15000 });
    const rows = await page.$$eval('#tblScheduleList tbody tr', (trs) => (
      trs.map((tr) => ({
        day: tr.querySelector('.day')?.textContent.trim() ?? '',
        rowspan: tr.querySelector('.day')?.getAttribute('rowspan') ?? '',
        cells: [...tr.querySelectorAll('td')].map((td) => td.textContent.trim())
      }))
    ));

    let count = 0;
    let rowspan = 0;
    for (const row of rows) {
      if (!row.day) {
        continue;
      }

      const rowSpanValue = Number.parseInt(row.rowspan || '1', 10);
      count += rowSpanValue;
      if (normalizeScheduleDate(row.day.split('(')[0]) === normalizedDate) {
        rowspan = rowSpanValue;
        break;
      }
    }

    if (rowspan === 0) {
      console.log(`[crawl:schedule] date=${normalizedDate} rows=0`);
      return 0;
    }

    const start = count - rowspan;
    const targetRows = rows.slice(start, count);
    let updatedCount = 0;
    for (const [index, row] of targetRows.entries()) {
      const firstRow = index === 0;
      const time = firstRow ? row.cells[1] : row.cells[0];
      const matchup = parseMatchup(firstRow ? row.cells[2] : row.cells[1]);
      const stadium = firstRow ? row.cells[7] : row.cells[6];
      const remarks = firstRow ? row.cells[8] : row.cells[7];

      await database.upsertGameAndScore({
        id: buildGameId(normalizedDate, index),
        time,
        away: matchup.away,
        home: matchup.home,
        awayScore: matchup.awayScore,
        homeScore: matchup.homeScore,
        stadium,
        remarks
      });
      updatedCount += 1;
      console.log(`[crawl:schedule] ${time} ${matchup.away} ${matchup.awayScore}-${matchup.homeScore} ${matchup.home} ${stadium} ${remarks}`);
    }

    return updatedCount;
  });
}

export async function updateTodaySchedule(database) {
  return updateScheduleOnce(toMmdd(nowKst()), database);
}

export async function updateLiveScores(selectedDate, database) {
  return updateLiveScoresFromKbo(normalizeScheduleDate(selectedDate), database);
}

export async function searchPlayers(keyword) {
  return searchKboPlayers(keyword);
}

export async function fetchPlayerDetail(candidate) {
  return fetchKboPlayerDetail(candidate);
}

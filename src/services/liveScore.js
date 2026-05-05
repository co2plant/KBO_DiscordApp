const SCOREBOARD_URL = 'https://www.koreabaseball.com/Schedule/ScoreBoard.aspx';
const MOBILE_LIVE_BASE_URL = 'https://m.koreabaseball.com';

export function parseScoreValue(value) {
  const text = String(value ?? '').trim();
  return /^\d+$/.test(text) ? Number.parseInt(text, 10) : -1;
}

function stripTags(html) {
  return html.replace(/<[^>]*>/g, '').replace(/\s+/g, ' ').trim();
}

function decodeHtml(value) {
  return value
    .replace(/&amp;/g, '&')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>');
}

function firstMatch(html, pattern, fallback = '') {
  const match = html.match(pattern);
  return match ? decodeHtml(match[1]).trim() : fallback;
}

function parseGameLink(block) {
  const href = firstMatch(block, /href=['"]([^'"]*GameCenter\/Main\.aspx[^'"]*)['"]/i);
  if (!href) {
    return { gameDate: '', gameId: '' };
  }

  const url = new URL(decodeHtml(href), 'https://www.koreabaseball.com');
  return {
    gameDate: url.searchParams.get('gameDate') ?? '',
    gameId: url.searchParams.get('gameId') ?? ''
  };
}

function parsePlace(block) {
  const placeHtml = firstMatch(block, /<p[^>]*class=['"][^'"]*place[^'"]*['"][^>]*>([\s\S]*?)<\/p>/i);
  const text = stripTags(placeHtml);
  const match = text.match(/^(.+?)\s+(\d{1,2}:\d{2})$/);
  if (!match) {
    return { stadium: text, time: '' };
  }

  return { stadium: match[1].trim(), time: match[2] };
}

export function parseScoreboardGames(html) {
  const blocks = html.match(/<div\s+class=['"]smsScore['"][\s\S]*?(?=<div\s+class=['"]smsScore['"]|<!--\s*\/\/smsscore\s*-->|$)/gi) ?? [];

  return blocks.map((block) => {
    const teamMatches = [...block.matchAll(/<strong[^>]*class=['"][^'"]*teamT[^'"]*['"][^>]*>([\s\S]*?)<\/strong>/gi)];
    const scoreMatches = [...block.matchAll(/<em[^>]*class=['"][^'"]*score[^'"]*['"][^>]*>\s*<span[^>]*>([\s\S]*?)<\/span>\s*<\/em>/gi)];
    const status = stripTags(firstMatch(block, /<strong[^>]*class=['"][^'"]*flag[^'"]*['"][^>]*>([\s\S]*?)<\/strong>/i, '-')) || '-';
    const { gameDate, gameId } = parseGameLink(block);
    const { stadium, time } = parsePlace(block);

    return {
      gameDate,
      gameId,
      awayTeam: stripTags(teamMatches[0]?.[1] ?? ''),
      homeTeam: stripTags(teamMatches[1]?.[1] ?? ''),
      awayScore: parseScoreValue(stripTags(scoreMatches[0]?.[1] ?? '')),
      homeScore: parseScoreValue(stripTags(scoreMatches[1]?.[1] ?? '')),
      status,
      stadium,
      time
    };
  }).filter((game) => game.awayTeam && game.homeTeam);
}

export function liveGameStatus(liveGame, fallbackStatus) {
  if (!liveGame) {
    return fallbackStatus || '-';
  }

  const sectionId = String(liveGame.SECTION_ID ?? '');
  if (sectionId === '1') {
    return '경기전';
  }
  if (sectionId === '3') {
    return '경기종료';
  }

  if (liveGame.INN_NO && liveGame.TB_NM) {
    return `${liveGame.INN_NO}회${liveGame.TB_NM}`;
  }

  return fallbackStatus || '-';
}

async function requestText(url, options = {}) {
  const response = await fetch(url, {
    headers: {
      'User-Agent': 'Mozilla/5.0 (compatible; KBO-DiscordBot/1.0)',
      ...(options.headers ?? {})
    },
    ...options
  });

  if (!response.ok) {
    throw new Error(`HTTP ${response.status} for ${url}`);
  }

  return response.text();
}

export async function fetchLiveGameState(gameId) {
  const body = new URLSearchParams({
    le_id: '1',
    sr_id: '0',
    g_id: gameId
  });
  const text = await requestText(`${MOBILE_LIVE_BASE_URL}/ws/Kbo.asmx/GetGameState`, {
    method: 'POST',
    body,
    headers: {
      'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
      Referer: `${MOBILE_LIVE_BASE_URL}/Kbo/Live/Live.aspx?p_le_id=1&p_sr_id=0&p_g_id=${gameId}&p_sc_id=0`,
      'X-Requested-With': 'XMLHttpRequest'
    }
  });
  const payload = JSON.parse(text);
  return payload.game?.[0] ?? null;
}

export async function updateLiveScores(selectedDateKey, database, dependencies = {}) {
  const fetchState = dependencies.fetchLiveGameState ?? fetchLiveGameState;
  const fetchScoreboard = dependencies.fetchScoreboard ?? (() => requestText(SCOREBOARD_URL));
  const scoreboardHtml = await fetchScoreboard();
  const games = parseScoreboardGames(scoreboardHtml)
    .filter((game) => !game.gameDate || game.gameDate.endsWith(selectedDateKey));

  console.log(`[crawl:live-score] date=${selectedDateKey} scoreboard_games=${games.length}`);

  let updatedCount = 0;
  for (const game of games) {
    let liveGame = null;
    if (game.gameId) {
      try {
        liveGame = await fetchState(game.gameId);
      } catch (error) {
        console.log(`[crawl:live-score] failed live state for ${game.gameId}: ${error.message}`);
      }
    }

    const awayScore = liveGame ? parseScoreValue(liveGame.A_SCORE_CN) : game.awayScore;
    const homeScore = liveGame ? parseScoreValue(liveGame.H_SCORE_CN) : game.homeScore;
    const status = liveGameStatus(liveGame, game.status);

    await database.updateLiveGameScore({
      selectedDate: selectedDateKey,
      time: game.time,
      away: game.awayTeam,
      home: game.homeTeam,
      awayScore,
      homeScore,
      remarks: status
    });
    updatedCount += 1;
    console.log(`[crawl:live-score] ${game.time} ${game.awayTeam} ${awayScore}-${homeScore} ${game.homeTeam} ${status}`);
  }

  return updatedCount;
}

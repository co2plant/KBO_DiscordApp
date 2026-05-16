const KBO_BASE_URL = 'https://www.koreabaseball.com';
const PLAYER_SEARCH_URL = `${KBO_BASE_URL}/Player/Search.aspx`;

function decodeHtml(value) {
  return String(value ?? '')
    .replace(/&amp;/g, '&')
    .replace(/&#39;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/&nbsp;/g, ' ');
}

function stripTags(html) {
  return decodeHtml(String(html ?? '').replace(/<[^>]*>/g, ' '))
    .replace(/\s+/g, ' ')
    .trim();
}

function firstMatch(html, pattern, fallback = '') {
  const match = String(html ?? '').match(pattern);
  return match ? decodeHtml(match[1]).trim() : fallback;
}

function normalizeUrl(value) {
  const text = decodeHtml(value);
  if (!text) {
    return '';
  }
  if (text.startsWith('//')) {
    return `https:${text}`;
  }
  return new URL(text, KBO_BASE_URL).toString();
}

function parseDetailType(detailUrl) {
  if (/PitcherDetail/i.test(detailUrl)) {
    return 'pitcher';
  }
  return 'hitter';
}

function shortTeamName(teamName) {
  return stripTags(teamName).split(/\s+/)[0] ?? '';
}

function labelValue(html, label) {
  const escapedLabel = label.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  const pattern = new RegExp(`<strong>\\s*${escapedLabel}:\\s*<\\/strong>([\\s\\S]*?)<\\/li>`, 'i');
  return stripTags(firstMatch(html, pattern));
}

function parseTableRows(tableHtml) {
  const headers = [...String(tableHtml ?? '').matchAll(/<th\b[^>]*>([\s\S]*?)<\/th>/gi)]
    .map((match) => stripTags(match[1]))
    .filter(Boolean);
  const body = firstMatch(tableHtml, /<tbody\b[^>]*>([\s\S]*?)<\/tbody>/i);
  const firstRow = firstMatch(body, /<tr\b[^>]*>([\s\S]*?)<\/tr>/i);
  const values = [...firstRow.matchAll(/<t[dh]\b[^>]*>([\s\S]*?)<\/t[dh]>/gi)]
    .map((match) => stripTags(match[1]));

  return { headers, values };
}

function firstSeasonBlock(html) {
  const match = String(html ?? '').match(/<h6>\s*(\d{4})\s*성적\s*<\/h6>([\s\S]*?)(?=<h6>|$)/i);
  if (!match) {
    return { year: '', block: '' };
  }

  return {
    year: match[1],
    block: match[2]
  };
}

export function parsePlayerSeasonStats(html, detailType = 'hitter') {
  const { year, block } = firstSeasonBlock(html);
  if (!block) {
    return null;
  }

  const stats = {};
  const tables = [...block.matchAll(/<table\b[^>]*>([\s\S]*?)<\/table>/gi)];
  for (const [, table] of tables) {
    const { headers, values } = parseTableRows(table);
    headers.forEach((header, index) => {
      if (values[index] !== undefined && values[index] !== '') {
        stats[header] = values[index];
      }
    });
  }

  if (Object.keys(stats).length === 0) {
    return null;
  }

  return {
    year,
    type: detailType,
    stats
  };
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

export function parsePlayerSearchResults(html) {
  const rows = [...String(html ?? '').matchAll(/<tr\b[^>]*>([\s\S]*?)<\/tr>/gi)];

  return rows.map(([, row]) => {
    const cells = [...row.matchAll(/<td\b[^>]*>([\s\S]*?)<\/td>/gi)].map((match) => match[1]);
    if (cells.length < 7) {
      return null;
    }

    const href = firstMatch(cells[1], /href=['"]([^'"]+)['"]/i);
    if (!href) {
      return null;
    }

    const detailUrl = normalizeUrl(href);
    const url = new URL(detailUrl);
    const playerId = url.searchParams.get('playerId') ?? '';
    if (!playerId) {
      return null;
    }

    return {
      playerId,
      name: stripTags(cells[1]),
      team: stripTags(cells[2]),
      backNo: stripTags(cells[0]),
      position: stripTags(cells[3]),
      birthday: stripTags(cells[4]),
      heightWeight: stripTags(cells[5]),
      career: stripTags(cells[6]),
      detailUrl,
      detailType: parseDetailType(detailUrl)
    };
  }).filter(Boolean);
}

export function parsePlayerDetail(html, source = {}) {
  const detailUrl = source.detailUrl ? normalizeUrl(source.detailUrl) : '';
  const playerId = source.playerId
    ?? (detailUrl ? new URL(detailUrl).searchParams.get('playerId') : '')
    ?? '';
  const teamName = stripTags(firstMatch(html, /<h4[^>]*id=['"]h4Team['"][^>]*>([\s\S]*?)<\/h4>/i));
  const profileImageUrl = normalizeUrl(firstMatch(
    html,
    /<img[^>]*id=['"][^'"]*playerProfile_imgProgile[^'"]*['"][^>]*src=['"]([^'"]+)['"]/i
  ));

  const detailType = source.detailType ?? parseDetailType(detailUrl);

  return {
    playerId,
    detailUrl,
    detailType,
    team: shortTeamName(teamName),
    teamName,
    name: labelValue(html, '선수명'),
    backNo: labelValue(html, '등번호').replace(/^No\./i, '').trim(),
    birthday: labelValue(html, '생년월일'),
    position: labelValue(html, '포지션'),
    heightWeight: labelValue(html, '신장/체중'),
    career: labelValue(html, '경력'),
    payment: labelValue(html, '입단 계약금'),
    salary: labelValue(html, '연봉'),
    draft: labelValue(html, '지명순위'),
    joinInfo: labelValue(html, '입단년도'),
    profileImageUrl,
    seasonStats: parsePlayerSeasonStats(html, detailType)
  };
}

export async function searchPlayers(keyword, dependencies = {}) {
  const fetchText = dependencies.fetchText ?? requestText;
  const url = `${PLAYER_SEARCH_URL}?searchWord=${encodeURIComponent(keyword)}`;
  const html = await fetchText(url);
  const players = parsePlayerSearchResults(html);
  console.log(`[crawl:player-search] keyword=${keyword} source=network results=${players.length}`);
  return players;
}

export async function fetchPlayerDetail(candidate, dependencies = {}) {
  const fetchText = dependencies.fetchText ?? requestText;
  const html = await fetchText(candidate.detailUrl);
  const player = parsePlayerDetail(html, candidate);
  console.log(`[crawl:player-detail] playerId=${player.playerId} team=${player.team} name=${player.name} profile=ok`);
  return player;
}

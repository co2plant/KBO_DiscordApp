function normalize(value) {
  return String(value ?? '').trim().toUpperCase();
}

function filterByTeam(players, team) {
  if (!team) {
    return players;
  }

  const normalizedTeam = normalize(team);
  return players.filter((player) => normalize(player.team) === normalizedTeam);
}

export async function getPlayerById(playerId, database, crawler, candidate = {}) {
  const cached = await database.selectPlayerById(playerId);
  if (cached) {
    console.log(`[cache:player] playerId=${playerId} hit`);
    return cached;
  }

  const player = await crawler.fetchPlayerDetail({
    ...candidate,
    playerId
  });
  await database.upsertPlayer(player);
  return player;
}

export async function resolvePlayerLookup(request, database, crawler) {
  const name = String(request.name ?? '').trim();
  const team = String(request.team ?? '').trim();

  if (team) {
    const cached = await database.selectPlayerByNameAndTeam(name, team);
    if (cached) {
      console.log(`[cache:player] name=${name} team=${team} hit`);
      return { type: 'player', player: cached, source: 'cache' };
    }
  } else {
    const cachedPlayers = await database.selectPlayersByName(name);
    if (cachedPlayers.length === 1) {
      console.log(`[cache:player] name=${name} hit`);
      return { type: 'player', player: cachedPlayers[0], source: 'cache' };
    }
    if (cachedPlayers.length > 1) {
      console.log(`[cache:player] name=${name} candidates=${cachedPlayers.length}`);
      return { type: 'candidates', candidates: cachedPlayers, source: 'cache' };
    }
  }

  const candidates = filterByTeam(await crawler.searchPlayers(name), team);
  if (candidates.length === 0) {
    return { type: 'not_found', candidates: [], source: 'network' };
  }
  if (candidates.length > 1) {
    return { type: 'candidates', candidates, source: 'network' };
  }

  const player = await getPlayerById(candidates[0].playerId, database, crawler, candidates[0]);
  return { type: 'player', player, source: 'network' };
}

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

export async function getPlayerById(playerId, database, crawler, candidate = {}, options = {}) {
  const cached = await database.selectPlayerById(playerId);
  if (cached && !options.refreshDetail) {
    console.log(`[cache:player] playerId=${playerId} hit`);
    return cached;
  }

  const player = await crawler.fetchPlayerDetail({
    ...(cached ?? {}),
    ...candidate,
    playerId
  });
  await database.upsertPlayer(player);
  return player;
}

export async function resolvePlayerLookup(request, database, crawler, options = {}) {
  const name = String(request.name ?? '').trim();
  const team = String(request.team ?? '').trim();

  if (team) {
    const cached = await database.selectPlayerByNameAndTeam(name, team);
    if (cached) {
      console.log(`[cache:player] name=${name} team=${team} hit`);
      const player = options.refreshDetail
        ? await getPlayerById(cached.playerId, database, crawler, cached, { refreshDetail: true })
        : cached;
      return { type: 'player', player, source: 'cache' };
    }
  } else {
    const cachedPlayers = await database.selectPlayersByName(name);
    if (cachedPlayers.length === 1) {
      console.log(`[cache:player] name=${name} hit`);
      const player = options.refreshDetail
        ? await getPlayerById(cachedPlayers[0].playerId, database, crawler, cachedPlayers[0], { refreshDetail: true })
        : cachedPlayers[0];
      return { type: 'player', player, source: 'cache' };
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

  const player = await getPlayerById(candidates[0].playerId, database, crawler, candidates[0], {
    refreshDetail: options.refreshDetail
  });
  return { type: 'player', player, source: 'network' };
}

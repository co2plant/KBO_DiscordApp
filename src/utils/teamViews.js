export function buildTeamRecordFields(team) {
  return [
    {
      name: '요약',
      value: `${team.id}위 · ${team.win}승 ${team.lose}패 ${team.draw}무 (${team.rate})`,
      inline: false
    },
    { name: '최근 10경기', value: team.last10, inline: true },
    {
      name: '연속',
      value: `${team.streak}\n**홈**\n${team.home}\n**원정**\n${team.away}`,
      inline: true
    }
  ];
}

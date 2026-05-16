import { logoEmoji, rankEmoji } from '../constants.js';

const PLAYER_COMPONENT_PREFIX = 'kbo_player';
const MAX_BUTTON_CANDIDATES = 5;
const MAX_SELECT_CANDIDATES = 25;
const ComponentType = {
  ActionRow: 1,
  Button: 2,
  StringSelect: 3
};
const ButtonStyle = {
  Primary: 1
};

function valueOrDash(value) {
  const text = String(value ?? '').trim();
  return text || '-';
}

function candidateLabel(candidate, index) {
  return `${index + 1}. ${candidate.team} ${candidate.name}`.slice(0, 80);
}

function candidateDescription(candidate) {
  return [
    candidate.position,
    candidate.backNo ? `No.${candidate.backNo}` : '',
    candidate.birthday
  ].filter(Boolean).join(' · ').slice(0, 100);
}

function formatAvailableStats(stats, keys) {
  return keys
    .map(([label, key]) => {
      const value = stats[key];
      return value === undefined || value === '' ? '' : `${label} ${value}`;
    })
    .filter(Boolean);
}

export function formatPlayerSeasonStats(seasonStats) {
  if (!seasonStats?.stats) {
    return '';
  }

  const stats = seasonStats.stats;
  if (seasonStats.type === 'pitcher') {
    return [
      ...formatAvailableStats(stats, [['ERA', 'ERA']]),
      `${stats.W ?? 0}승 ${stats.L ?? 0}패`,
      ...formatAvailableStats(stats, [
        ['SV', 'SV'],
        ['HLD', 'HLD'],
        ['IP', 'IP'],
        ['SO', 'SO'],
        ['WHIP', 'WHIP']
      ])
    ].filter(Boolean).join(' · ');
  }

  return formatAvailableStats(stats, [
    ['AVG', 'AVG'],
    ['OPS', 'OPS'],
    ['HR', 'HR'],
    ['RBI', 'RBI'],
    ['SB', 'SB']
  ]).join(' · ');
}

export function buildPlayerDetailUrl(playerId, detailType = 'hitter') {
  const path = detailType === 'pitcher'
    ? '/Record/Player/PitcherDetail/Basic.aspx'
    : '/Record/Player/HitterDetail/Basic.aspx';
  return `https://www.koreabaseball.com${path}?playerId=${playerId}`;
}

export function buildPlayerEmbed(player) {
  const teamLogo = logoEmoji[player.team] ?? '';
  const seasonStatsText = formatPlayerSeasonStats(player.seasonStats);
  const fields = [
    { name: '팀', value: valueOrDash(player.teamName || player.team), inline: true },
    { name: '등번호', value: valueOrDash(player.backNo), inline: true },
    { name: '포지션', value: valueOrDash(player.position), inline: true },
    { name: '생년월일', value: valueOrDash(player.birthday), inline: true },
    { name: '신장/체중', value: valueOrDash(player.heightWeight), inline: true },
    { name: '입단년도', value: valueOrDash(player.joinInfo), inline: true },
    { name: '경력', value: valueOrDash(player.career), inline: false },
    { name: '지명순위', value: valueOrDash(player.draft), inline: false },
    { name: '연봉', value: valueOrDash(player.salary), inline: true },
    { name: '입단 계약금', value: valueOrDash(player.payment), inline: true }
  ];

  if (seasonStatsText) {
    fields.unshift({
      name: `${player.seasonStats.year} 성적`,
      value: seasonStatsText,
      inline: false
    });
  }

  const embed = {
    title: `${teamLogo} ${player.name} 선수 정보`.trim(),
    url: player.detailUrl,
    color: 0x00AEEF,
    fields
  };

  if (player.profileImageUrl) {
    embed.thumbnail = { url: player.profileImageUrl };
  }

  return embed;
}

export function buildPlayerCandidateResponse(candidates, ownerId) {
  const limitedCandidates = candidates.slice(0, MAX_SELECT_CANDIDATES);
  const lines = limitedCandidates.map((candidate, index) => {
    const rank = rankEmoji[index + 1] ?? `${index + 1}.`;
    const teamLogo = logoEmoji[candidate.team] ?? '';
    const description = candidateDescription(candidate);
    return `${rank} ${teamLogo} ${candidate.team} ${candidate.name}${description ? ` · ${description}` : ''}`.trim();
  });

  const embed = {
    title: '동명이인 선수 선택',
    description: lines.join('\n'),
    color: 0x00AEEF
  };

  if (limitedCandidates.length <= MAX_BUTTON_CANDIDATES) {
    return {
      embeds: [embed],
      components: [
        {
          type: ComponentType.ActionRow,
          components: limitedCandidates.map((candidate, index) => ({
            type: ComponentType.Button,
            custom_id: `${PLAYER_COMPONENT_PREFIX}:button:${ownerId}:${candidate.playerId}:${candidate.detailType ?? 'hitter'}`,
            label: candidateLabel(candidate, index),
            style: ButtonStyle.Primary
          }))
        }
      ]
    };
  }

  return {
    embeds: [embed],
    components: [
      {
        type: ComponentType.ActionRow,
        components: [
          {
            type: ComponentType.StringSelect,
            custom_id: `${PLAYER_COMPONENT_PREFIX}:select:${ownerId}`,
            placeholder: '조회할 선수를 선택하세요',
            options: limitedCandidates.map((candidate, index) => ({
              label: candidateLabel(candidate, index),
              value: `${candidate.playerId}:${candidate.detailType ?? 'hitter'}`,
              description: candidateDescription(candidate)
            }))
          }
        ]
      }
    ]
  };
}

export function parsePlayerComponentCustomId(customId, values = []) {
  const parts = String(customId ?? '').split(':');
  if (parts[0] !== PLAYER_COMPONENT_PREFIX) {
    return null;
  }

  if (parts[1] === 'button') {
    return {
      type: 'button',
      ownerId: parts[2],
      playerId: parts[3],
      detailType: parts[4] || 'hitter'
    };
  }

  if (parts[1] === 'select') {
    const [playerId, detailType = 'hitter'] = String(values[0] ?? '').split(':');
    return {
      type: 'select',
      ownerId: parts[2],
      playerId,
      detailType
    };
  }

  return null;
}

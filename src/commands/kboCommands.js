import { EmbedBuilder, SlashCommandBuilder } from 'discord.js';

import {
  addKstDays,
  formatKoreanMonthDay,
  getKoreanWeekday,
  logoEmoji,
  nowKst,
  rankEmoji,
  toMmdd,
  toYmd
} from '../constants.js';
import {
  ensureDataReady,
  ensureScheduleDataForDate,
  refreshLiveScoresForCommand,
  refreshStandingsForCommand,
  selectScheduleRowsForCommand
} from '../services/dataReady.js';
import {
  buildStandingsFields,
  findStandingsTeam,
  findTeamGames,
  formatScheduleMatchup,
  formatScoreLine,
  normalizeTeamName
} from '../utils/formatters.js';
import { resolvePlayerLookup } from '../services/playerLookup.js';
import { buildGameSummary } from '../services/gameSummary.js';
import {
  ALERT_TYPES,
  ALERT_TYPE_LABELS,
  DEFAULT_NOTIFY_BEFORE_MINUTES,
  normalizeNotifyBeforeMinutes
} from '../services/alerts.js';
import {
  buildPlayerCandidateResponse,
  buildPlayerEmbed
} from '../utils/playerViews.js';
import { buildTeamRecordFields } from '../utils/teamViews.js';
import {
  buildHelpFields,
  buildHelpIntro
} from '../utils/helpViews.js';
import {
  normalizeTeamInput,
  resolvePreferredTeam
} from '../utils/teamAutocomplete.js';

function createdFooter(embed) {
  return embed.setFooter({ text: 'Created' }).setTimestamp(new Date());
}

function buildStandingsEmbed(rows) {
  return createdFooter(
    new EmbedBuilder()
      .setTitle('KBO 순위')
      .setURL('https://sports.news.naver.com/kbaseball/record/index?category=kbo')
      .setColor(0x00AEEF)
      .addFields(buildStandingsFields(rows))
  );
}

function teamDisplayName(teamRow, teamGames, requestedTeam) {
  if (teamRow) {
    return teamRow.team;
  }

  const firstGame = teamGames[0];
  if (!firstGame) {
    return requestedTeam;
  }

  return normalizeTeamName(firstGame.away) === normalizeTeamName(requestedTeam)
    ? firstGame.away
    : firstGame.home;
}

const alertTypeChoices = [
  { name: '경기 시작', value: ALERT_TYPES.GAME_START },
  { name: '경기 종료', value: ALERT_TYPES.GAME_RESULT },
  { name: '득점', value: ALERT_TYPES.SCORE_CHANGE },
  { name: '역전', value: ALERT_TYPES.LEAD_CHANGE },
  { name: '경기 취소', value: ALERT_TYPES.GAME_CANCELLED }
];

function addTeamOption(command, description, required = false) {
  return command.addStringOption((option) => (
    option.setName('team')
      .setDescription(description)
      .setRequired(required)
      .setAutocomplete(true)
  ));
}

function addAlertOptions(command, includeMinutes = false) {
  command
    .addStringOption((option) => (
      option.setName('type')
        .setDescription('알림 종류를 선택하세요.')
        .setRequired(true)
        .addChoices(...alertTypeChoices)
    ));

  addTeamOption(command, '알림을 받을 팀을 선택하세요. 비우면 내 팀을 사용합니다.');

  if (includeMinutes) {
    command.addIntegerOption((option) => (
      option.setName('minutes')
        .setDescription('경기 시작 몇 분 전에 받을지 선택하세요. 기본값은 10분입니다.')
        .setRequired(false)
        .setMinValue(1)
        .setMaxValue(60)
    ));
  }

  return command;
}

async function resolveTeamForCommand(interaction, database) {
  return resolvePreferredTeam({
    providedTeam: interaction.options.getString('team') ?? '',
    discordUserId: interaction.user.id,
    database
  });
}

function missingTeamMessage(commandName) {
  return `${commandName}에 사용할 팀을 찾지 못했습니다. team을 입력하거나 /내팀설정으로 기본 팀을 먼저 설정하세요.`;
}

function formatAlertLine(alert) {
  const label = ALERT_TYPE_LABELS[alert.alertType] ?? alert.alertType;
  const timingByType = {
    [ALERT_TYPES.GAME_START]: `(${alert.notifyBeforeMinutes}분 전)`,
    [ALERT_TYPES.GAME_RESULT]: '(경기 종료 후)',
    [ALERT_TYPES.SCORE_CHANGE]: '(득점 시)',
    [ALERT_TYPES.LEAD_CHANGE]: '(역전 시)',
    [ALERT_TYPES.GAME_CANCELLED]: '(취소 시)'
  };
  const timing = timingByType[alert.alertType] ?? '';
  return `${logoEmoji[alert.team] ?? ''} ${alert.team} ${label} ${timing}`.trim();
}

export function createCommands(dependencies) {
  const { database, crawler } = dependencies;

  return [
    {
      data: new SlashCommandBuilder()
        .setName('도움말')
        .setDescription('KBO 봇 사용법과 주요 명령어를 보여줍니다.'),
      async execute(interaction) {
        const embed = createdFooter(
          new EmbedBuilder()
            .setTitle('KBO 봇 도움말')
            .setDescription(buildHelpIntro())
            .setColor(0x00AEEF)
            .addFields(buildHelpFields())
        );

        await interaction.reply({ embeds: [embed], ephemeral: true });
      }
    },
    {
      data: addTeamOption(
        new SlashCommandBuilder()
          .setName('내팀설정')
          .setDescription('자주 보는 KBO 팀을 기본 팀으로 저장합니다.'),
        '기본 팀으로 저장할 팀을 선택하세요.',
        true
      ),
      async execute(interaction) {
        await database.ensureSchema();

        const team = normalizeTeamInput(interaction.options.getString('team', true));
        if (!team) {
          await interaction.reply({ content: '저장할 팀을 확인할 수 없습니다.', ephemeral: true });
          return;
        }

        await database.upsertUserPreference({
          discordUserId: interaction.user.id,
          favoriteTeam: team
        });
        await interaction.reply({
          content: `${logoEmoji[team] ?? ''} ${team}을 내 팀으로 설정했습니다.`,
          ephemeral: true
        });
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('내팀')
        .setDescription('내 기본 KBO 팀 설정을 확인합니다.'),
      async execute(interaction) {
        await database.ensureSchema();

        const preference = await database.selectUserPreference(interaction.user.id);
        await interaction.reply({
          content: preference?.favoriteTeam
            ? `${logoEmoji[preference.favoriteTeam] ?? ''} 내 팀은 ${preference.favoriteTeam}입니다.`
            : '설정된 내 팀이 없습니다. /내팀설정으로 먼저 저장하세요.',
          ephemeral: true
        });
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('내팀해제')
        .setDescription('저장한 기본 KBO 팀 설정을 삭제합니다.'),
      async execute(interaction) {
        await database.ensureSchema();

        const deleted = await database.deleteUserPreference(interaction.user.id);
        await interaction.reply({
          content: deleted ? '내 팀 설정을 해제했습니다.' : '해제할 내 팀 설정이 없습니다.',
          ephemeral: true
        });
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('순위')
        .setDescription('돌승엽이 KBO 순위를 당신에게 보여줍니다.'),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);
        await refreshStandingsForCommand(database, crawler);

        const rows = await database.selectStandings();
        if (!rows?.length) {
          await interaction.editReply('순위 데이터를 찾을 수 없습니다.');
          return;
        }

        await interaction.editReply({ embeds: [buildStandingsEmbed(rows)] });
      }
    },
    {
      data: addTeamOption(
        new SlashCommandBuilder()
          .setName('성적')
          .setDescription('선택한 팀의 KBO 상세 성적을 보여줍니다.'),
        '상세 성적을 확인할 팀 이름을 입력하세요. 비우면 내 팀을 사용합니다.'
      ),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);
        await refreshStandingsForCommand(database, crawler);

        const teamName = await resolveTeamForCommand(interaction, database);
        if (!teamName) {
          await interaction.editReply(missingTeamMessage('/성적'));
          return;
        }

        const rows = await database.selectStandings();
        const team = findStandingsTeam(rows, teamName);
        if (!team) {
          await interaction.editReply(`${teamName} 팀의 성적을 찾을 수 없습니다.`);
          return;
        }

        const embed = createdFooter(
          new EmbedBuilder()
            .setTitle(`${logoEmoji[team.team] ?? ''} ${team.team} 성적`)
            .setURL('https://sports.news.naver.com/kbaseball/record/index?category=kbo')
            .setColor(0x00AEEF)
            .addFields(buildTeamRecordFields(team))
        );

        await interaction.editReply({ embeds: [embed] });
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('일정')
        .setDescription('돌승엽이 KBO 경기 일정을 당신에게 보여줍니다.')
        .addStringOption((option) => (
          option.setName('date')
            .setDescription('[오늘|내일|모레] 중 하나를 선택하세요.')
            .setRequired(true)
            .addChoices(
              { name: '오늘', value: '오늘' },
              { name: '내일', value: '내일' },
              { name: '모레', value: '모레' }
            )
        )),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);

        const selectedDay = { '오늘': 0, '내일': 1, '모레': 2 }[interaction.options.getString('date', true)];
        const selectedDate = addKstDays(nowKst(), selectedDay);
        const selectedDateKey = toMmdd(selectedDate);

        const rows = await selectScheduleRowsForCommand(database, crawler, selectedDateKey, selectedDate);
        if (selectedDate.getUTCDay() === 1 || !rows?.length) {
          await interaction.editReply('경기가 없는 날입니다.');
          return;
        }

        const timeLines = rows.map((row, index) => `${rankEmoji[index + 1]} ${row.time}`).join('\n');
        const gameLines = rows.map((row) => formatScheduleMatchup(selectedDate, row, { now: nowKst() })).join('\n');
        const stadiumLines = rows.map((row) => `${row.stadium} ${row.remarks}`).join('\n');

        const embed = createdFooter(
          new EmbedBuilder()
            .setTitle(`${formatKoreanMonthDay(selectedDate)} ${getKoreanWeekday(selectedDate)}요일 KBO 경기 일정`)
            .setURL(`https://m.sports.naver.com/kbaseball/schedule/index?date=${toYmd(selectedDate)}`)
            .setColor(0x00AEEF)
            .addFields(
              { name: '목차 시간', value: timeLines, inline: true },
              { name: '경기', value: gameLines, inline: true },
              { name: '구장 비고', value: stadiumLines, inline: true }
            )
        );

        await interaction.editReply({ embeds: [embed] });
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('선수')
        .setDescription('선수 이름으로 KBO 기본 정보를 조회합니다.')
        .addStringOption((option) => (
          option.setName('name')
            .setDescription('조회할 선수 이름을 입력하세요.')
            .setRequired(true)
            .setAutocomplete(true)
        ))
        .addStringOption((option) => (
          option.setName('team')
            .setDescription('동명이인이 있을 때 좁힐 팀 이름을 입력하세요.')
            .setRequired(false)
            .setAutocomplete(true)
        )),
      async execute(interaction) {
        await interaction.deferReply();
        await database.ensureSchema();

        const name = interaction.options.getString('name', true);
        const team = interaction.options.getString('team') ?? '';
        const result = await resolvePlayerLookup({ name, team }, database, crawler, { refreshDetail: true });

        if (result.type === 'not_found') {
          await interaction.editReply(`${name} 선수 정보를 찾을 수 없습니다.`);
          return;
        }

        if (result.type === 'candidates') {
          await interaction.editReply(buildPlayerCandidateResponse(result.candidates, interaction.user.id));
          return;
        }

        await interaction.editReply({ embeds: [buildPlayerEmbed(result.player)], components: [] });
      }
    },
    {
      data: addAlertOptions(
        new SlashCommandBuilder()
          .setName('알림설정')
          .setDescription('개인 DM으로 받을 KBO 팀 알림을 설정합니다.'),
        true
      ),
      async execute(interaction) {
        await database.ensureSchema();

        const team = await resolveTeamForCommand(interaction, database);
        const alertType = interaction.options.getString('type', true);
        if (!team || !Object.values(ALERT_TYPES).includes(alertType)) {
          await interaction.reply({ content: missingTeamMessage('/알림설정'), ephemeral: true });
          return;
        }

        const notifyBeforeMinutes = alertType === ALERT_TYPES.GAME_START
          ? normalizeNotifyBeforeMinutes(interaction.options.getInteger('minutes') ?? DEFAULT_NOTIFY_BEFORE_MINUTES)
          : DEFAULT_NOTIFY_BEFORE_MINUTES;

        await database.upsertUserAlert({
          discordUserId: interaction.user.id,
          alertType,
          team,
          notifyBeforeMinutes
        });

        await interaction.reply({
          content: `${formatAlertLine({ alertType, team, notifyBeforeMinutes })} 알림을 설정했습니다.`,
          ephemeral: true
        });
      }
    },
    {
      data: addAlertOptions(
        new SlashCommandBuilder()
          .setName('알림해제')
          .setDescription('설정한 개인 KBO 팀 알림을 해제합니다.')
      ),
      async execute(interaction) {
        await database.ensureSchema();

        const team = await resolveTeamForCommand(interaction, database);
        const alertType = interaction.options.getString('type', true);
        if (!team || !Object.values(ALERT_TYPES).includes(alertType)) {
          await interaction.reply({ content: missingTeamMessage('/알림해제'), ephemeral: true });
          return;
        }

        const deleted = await database.deleteUserAlert({
          discordUserId: interaction.user.id,
          alertType,
          team
        });

        await interaction.reply({
          content: deleted
            ? `${formatAlertLine({ alertType, team, notifyBeforeMinutes: DEFAULT_NOTIFY_BEFORE_MINUTES })} 알림을 해제했습니다.`
            : '해제할 알림을 찾지 못했습니다.',
          ephemeral: true
        });
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('내알림')
        .setDescription('내가 설정한 개인 KBO 팀 알림 목록을 보여줍니다.'),
      async execute(interaction) {
        await database.ensureSchema();

        const alerts = await database.selectUserAlerts(interaction.user.id);
        await interaction.reply({
          content: alerts.length
            ? alerts.map(formatAlertLine).join('\n')
            : '설정된 알림이 없습니다.',
          ephemeral: true
        });
      }
    },
    {
      data: addTeamOption(
        new SlashCommandBuilder()
          .setName('경기요약')
          .setDescription('선택한 팀의 오늘 경기 흐름을 요약합니다.'),
        '요약을 확인할 팀 이름을 입력하세요. 비우면 내 팀을 사용합니다.'
      ),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);

        const requestedTeam = await resolveTeamForCommand(interaction, database);
        if (!requestedTeam) {
          await interaction.editReply(missingTeamMessage('/경기요약'));
          return;
        }

        const selectedDate = nowKst();
        const selectedDateKey = toMmdd(selectedDate);

        await ensureScheduleDataForDate(database, crawler, selectedDateKey);
        const gameRows = await refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate);
        const teamGames = findTeamGames(gameRows ?? [], requestedTeam);

        if (teamGames.length === 0) {
          await interaction.editReply(`${requestedTeam} 오늘 경기 정보를 찾을 수 없습니다.`);
          return;
        }

        const teamName = teamDisplayName(null, teamGames, requestedTeam);
        const embed = createdFooter(
          new EmbedBuilder()
            .setTitle(`${logoEmoji[teamName] ?? ''} ${teamName} 경기 요약`)
            .setURL(`https://m.sports.naver.com/kbaseball/schedule/index?date=${toYmd(selectedDate)}`)
            .setColor(0x00AEEF)
        );

        for (const game of teamGames) {
          const summary = buildGameSummary(game, teamName, selectedDate);
          embed.addFields({
            name: summary.context,
            value: `${summary.scoreLine}\n${summary.summary}`,
            inline: false
          });
        }

        await interaction.editReply({ embeds: [embed] });
      }
    },
    {
      data: addTeamOption(
        new SlashCommandBuilder()
          .setName('팀')
          .setDescription('선택한 팀의 오늘 경기와 성적 요약을 보여줍니다.'),
        '요약을 확인할 팀 이름을 입력하세요. 비우면 내 팀을 사용합니다.'
      ),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);

        const requestedTeam = await resolveTeamForCommand(interaction, database);
        if (!requestedTeam) {
          await interaction.editReply(missingTeamMessage('/팀'));
          return;
        }

        const selectedDate = nowKst();
        const selectedDateKey = toMmdd(selectedDate);

        await ensureScheduleDataForDate(database, crawler, selectedDateKey);
        const gameRows = await refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate);
        await refreshStandingsForCommand(database, crawler);

        const standingsRows = await database.selectStandings();
        const teamRow = findStandingsTeam(standingsRows, requestedTeam);
        const teamGames = findTeamGames(gameRows ?? [], requestedTeam);

        if (!teamRow && teamGames.length === 0) {
          await interaction.editReply(`${requestedTeam} 팀 정보를 찾을 수 없습니다.`);
          return;
        }

        const teamName = teamDisplayName(teamRow, teamGames, requestedTeam);
        const embed = createdFooter(
          new EmbedBuilder()
            .setTitle(`${logoEmoji[teamName] ?? ''} ${teamName} 팀 요약`)
            .setURL('https://sports.news.naver.com/kbaseball/record/index?category=kbo')
            .setColor(0x00AEEF)
        );

        if (teamRow) {
          embed.addFields({
            name: '성적',
            value: `${teamRow.id}위 · ${teamRow.win}승 ${teamRow.lose}패 ${teamRow.draw}무 (${teamRow.rate})\n`
              + `최근 10경기 ${teamRow.last10} · 연속 ${teamRow.streak}\n`
              + `홈 ${teamRow.home} · 원정 ${teamRow.away}`,
            inline: false
          });
        } else {
          embed.addFields({ name: '성적', value: '순위 데이터를 찾을 수 없습니다.', inline: false });
        }

        embed.addFields({
          name: '오늘 경기',
          value: teamGames.length
            ? teamGames.map((row) => formatScoreLine(selectedDate, row, { now: nowKst() })).join('\n')
            : '오늘 예정된 경기가 없습니다.',
          inline: false
        });

        await interaction.editReply({ embeds: [embed] });
      }
    }
  ];
}

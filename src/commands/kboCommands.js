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
import {
  buildPlayerCandidateResponse,
  buildPlayerEmbed
} from '../utils/playerViews.js';

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

export function createCommands(dependencies) {
  const { database, crawler } = dependencies;

  return [
    {
      data: new SlashCommandBuilder()
        .setName('차렷')
        .setDescription('돌승엽이 잘못한 경우에 사용하십시오.'),
      async execute(interaction) {
        await interaction.reply('차렷!');
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('열중쉬어')
        .setDescription('돌승엽이 잘하였지만 부족할 때 사용하십시오.'),
      async execute(interaction) {
        await interaction.reply('열중 쉬어!');
      }
    },
    {
      data: new SlashCommandBuilder()
        .setName('쉬어')
        .setDescription('돌승엽이 잘한 경우에 사용하십시오.'),
      async execute(interaction) {
        await interaction.reply('쉬어!');
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
      data: new SlashCommandBuilder()
        .setName('성적')
        .setDescription('선택한 팀의 KBO 상세 성적을 보여줍니다.')
        .addStringOption((option) => (
          option.setName('team')
            .setDescription('상세 성적을 확인할 팀 이름을 입력하세요.')
            .setRequired(true)
        )),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);
        await refreshStandingsForCommand(database, crawler);

        const teamName = interaction.options.getString('team', true);
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
            .addFields(
              {
                name: '요약',
                value: `${team.id}위 · ${team.win}승 ${team.lose}패 ${team.draw}무 (${team.rate})`,
                inline: false
              },
              { name: '최근 10경기', value: team.last10, inline: true },
              { name: '연속', value: team.streak, inline: true },
              { name: '홈', value: team.home, inline: true },
              { name: '원정', value: team.away, inline: true }
            )
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
        .setName('스코어')
        .setDescription('오늘 KBO 경기 스코어를 보여줍니다.'),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);

        const selectedDate = nowKst();
        const selectedDateKey = toMmdd(selectedDate);
        await ensureScheduleDataForDate(database, crawler, selectedDateKey);

        const rows = await refreshLiveScoresForCommand(database, crawler, selectedDateKey, selectedDate);
        if (!rows?.length) {
          await interaction.editReply('오늘 경기 스코어를 찾을 수 없습니다.');
          return;
        }

        const embed = createdFooter(
          new EmbedBuilder()
            .setTitle(`${formatKoreanMonthDay(selectedDate)} KBO 스코어`)
            .setURL(`https://m.sports.naver.com/kbaseball/schedule/index?date=${toYmd(selectedDate)}`)
            .setColor(0x00AEEF)
            .addFields({
              name: '오늘 스코어',
              value: rows.map((row) => formatScoreLine(selectedDate, row, { now: nowKst() })).join('\n'),
              inline: false
            })
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
        ))
        .addStringOption((option) => (
          option.setName('team')
            .setDescription('동명이인이 있을 때 좁힐 팀 이름을 입력하세요.')
            .setRequired(false)
        )),
      async execute(interaction) {
        await interaction.deferReply();
        await database.ensureSchema();

        const name = interaction.options.getString('name', true);
        const team = interaction.options.getString('team') ?? '';
        const result = await resolvePlayerLookup({ name, team }, database, crawler);

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
      data: new SlashCommandBuilder()
        .setName('팀')
        .setDescription('선택한 팀의 오늘 경기와 성적 요약을 보여줍니다.')
        .addStringOption((option) => (
          option.setName('team')
            .setDescription('요약을 확인할 팀 이름을 입력하세요.')
            .setRequired(true)
        )),
      async execute(interaction) {
        await interaction.deferReply();
        await ensureDataReady(database, crawler);

        const requestedTeam = interaction.options.getString('team', true);
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

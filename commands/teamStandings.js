const { EmbedBuilder, SlashCommandBuilder } = require('discord.js');

const database = require('../src/database');
const { LOGO_EMOJI } = require('../src/constants');
const { findStandingsTeam } = require('../src/render/standings');

module.exports = {
  data: new SlashCommandBuilder()
    .setName('성적')
    .setDescription('선택한 팀의 KBO 상세 성적을 보여줍니다.')
    .addStringOption(option => option
      .setName('team')
      .setDescription('상세 성적을 확인할 팀 이름을 입력하세요.')
      .setRequired(true)),
  async execute(interaction, context) {
    await interaction.deferReply();
    await context.ensureDataReady();

    const rows = await database.selectStandings();
    if (!rows || rows.length === 0) {
      await interaction.followUp('순위 데이터를 찾을 수 없습니다.');
      return;
    }

    const teamName = interaction.options.getString('team', true);
    const teamRow = findStandingsTeam(rows, teamName);
    if (!teamRow) {
      await interaction.followUp(`${teamName} 팀의 성적을 찾을 수 없습니다.`);
      return;
    }

    const embed = new EmbedBuilder()
      .setTitle(`${LOGO_EMOJI[teamRow.team]} ${teamRow.team} 성적`)
      .setURL('https://sports.news.naver.com/kbaseball/record/index?category=kbo')
      .setColor(0x00AEEF)
      .addFields(
        { name: '요약', value: `${teamRow.id}위 · ${teamRow.win}승 ${teamRow.lose}패 ${teamRow.draw}무 (${teamRow.rate})`, inline: false },
        { name: '최근 10경기', value: String(teamRow.last_10), inline: true },
        { name: '연속', value: String(teamRow.streak), inline: true },
        { name: '홈', value: String(teamRow.home), inline: true },
        { name: '원정', value: String(teamRow.away), inline: true },
      )
      .setTimestamp()
      .setFooter({ text: 'Created' });

    await interaction.followUp({ embeds: [embed] });
  },
};

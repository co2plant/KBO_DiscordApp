const { EmbedBuilder } = require('discord.js');

const database = require('../src/database');
const { buildStandingsLines } = require('../src/render/standings');

module.exports = {
  data: {
    name: '순위',
    description: '돌승엽이 KBO 순위를 당신에게 보여줍니다.',
  },
  async execute(interaction, context) {
    await interaction.deferReply();
    await context.ensureDataReady();

    const rows = await database.selectStandings();
    if (!rows || rows.length === 0) {
      await interaction.followUp('순위 데이터를 찾을 수 없습니다.');
      return;
    }

    const embed = new EmbedBuilder()
      .setTitle('KBO 순위')
      .setURL('https://sports.news.naver.com/kbaseball/record/index?category=kbo')
      .setColor(0x00AEEF)
      .addFields({ name: '전체 순위', value: buildStandingsLines(rows).join('\n'), inline: false })
      .setTimestamp()
      .setFooter({ text: 'Created' });

    await interaction.followUp({ embeds: [embed] });
  },
};

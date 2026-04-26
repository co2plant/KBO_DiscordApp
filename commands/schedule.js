const { EmbedBuilder, SlashCommandBuilder } = require('discord.js');

const database = require('../src/database');
const { addDays, formatMonthDay, nowKst } = require('../src/time');
const { buildScheduleEmbedData } = require('../src/render/schedule');

const SELECTED_DAY = {
  오늘: 0,
  내일: 1,
  모레: 2,
};

module.exports = {
  data: new SlashCommandBuilder()
    .setName('일정')
    .setDescription('돌승엽이 KBO 경기 일정을 당신에게 보여줍니다.')
    .addStringOption(option => option
      .setName('args_date')
      .setDescription('[오늘|내일|모레]를 선택해 언제 일정을 확인할지 선택하세요.')
      .setRequired(true)
      .addChoices(
        { name: '오늘', value: '오늘' },
        { name: '내일', value: '내일' },
        { name: '모레', value: '모레' },
      )),
  async execute(interaction, context) {
    await interaction.deferReply();
    await context.ensureDataReady();

    const argsDate = interaction.options.getString('args_date', true);
    const selectedDate = addDays(nowKst(), SELECTED_DAY[argsDate]);
    const weekday = selectedDate.getUTCDay();
    if (weekday === 1) {
      await interaction.followUp('경기가 없는 날입니다.');
      return;
    }

    const rows = await database.selectGameAndScore(formatMonthDay(selectedDate));
    if (!rows || rows.length === 0) {
      await interaction.followUp('일정을 찾을 수 없습니다.');
      return;
    }

    const embedData = buildScheduleEmbedData(selectedDate, rows);
    const embed = new EmbedBuilder()
      .setTitle(embedData.title)
      .setURL(embedData.url)
      .setColor(0x00AEEF)
      .addFields(
        { name: '목차  시간', value: embedData.columns[0], inline: true },
        { name: '경기', value: embedData.columns[1], inline: true },
        { name: '구장  비고', value: embedData.columns[2], inline: true },
      )
      .setTimestamp()
      .setFooter({ text: 'Created' });

    await interaction.followUp({ embeds: [embed] });
  },
};

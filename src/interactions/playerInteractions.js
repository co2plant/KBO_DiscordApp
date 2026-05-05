import { getPlayerById } from '../services/playerLookup.js';
import {
  buildPlayerDetailUrl,
  buildPlayerEmbed,
  parsePlayerComponentCustomId
} from '../utils/playerViews.js';

export function isPlayerComponent(interaction) {
  return (interaction.isButton() || interaction.isStringSelectMenu())
    && String(interaction.customId ?? '').startsWith('kbo_player:');
}

export async function handlePlayerComponent(interaction, dependencies) {
  const parsed = parsePlayerComponentCustomId(interaction.customId, interaction.values ?? []);
  if (!parsed?.playerId) {
    return false;
  }

  if (parsed.ownerId !== interaction.user.id) {
    await interaction.reply({
      content: '처음 선수 조회를 요청한 사용자만 선택할 수 있습니다.',
      ephemeral: true
    });
    return true;
  }

  await interaction.deferUpdate();
  const player = await getPlayerById(parsed.playerId, dependencies.database, dependencies.crawler, {
    playerId: parsed.playerId,
    detailType: parsed.detailType,
    detailUrl: buildPlayerDetailUrl(parsed.playerId, parsed.detailType)
  }, {
    refreshDetail: true
  });
  await interaction.editReply({
    embeds: [buildPlayerEmbed(player)],
    components: []
  });
  return true;
}

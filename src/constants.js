export const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

export const weekdays = ['월', '화', '수', '목', '금', '토', '일'];

export const rankEmoji = [
  ':zero:',
  ':one:',
  ':two:',
  ':three:',
  ':four:',
  ':five:',
  ':six:',
  ':seven:',
  ':eight:',
  ':nine:',
  '🔟'
];

export const logoEmoji = {
  '두산': '<:OB:1242717662954651720>',
  KIA: '<:HT:1242717660958035968>',
  NC: '<:NC:1242717654423179326>',
  '키움': '<:WO:1242717664397496321>',
  LG: '<:LG:1242717643966779404>',
  '삼성': '<:SS:1242717658554564608>',
  '롯데': '<:LT:1242717666549039174>',
  SSG: '<:SK:1242717650505957416>',
  '한화': '<:HH:1242717656214143056>',
  KT: '<:KT:1242717652447662111>'
};

export function nowKst() {
  return new Date(Date.now() + KST_OFFSET_MS);
}

export function toMmdd(date) {
  return `${String(date.getUTCMonth() + 1).padStart(2, '0')}${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function toYmd(date) {
  return `${date.getUTCFullYear()}-${String(date.getUTCMonth() + 1).padStart(2, '0')}-${String(date.getUTCDate()).padStart(2, '0')}`;
}

export function formatKoreanMonthDay(date) {
  return `${String(date.getUTCMonth() + 1).padStart(2, '0')}월 ${String(date.getUTCDate()).padStart(2, '0')}일`;
}

export function getKoreanWeekday(date) {
  const day = date.getUTCDay();
  return weekdays[day === 0 ? 6 : day - 1];
}

export function addKstDays(date, days) {
  const next = new Date(date.getTime());
  next.setUTCDate(next.getUTCDate() + days);
  return next;
}

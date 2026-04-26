const KST_OFFSET_MS = 9 * 60 * 60 * 1000;

function nowKst() {
  return new Date(Date.now() + KST_OFFSET_MS);
}

function addDays(date, days) {
  const nextDate = new Date(date.getTime());
  nextDate.setUTCDate(nextDate.getUTCDate() + days);
  return nextDate;
}

function pad2(value) {
  return String(value).padStart(2, '0');
}

function formatMonthDay(date) {
  return `${pad2(date.getUTCMonth() + 1)}${pad2(date.getUTCDate())}`;
}

function formatIsoDate(date) {
  return `${date.getUTCFullYear()}-${pad2(date.getUTCMonth() + 1)}-${pad2(date.getUTCDate())}`;
}

function formatKoreanMonthDay(date) {
  return `${pad2(date.getUTCMonth() + 1)}월 ${pad2(date.getUTCDate())}일`;
}

function getKoreanWeekday(date) {
  return (date.getUTCDay() + 6) % 7;
}

module.exports = {
  addDays,
  formatIsoDate,
  formatKoreanMonthDay,
  formatMonthDay,
  getKoreanWeekday,
  nowKst,
};

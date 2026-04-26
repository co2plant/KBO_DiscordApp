const { Builder, By } = require('selenium-webdriver');
const chrome = require('selenium-webdriver/chrome');

const database = require('../database');

const STANDINGS_URL = 'https://www.koreabaseball.com/Record/TeamRank/TeamRankDaily.aspx';
const STANDINGS_ROWS_XPATH = '//*[@id="cphContents_cphContents_cphContents_udpRecord"]/table/tbody/tr';
const SCHEDULE_URL = 'https://www.koreabaseball.com/Schedule/Schedule.aspx';
const SCHEDULE_ROWS_XPATH = '//*[@id="tblScheduleList"]/tbody/tr';

async function createDriver() {
  const options = new chrome.Options();
  options.addArguments('--headless=new', '--no-sandbox');
  return new Builder().forBrowser('chrome').setChromeOptions(options).build();
}

function buildGameId(selectedDate, gameIndex) {
  return `${selectedDate}${String(gameIndex).padStart(2, '0')}`;
}

function splitMatchupText(matchupText) {
  const separatedMatchup = matchupText.split('vs');
  const team = ['', ''];
  const score = ['', ''];

  for (let index = 0; index < 2; index += 1) {
    for (const char of separatedMatchup[index]) {
      if (/\d/.test(char)) {
        score[index] += char;
      } else {
        team[index] += char;
      }
    }
  }

  return { team, score };
}

async function fetchStandingsRows(driver) {
  await driver.get(STANDINGS_URL);
  return driver.findElements(By.xpath(STANDINGS_ROWS_XPATH));
}

async function fetchScheduleRows(driver) {
  await driver.get(SCHEDULE_URL);
  return driver.findElements(By.xpath(SCHEDULE_ROWS_XPATH));
}

async function parseStandingsRow(row) {
  const tds = await row.findElements(By.css('td'));
  const values = await Promise.all(tds.map(td => td.getText()));
  return [
    values[0],
    values[1],
    values[2],
    values[3],
    values[4],
    values[6],
    values[8],
    values[9],
    values[10],
    values[11],
  ];
}

async function insertStandings() {
  let driver;
  try {
    driver = await createDriver();
    const rows = await fetchStandingsRows(driver);
    for (const row of rows) {
      await database.upsertStandings(await parseStandingsRow(row));
    }
  } finally {
    if (driver) {
      await driver.quit();
    }
  }
}

async function updateStandings() {
  let driver;
  try {
    driver = await createDriver();
    const rows = await fetchStandingsRows(driver);
    for (const row of rows) {
      await database.upsertStandings(await parseStandingsRow(row));
    }
  } finally {
    if (driver) {
      await driver.quit();
    }
  }
}

async function updateScheduleOnce(selectedDate) {
  let driver;
  try {
    driver = await createDriver();
    const scheduleArea = await fetchScheduleRows(driver);
    let count = 0;
    let rowspanValue = 0;
    let shouldBreak = false;

    for (const row of scheduleArea) {
      if (shouldBreak) {
        break;
      }

      const dateCells = await row.findElements(By.className('day'));
      for (const td of dateCells) {
        const text = await td.getText();
        const dates = text.split('(');
        const rowspan = await td.getAttribute('rowspan');
        count += Number.parseInt(rowspan, 10);

        if (dates[0] === selectedDate) {
          rowspanValue = Number.parseInt(rowspan, 10);
          shouldBreak = true;
          break;
        }
      }
    }

    for (let index = count - rowspanValue; index < count; index += 1) {
      const tds = await scheduleArea[index].findElements(By.css('td'));
      const values = await Promise.all(tds.map(td => td.getText()));
      const gameId = buildGameId(selectedDate, index - (count - rowspanValue));

      if (index === count - rowspanValue) {
        const { team, score } = splitMatchupText(values[2]);
        await database.updateGameAndScore([gameId, values[1], team[0], score[0], score[1], team[1], values[7], values[8]]);
      } else {
        const { team, score } = splitMatchupText(values[1]);
        await database.updateGameAndScore([gameId, values[0], team[0], score[0], score[1], team[1], values[6], values[7]]);
      }
    }
  } finally {
    if (driver) {
      await driver.quit();
    }
  }
}

async function insertScheduleMonth() {
  let driver;
  try {
    driver = await createDriver();
    const scheduleArea = await fetchScheduleRows(driver);
    let incount = 0;
    let temp = null;

    for (const row of scheduleArea) {
      let cellOffset = 1;
      try {
        const dayCell = await row.findElement(By.className('day'));
        const dayText = await dayCell.getText();
        temp = dayText.split(/[.|(]/);
        incount = 0;
      } catch (_error) {
        cellOffset = 0;
      }

      const idFormat = `${temp[0]}${temp[1]}${String(incount).padStart(2, '0')}`;
      const separatedRow = (await row.getText()).split(' ');
      const { team, score } = splitMatchupText(separatedRow[cellOffset + 1]);

      if (score[0] === '') {
        score[0] = '-1';
      }
      if (score[1] === '') {
        score[1] = '-1';
      }

      incount += 1;
      await database.insertGameAndScore([idFormat, separatedRow[cellOffset], team[0], score[0], score[1], team[1], separatedRow.at(-2), separatedRow.at(-1)]);
    }
  } finally {
    if (driver) {
      await driver.quit();
    }
  }
}

module.exports = {
  buildGameId,
  insertScheduleMonth,
  insertStandings,
  splitMatchupText,
  updateScheduleOnce,
  updateStandings,
};

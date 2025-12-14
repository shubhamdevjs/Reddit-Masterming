import * as XLSX from 'xlsx';

// Normalize a cell value to a trimmed string (empty if null/undefined)
const norm = (v) => (v === undefined || v === null ? '' : String(v).trim());

const isEmptyRow = (row) => row.every((cell) => norm(cell) === '');

const readWorkbookRows = async (file) => {
  const isExcel = /\.(xlsx|xls)$/i.test(file.name);

  if (isExcel) {
    const buffer = await file.arrayBuffer();
    const workbook = XLSX.read(buffer, { type: 'array' });
    const firstSheetName = workbook.SheetNames[0];
    const sheet = workbook.Sheets[firstSheetName];
    return XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false });
  }

  // Fallback for CSV using the same XLSX parser for consistency
  const text = await file.text();
  const workbook = XLSX.read(text, { type: 'string' });
  const firstSheetName = workbook.SheetNames[0];
  const sheet = workbook.Sheets[firstSheetName];
  return XLSX.utils.sheet_to_json(sheet, { header: 1, raw: false });
};

const extractCompanyInfo = (rows) => {
  // Try headered format: companyName, companyWebsite, companyDescription on first col
  const info = { companyName: '', companyWebsite: '', companyDescription: '' };

  rows.slice(0, 5).forEach((row) => {
    const key = norm(row[0]).toLowerCase();
    const val = norm(row[1]);
    if (key === 'companyname') info.companyName = val;
    if (key === 'companywebsite') info.companyWebsite = val;
    if (key === 'companydescription') info.companyDescription = val;
    if (key === 'postsperweek') info.postsPerWeek = Number(val) || undefined;
  });

  // If not headered, fall back to positional first 3 rows
  if (!info.companyName && rows.length > 0) info.companyName = norm(rows[0][1] ?? rows[0][0]);
  if (!info.companyWebsite && rows.length > 1) info.companyWebsite = norm(rows[1][1] ?? rows[1][0]);
  if (!info.companyDescription && rows.length > 2) info.companyDescription = norm(rows[2][1] ?? rows[2][0]);

  return info;
};

const extractSection = (rows, startIndex, stopWords) => {
  const items = [];
  let i = startIndex;
  while (i < rows.length) {
    const row = rows[i];
    const first = norm(row[0]).toLowerCase();
    const second = norm(row[1]).toLowerCase();

    if (isEmptyRow(row) || stopWords.includes(first) || stopWords.includes(second)) break;

    const value = norm(row[0]) || norm(row[1]);
    if (value) items.push(value.replace(/^r\//i, ''));
    i += 1;
  }
  return { items, next: i };
};

const extractPersonas = (rows, startIndex) => {
  const personas = {};
  let i = startIndex;
  while (i < rows.length) {
    const row = rows[i];
    const username = norm(row[0]);
    const info = norm(row[1]);
    if (!username || username.toLowerCase().startsWith('keyword')) break;
    personas[username] = info;
    i += 1;
  }
  return { personas, next: i };
};

const extractKeywords = (rows, startIndex) => {
  const keywords = [];
  let i = startIndex;
  while (i < rows.length) {
    const row = rows[i];
    const kw = norm(row[1] ?? row[0]);
    if (!kw) break;
    keywords.push(kw);
    i += 1;
  }
  return keywords;
};

export async function parseCampaignFile(file) {
  const rows = await readWorkbookRows(file);
  const lower = rows.map((r) => r.map((c) => norm(c)));

  const { companyName, companyWebsite, companyDescription, postsPerWeek } = extractCompanyInfo(lower);

  // Locate sections by headers
  const findIndex = (match) => lower.findIndex((r) => norm(r[0]).toLowerCase().includes(match));
  const subIdx = findIndex('subreddits');
  const personaIdx = findIndex('username');
  const keywordIdx = lower.findIndex((r) => norm(r[0]).toLowerCase().includes('keyword_id'));

  const subreddits = subIdx !== -1
    ? extractSection(lower, subIdx + 1, ['username', 'information', 'keyword_id', 'keyword']).items
    : [];

  const personaRes = personaIdx !== -1
    ? extractPersonas(lower, personaIdx + 1)
    : { personas: {} };

  const keywords = keywordIdx !== -1
    ? extractKeywords(lower, keywordIdx + 1)
    : [];

  // Build payload expected by backend /api/campaigns/create
  return {
    companyName,
    companyWebsite,
    companyDescription,
    personas: personaRes.personas,
    subreddits,
    keywords,
    postsPerWeek: postsPerWeek || 7 // default if not provided in file
  };
}

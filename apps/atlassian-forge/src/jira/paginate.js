export async function paginateToken({ fetchPage, getItems, getToken, isComplete, identity, maxPages, maxRecords }) {
  const items = [];
  const seenIds = new Set();
  const seenTokens = new Set();
  let token;
  let pages = 0;
  let duplicateRecords = 0;
  while (pages < maxPages) {
    const page = await fetchPage(token);
    pages += 1;
    if (page.error) {
      return { items, pages, truncated: true, complete: false, reason: page.error, duplicateRecords };
    }
    const records = getItems(page) ?? [];
    for (const record of records) {
      const id = identity(record);
      if (id && seenIds.has(id)) {
        duplicateRecords += 1;
        continue;
      }
      if (id) seenIds.add(id);
      items.push(record);
      if (items.length >= maxRecords) {
        return { items, pages, truncated: true, complete: false, reason: "record_budget", duplicateRecords };
      }
    }
    if (isComplete ? isComplete(page, records) : !getToken(page)) {
      return { items, pages, truncated: false, complete: true, reason: null, duplicateRecords };
    }
    const next = getToken(page);
    if (!next) {
      return { items, pages, truncated: true, complete: false, reason: "missing_continuation", duplicateRecords };
    }
    if (next === token || seenTokens.has(next)) {
      return { items, pages, truncated: true, complete: false, reason: "repeated_page", duplicateRecords };
    }
    seenTokens.add(next);
    token = next;
  }
  return { items, pages, truncated: true, complete: false, reason: "page_budget", duplicateRecords };
}

export async function paginateOffset({ fetchPage, getItems, identity, maxPages, maxRecords, pageSize }) {
  const items = [];
  const seenIds = new Set();
  let startAt = 0;
  let pages = 0;
  let duplicateRecords = 0;
  while (pages < maxPages) {
    const page = await fetchPage(startAt, pageSize);
    pages += 1;
    if (page.error) {
      return { items, pages, truncated: true, complete: false, reason: page.error, duplicateRecords };
    }
    const records = getItems(page) ?? [];
    for (const record of records) {
      const id = identity(record);
      if (id && seenIds.has(id)) {
        duplicateRecords += 1;
        continue;
      }
      if (id) seenIds.add(id);
      items.push(record);
      if (items.length >= maxRecords) {
        return { items, pages, truncated: true, complete: false, reason: "record_budget", duplicateRecords };
      }
    }
    const total = Number(page.total);
    const isLast = page.isLastPage === true || records.length === 0 || (Number.isFinite(total) && startAt + records.length >= total);
    if (isLast) {
      return { items, pages, truncated: false, complete: true, reason: null, duplicateRecords };
    }
    if (records.length === 0) {
      return { items, pages, truncated: true, complete: false, reason: "empty_page", duplicateRecords };
    }
    startAt += records.length;
  }
  return { items, pages, truncated: true, complete: false, reason: "page_budget", duplicateRecords };
}

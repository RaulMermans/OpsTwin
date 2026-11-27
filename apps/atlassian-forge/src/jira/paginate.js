function tokenComplete(page, getToken) {
  const next = getToken(page);
  const last = page.isLast === true;
  if (last && next) return { complete: false, truncated: true, reason: "contradictory_pagination" };
  if (last) return { complete: true, truncated: false, reason: null };
  if (!next) return { complete: false, truncated: true, reason: "missing_continuation" };
  return null;
}

function offsetComplete(page, startAt, sourceCount) {
  const total = Number(page.total);
  const claimedLast = page.isLast === true || page.isLastPage === true;
  const claimedNotLast = page.isLast === false || page.isLastPage === false;
  const consumed = startAt + sourceCount;
  if (claimedLast && Number.isFinite(total) && consumed < total) {
    return { complete: false, truncated: true, reason: "contradictory_pagination" };
  }
  if (claimedNotLast && Number.isFinite(total) && consumed >= total) {
    return { complete: false, truncated: true, reason: "contradictory_pagination" };
  }
  if (claimedLast || (Number.isFinite(total) && consumed >= total)) {
    return { complete: true, truncated: false, reason: null };
  }
  if (sourceCount === 0) {
    return { complete: false, truncated: true, reason: "empty_page" };
  }
  return null;
}

export async function paginateToken({ fetchPage, getItems, getToken, identity, maxPages, maxRecords }) {
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
    let stoppedMidPage = false;
    for (const record of records) {
      const id = identity(record);
      if (id && seenIds.has(id)) {
        duplicateRecords += 1;
        continue;
      }
      if (id) seenIds.add(id);
      items.push(record);
      if (items.length >= maxRecords) {
        stoppedMidPage = items.length < records.length || records.indexOf(record) < records.length - 1;
        const remainingUnprocessed = records.slice(records.indexOf(record) + 1).some((item) => {
          const itemId = identity(item);
          return !itemId || !seenIds.has(itemId);
        });
        stoppedMidPage = remainingUnprocessed;
        break;
      }
    }
    const termination = tokenComplete(page, getToken);
    if (items.length >= maxRecords) {
      if (!stoppedMidPage && termination?.complete) {
        return { items, pages, truncated: false, complete: true, reason: null, duplicateRecords };
      }
      return { items, pages, truncated: true, complete: false, reason: "record_budget", duplicateRecords };
    }
    if (termination) {
      return { items, pages, truncated: termination.truncated, complete: termination.complete, reason: termination.reason, duplicateRecords };
    }
    const next = getToken(page);
    if (next === token || seenTokens.has(next)) {
      return { items, pages, truncated: true, complete: false, reason: "repeated_page", duplicateRecords };
    }
    seenTokens.add(next);
    token = next;
  }
  return { items, pages, truncated: true, complete: false, reason: "page_budget", duplicateRecords };
}

export async function paginateOffset({ fetchPage, getItems, identity, maxPages, maxRecords, pageSize, getSourceCount }) {
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
    const sourceCount = getSourceCount ? getSourceCount(page) : records.length;
    let stoppedMidPage = false;
    for (const record of records) {
      const id = identity(record);
      if (id && seenIds.has(id)) {
        duplicateRecords += 1;
        continue;
      }
      if (id) seenIds.add(id);
      items.push(record);
      if (items.length >= maxRecords) {
        const remainingUnprocessed = records.slice(records.indexOf(record) + 1).some((item) => {
          const itemId = identity(item);
          return !itemId || !seenIds.has(itemId);
        });
        stoppedMidPage = remainingUnprocessed;
        break;
      }
    }
    const termination = offsetComplete(page, startAt, sourceCount);
    if (items.length >= maxRecords) {
      if (!stoppedMidPage && termination?.complete) {
        return { items, pages, truncated: false, complete: true, reason: null, duplicateRecords };
      }
      return { items, pages, truncated: true, complete: false, reason: "record_budget", duplicateRecords };
    }
    if (termination) {
      return { items, pages, truncated: termination.truncated, complete: termination.complete, reason: termination.reason, duplicateRecords };
    }
    startAt += sourceCount;
  }
  return { items, pages, truncated: true, complete: false, reason: "page_budget", duplicateRecords };
}

import assert from "node:assert/strict";
import test from "node:test";
import { paginateOffset, paginateToken } from "./paginate.js";

test("token pagination covers single, empty, multi-page, duplicate, repeated, and budget cases", async () => {
  const single = await paginateToken({
    maxPages: 3,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (page) => page.issues,
    getToken: (page) => page.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "1" }], nextPageToken: null, isLast: true }),
  });
  assert.equal(single.complete, true);
  assert.equal(single.items.length, 1);

  const empty = await paginateToken({
    maxPages: 3,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (page) => page.issues,
    getToken: (page) => page.nextPageToken,
    fetchPage: async () => ({ issues: [], nextPageToken: null, isLast: true }),
  });
  assert.equal(empty.complete, true);
  assert.equal(empty.items.length, 0);

  let page = 0;
  const multi = await paginateToken({
    maxPages: 5,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (item) => item.issues,
    getToken: (item) => item.nextPageToken,
    fetchPage: async () => {
      page += 1;
      if (page === 1) return { issues: [{ id: "a" }], nextPageToken: "p2", isLast: false };
      return { issues: [{ id: "b" }], nextPageToken: null, isLast: true };
    },
  });
  assert.deepEqual(
    multi.items.map((item) => item.id),
    ["a", "b"],
  );

  const dupes = await paginateToken({
    maxPages: 5,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (item) => item.issues,
    getToken: (item) => item.nextPageToken,
    fetchPage: async (token) => {
      if (!token) return { issues: [{ id: "a" }, { id: "a" }], nextPageToken: "x", isLast: false };
      return { issues: [{ id: "a" }], nextPageToken: null, isLast: true };
    },
  });
  assert.equal(dupes.items.length, 1);
  assert.equal(dupes.duplicateRecords, 2);

  const repeated = await paginateToken({
    maxPages: 5,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (item) => item.issues,
    getToken: (item) => item.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "a" }], nextPageToken: "same", isLast: false }),
  });
  assert.equal(repeated.complete, false);
  assert.equal(repeated.reason, "repeated_page");

  const budget = await paginateToken({
    maxPages: 1,
    maxRecords: 1,
    identity: (item) => item.id,
    getItems: (item) => item.issues,
    getToken: (item) => item.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "a" }, { id: "b" }], nextPageToken: "more", isLast: false }),
  });
  assert.equal(budget.reason, "record_budget");
  assert.equal(budget.complete, false);
});

test("missing continuation is not successful termination", async () => {
  const missing = await paginateToken({
    maxPages: 5,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (page) => page.issues,
    getToken: (page) => page.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "a" }], isLast: false }),
  });
  assert.equal(missing.complete, false);
  assert.equal(missing.reason, "missing_continuation");
});

test("exact record budget on a last page is complete", async () => {
  const exact = await paginateToken({
    maxPages: 5,
    maxRecords: 2,
    identity: (item) => item.id,
    getItems: (page) => page.issues,
    getToken: (page) => page.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "a" }, { id: "b" }], nextPageToken: null, isLast: true }),
  });
  assert.equal(exact.complete, true);
  assert.equal(exact.items.length, 2);
});

test("offset pagination uses source-page counts and last-page metadata", async () => {
  const last = await paginateOffset({
    maxPages: 5,
    maxRecords: 20,
    pageSize: 2,
    identity: (item) => item.id,
    getItems: (page) => page.values,
    fetchPage: async (startAt) => ({ values: startAt === 0 ? [{ id: "1" }, { id: "2" }] : [{ id: "3" }], total: 3, isLastPage: startAt > 0 }),
  });
  assert.equal(last.complete, true);
  assert.equal(last.items.length, 3);

  const pages = await paginateOffset({
    maxPages: 1,
    maxRecords: 20,
    pageSize: 1,
    identity: (item) => item.id,
    getItems: (page) => page.values,
    fetchPage: async () => ({ values: [{ id: "1" }], total: 9, isLastPage: false }),
  });
  assert.equal(pages.reason, "page_budget");
});

test("offset pagination advances by source histories when one history has multiple events", async () => {
  const starts = [];
  const paged = await paginateOffset({
    maxPages: 5,
    maxRecords: 20,
    pageSize: 1,
    identity: (item) => item.id,
    getItems: (page) => page.values.flatMap((history) => history.items.map((item) => ({ id: `${history.id}:${item.field}` }))),
    getSourceCount: (page) => page.values.length,
    fetchPage: async (startAt) => {
      starts.push(startAt);
      if (startAt === 0) return { values: [{ id: "h1", items: [{ field: "status" }, { field: "assignee" }] }], total: 2, isLast: false };
      return { values: [{ id: "h2", items: [{ field: "status" }] }], total: 2, isLast: true };
    },
  });
  assert.deepEqual(starts, [0, 1]);
  assert.equal(paged.complete, true);
  assert.equal(paged.items.length, 3);
});

test("contradictory pagination metadata is incomplete", async () => {
  const token = await paginateToken({
    maxPages: 3,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (page) => page.issues,
    getToken: (page) => page.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "a" }], isLast: true, nextPageToken: "more" }),
  });
  assert.equal(token.reason, "contradictory_pagination");

  const offset = await paginateOffset({
    maxPages: 3,
    maxRecords: 10,
    pageSize: 10,
    identity: (item) => item.id,
    getItems: (page) => page.values,
    fetchPage: async () => ({ values: [{ id: "a" }], total: 9, isLast: true }),
  });
  assert.equal(offset.reason, "contradictory_pagination");
});

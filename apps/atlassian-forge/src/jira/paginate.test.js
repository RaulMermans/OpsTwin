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
    fetchPage: async () => ({ issues: [{ id: "1" }], nextPageToken: null }),
  });
  assert.equal(single.complete, true);
  assert.equal(single.items.length, 1);

  const empty = await paginateToken({
    maxPages: 3,
    maxRecords: 10,
    identity: (item) => item.id,
    getItems: (page) => page.issues,
    getToken: (page) => page.nextPageToken,
    fetchPage: async () => ({ issues: [], nextPageToken: null }),
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
      if (page === 1) return { issues: [{ id: "a" }], nextPageToken: "p2" };
      return { issues: [{ id: "b" }], nextPageToken: null };
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
      if (!token) return { issues: [{ id: "a" }, { id: "a" }], nextPageToken: "x" };
      return { issues: [{ id: "a" }], nextPageToken: null };
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
    fetchPage: async () => ({ issues: [{ id: "a" }], nextPageToken: "same" }),
  });
  assert.equal(repeated.complete, false);
  assert.equal(repeated.reason, "repeated_page");

  const budget = await paginateToken({
    maxPages: 1,
    maxRecords: 1,
    identity: (item) => item.id,
    getItems: (item) => item.issues,
    getToken: (item) => item.nextPageToken,
    fetchPage: async () => ({ issues: [{ id: "a" }, { id: "b" }], nextPageToken: "more" }),
  });
  assert.equal(budget.reason, "record_budget");
  assert.equal(budget.complete, false);
});

test("offset pagination stops on last page and page budget", async () => {
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

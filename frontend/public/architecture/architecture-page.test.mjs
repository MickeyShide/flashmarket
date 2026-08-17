import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import test from "node:test";
import architectureData from "./architecture-data.js";

const root = path.dirname(new URL(import.meta.url).pathname.replace(/^\/(.:)/, "$1"));

test("audited architecture counts remain visible to the UI", () => {
  assert.equal(architectureData.services.length, 9);
  assert.equal(architectureData.events.length, 27);
  assert.equal(architectureData.queues.length, 25);
  assert.equal(architectureData.workerProcesses.length, 16);
  assert.equal(architectureData.databases.length, 9);
  assert.equal(architectureData.redisUseCases.length, 5);
  assert.equal(architectureData.flows.length, 7);
  assert.equal(architectureData.celeryTasks.length, 4);
});

test("all normalized entity IDs are globally unique", () => {
  const groups = [
    "services", "infrastructure", "connections", "endpoints", "events", "exchanges", "queues",
    "workerProcesses", "oneShotProcesses", "databases", "tables", "constraints", "indexes",
    "redisUseCases", "mechanisms", "flows", "consistencyBoundaries", "failureScenarios",
    "interviewQuestions", "engineeringHighlights", "plannedCapabilities", "celeryTasks", "evidence",
  ];
  const ids = groups.flatMap((group) => architectureData[group].map((item) => item.id));
  assert.equal(new Set(ids).size, ids.length);
});

test("standalone page references only existing local assets", () => {
  const html = fs.readFileSync(path.join(root, "index.html"), "utf8");
  const references = [...html.matchAll(/(?:src|href)="(\.\/[^"#?]+)"/g)].map((match) => match[1]);
  assert.ok(references.length >= 2);
  references.forEach((reference) => assert.ok(fs.existsSync(path.resolve(root, reference)), `${reference} must exist`));
});

test("every flow step has complete explanatory content and a valid node", () => {
  const entityIds = new Set([
    ...architectureData.services, ...architectureData.infrastructure, ...architectureData.workerProcesses,
    ...architectureData.databases, ...architectureData.tables, ...architectureData.queues,
  ].map((item) => item.id));
  architectureData.flows.forEach((flow) => flow.steps.forEach((step) => {
    assert.ok(entityIds.has(step.nodeId), `${step.id} node must resolve`);
    ["what", "why", "consistency", "failure", "protection"].forEach((field) => assert.ok(step[field], `${step.id}.${field} must be present`));
  }));
});

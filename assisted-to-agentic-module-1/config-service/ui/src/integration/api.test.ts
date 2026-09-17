// Runs against the real config-service API (see config-service/README.md
// for how to start it). Not run by `npm test` - run explicitly with
// `npm run test:integration` when the service is up, since it reads and
// writes real DynamoDB data (cleaned up in afterAll).
import { describe, it, expect, beforeAll, afterAll } from "vitest";
import {
  listApplications,
  listConfigurations,
  updateConfiguration,
  listFlags,
  updateFlag,
} from "../api";

const BASE_URL = "http://localhost:5038";
const APP_NAME = `ui-integration-test-${Date.now()}`;

let applicationId: string;

beforeAll(async () => {
  const createApp = await fetch(`${BASE_URL}/api/v1/applications`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name: APP_NAME,
      description: "created by ui integration test",
    }),
  });
  const application = await createApp.json();
  applicationId = application.id;

  await fetch(
    `${BASE_URL}/api/v1/applications/${applicationId}/configurations`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ configKey: "greeting", value: "hello" }),
    },
  );

  await fetch(`${BASE_URL}/api/v1/applications/${applicationId}/flags`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ flagKey: "new-checkout", enabled: false }),
  });
});

afterAll(async () => {
  await fetch(
    `${BASE_URL}/api/v1/applications/${applicationId}/configurations/greeting`,
    {
      method: "DELETE",
    },
  );
  await fetch(
    `${BASE_URL}/api/v1/applications/${applicationId}/flags/new-checkout`,
    {
      method: "DELETE",
    },
  );
  await fetch(`${BASE_URL}/api/v1/applications/${applicationId}`, {
    method: "DELETE",
  });
});

describe("api against the live service", () => {
  it("lists the created application", async () => {
    const applications = await listApplications();
    expect(
      applications.some((a) => a.id === applicationId && a.name === APP_NAME),
    ).toBe(true);
  });

  it("lists the created configuration entry", async () => {
    const configurations = await listConfigurations(applicationId);
    expect(configurations).toEqual([
      expect.objectContaining({ configKey: "greeting", value: "hello" }),
    ]);
  });

  it("updates a configuration value and the change is visible on the next read", async () => {
    await updateConfiguration(applicationId, "greeting", "hello world");

    const configurations = await listConfigurations(applicationId);
    expect(configurations).toEqual([
      expect.objectContaining({ configKey: "greeting", value: "hello world" }),
    ]);
  });

  it("lists the created flag", async () => {
    const flags = await listFlags(applicationId);
    expect(flags).toEqual([
      expect.objectContaining({ flagKey: "new-checkout", enabled: false }),
    ]);
  });

  it("toggles a flag and the change is visible on the next read", async () => {
    await updateFlag(applicationId, "new-checkout", true);

    const flags = await listFlags(applicationId);
    expect(flags).toEqual([
      expect.objectContaining({ flagKey: "new-checkout", enabled: true }),
    ]);
  });
});

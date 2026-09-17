import { describe, it, expect, vi, beforeEach } from "vitest";
import { listApplications, updateConfiguration } from "./api";

function mockFetchOnce(status: number, body: unknown) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({
      ok: status >= 200 && status < 300,
      status,
      statusText: "",
      json: async () => body,
    }),
  );
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe("listApplications", () => {
  it("returns the parsed application list on success", async () => {
    mockFetchOnce(200, [
      { id: "1", name: "app-a", description: null, createdDate: "now" },
    ]);

    const applications = await listApplications();

    expect(applications).toEqual([
      { id: "1", name: "app-a", description: null, createdDate: "now" },
    ]);
  });
});

describe("updateConfiguration", () => {
  it("sends a PUT with configKey and value, and returns the updated entry", async () => {
    const updated = {
      applicationId: "1",
      configKey: "greeting",
      value: "hello world",
      description: null,
      createdDate: "now",
    };
    mockFetchOnce(200, updated);

    const result = await updateConfiguration("1", "greeting", "hello world");

    expect(result).toEqual(updated);
    expect(fetch).toHaveBeenCalledWith(
      "http://localhost:5038/api/v1/applications/1/configurations/greeting",
      expect.objectContaining({
        method: "PUT",
        body: JSON.stringify({ configKey: "greeting", value: "hello world" }),
      }),
    );
  });

  it("throws with the server's detail message on failure", async () => {
    mockFetchOnce(404, {
      status: 404,
      title: "Not Found",
      detail: "not found",
    });

    await expect(updateConfiguration("1", "missing", "x")).rejects.toThrow(
      "404 not found",
    );
  });
});

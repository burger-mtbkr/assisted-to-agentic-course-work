const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:5038";

export interface Application {
  id: string;
  name: string;
  description: string | null;
  createdDate: string;
}

export interface Configuration {
  applicationId: string;
  configKey: string;
  value: string;
  description: string | null;
  createdDate: string;
}

export interface Flag {
  applicationId: string;
  flagKey: string;
  enabled: boolean;
  description: string | null;
  createdDate: string;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  if (!response.ok) {
    const body = await response.json().catch(() => null);
    const message = body?.detail ?? body?.title ?? response.statusText;
    throw new Error(`${response.status} ${message}`);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return response.json() as Promise<T>;
}

export function listApplications(): Promise<Application[]> {
  return request<Application[]>("/api/v1/applications");
}

export function listConfigurations(
  applicationId: string,
): Promise<Configuration[]> {
  return request<Configuration[]>(
    `/api/v1/applications/${applicationId}/configurations`,
  );
}

export function updateConfiguration(
  applicationId: string,
  configKey: string,
  value: string,
): Promise<Configuration> {
  return request<Configuration>(
    `/api/v1/applications/${applicationId}/configurations/${configKey}`,
    {
      method: "PUT",
      body: JSON.stringify({ configKey, value }),
    },
  );
}

export function listFlags(applicationId: string): Promise<Flag[]> {
  return request<Flag[]>(`/api/v1/applications/${applicationId}/flags`);
}

export function updateFlag(
  applicationId: string,
  flagKey: string,
  enabled: boolean,
): Promise<Flag> {
  return request<Flag>(
    `/api/v1/applications/${applicationId}/flags/${flagKey}`,
    {
      method: "PUT",
      body: JSON.stringify({ flagKey, enabled }),
    },
  );
}

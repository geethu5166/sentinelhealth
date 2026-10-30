let inMemoryToken: string | null = "demo-token-analyst-public_health_analyst";

export function setApiToken(token: string | null) {
  inMemoryToken = token;
}

export function getApiToken(): string | null {
  return inMemoryToken;
}

export async function apiFetch<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers || {});
  
  const token = getApiToken();
  if (token && !headers.has("Authorization")) {
    headers.set("Authorization", `Bearer ${token}`);
  }
  
  if (!headers.has("Content-Type") && !(options.body instanceof FormData)) {
    headers.set("Content-Type", "application/json");
  }

  const url = endpoint.startsWith("http") ? endpoint : `/api/v1${endpoint.startsWith("/") ? endpoint : `/${endpoint}`}`;

  const response = await fetch(url, {
    ...options,
    headers,
  });

  if (!response.ok) {
    if (response.status === 401) {
      // Trigger token refresh or redirect
    }
    let errorDetail = "API Request failed";
    try {
      const errJson = await response.json();
      errorDetail = errJson.message || errJson.detail || JSON.stringify(errJson);
    } catch {
      errorDetail = response.statusText;
    }
    throw new Error(errorDetail);
  }

  return response.json();
}


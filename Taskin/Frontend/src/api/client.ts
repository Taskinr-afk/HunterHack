const importMetaEnv = (import.meta as ImportMeta & {
  env: { VITE_API_BASE_URL?: string };
}).env;

const API_BASE = (importMetaEnv.VITE_API_BASE_URL || "http://localhost:8000").replace(/\/$/, "");

async function fetchAPI<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: { "Content-Type": "application/json", ...options.headers },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    const message =
      (payload && typeof payload === "object" && "message" in payload && typeof payload.message === "string" && payload.message) ||
      (payload && typeof payload === "object" && "detail" in payload && typeof payload.detail === "string" && payload.detail) ||
      response.statusText ||
      "Request failed";
    throw new Error(message);
  }

  return payload as T;
}

export { API_BASE, fetchAPI };

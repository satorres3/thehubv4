import { HttpRequest } from "@azure/functions";
import { config } from "./config";

/**
 * Determines the original request origin from forwarded headers if available,
 * otherwise falls back to the configured APP_URI. This is essential for
 * handling proxying during local development.
 * @param request The incoming HTTP request.
 * @returns The origin URL (e.g., "http://localhost:5173").
 */
export function getRequestOrigin(request: HttpRequest): string {
    const proto = request.headers.get('x-forwarded-proto');
    const host = request.headers.get('x-forwarded-host');

    if (proto && host) {
        return `${proto}://${host}`;
    }

    return config.app.uri;
}

import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import * as msal from "@azure/msal-node";
import { getMsalClient } from "../shared/msal";
import { createSessionCookie } from "../shared/session";
import * as cookie from "cookie";
import { getRequestOrigin } from "../shared/utils";

const PKCE_COOKIE_NAME = "HUB_PKCE_VERIFIER";

export async function authCallback(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
    const cookies = cookie.parse(request.headers.get('cookie') || '');
    const pkceVerifier = cookies[PKCE_COOKIE_NAME];
    const origin = getRequestOrigin(request);

    if (!pkceVerifier) {
        context.error("PKCE verifier cookie not found.");
        return { status: 400, body: "Authentication error: Missing PKCE verifier. Please try logging in again." };
    }
    
    const msalClient = getMsalClient();
    const tokenRequest = {
        code: request.query.get("code") || "",
        scopes: ["User.Read", "Files.Read.All", "offline_access"],
        redirectUri: `${origin}/api/auth/callback`,
        codeVerifier: pkceVerifier,
    };

    try {
        const response = await msalClient.acquireTokenByCode(tokenRequest);
        if (!response || !response.account) {
            throw new Error("Token acquisition failed: No response or account returned.");
        }

        context.log("Token acquired successfully. Creating session cookie.");

        const sessionCookie = createSessionCookie(response.account.homeAccountId);

        // Clear the PKCE verifier cookie
        const clearPkceCookie = cookie.serialize(PKCE_COOKIE_NAME, "", {
            httpOnly: true,
            secure: process.env.NODE_ENV === "production",
            path: "/api/auth/callback",
            sameSite: 'lax',
            // Omit domain for better localhost compatibility
            expires: new Date(0), // Expire immediately
        });
        
        // Use a client-side redirect via HTML to ensure cookies are set before navigation
        const htmlBody = `
            <!DOCTYPE html>
            <html>
                <head>
                    <title>Logging in...</title>
                    <script>
                        // Redirect to the root of the application
                        window.location.href = "${origin}";
                    </script>
                </head>
                <body>
                    <p>Please wait while we redirect you...</p>
                </body>
            </html>
        `;

        return {
            status: 200,
            headers: {
                "Content-Type": "text/html",
                "Set-Cookie": [sessionCookie, clearPkceCookie] as any
            },
            body: htmlBody
        };

    } catch (error) {
        if (error instanceof msal.AuthError) {
            context.error(`MSAL AuthError during token acquisition: ${error.errorCode} - ${error.errorMessage}`, error.stack);
        } else {
            context.error("Generic error during token acquisition:", error);
        }
        return {
            status: 500,
            body: "Error during authentication callback. Please try logging in again."
        };
    }
}

app.http('authCallback', {
    methods: ['GET'],
    authLevel: 'anonymous',
    handler: authCallback,
    route: 'auth/callback'
});
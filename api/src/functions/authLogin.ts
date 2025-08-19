import { app, HttpRequest, HttpResponseInit, InvocationContext } from "@azure/functions";
import { CryptoProvider } from "@azure/msal-node";
import { getMsalClient } from "../shared/msal";
import { config } from "../shared/config";
import * as cookie from "cookie";
import { getRequestOrigin } from "../shared/utils";

const PKCE_COOKIE_NAME = "HUB_PKCE_VERIFIER";

export async function authLogin(request: HttpRequest, context: InvocationContext): Promise<HttpResponseInit> {
    const msalClient = getMsalClient();
    const cryptoProvider = new CryptoProvider();
    const { verifier, challenge } = await cryptoProvider.generatePkceCodes();
    const origin = getRequestOrigin(request);

    // Store the verifier in a short-lived, secure cookie
    const pkceCookie = cookie.serialize(PKCE_COOKIE_NAME, verifier, {
        httpOnly: true,
        secure: process.env.NODE_ENV === "production",
        path: "/api/auth/callback", // Only send to the callback URL
        sameSite: 'lax',
        maxAge: 10 * 60, // 10 minutes
        domain: new URL(origin).hostname,
    });

    const authCodeUrlParameters = {
        scopes: ["User.Read", "Files.Read.All", "offline_access"],
        redirectUri: `${origin}/api/auth/callback`,
        codeChallenge: challenge,
        codeChallengeMethod: "S256"
    };

    try {
        const authUrl = await msalClient.getAuthCodeUrl(authCodeUrlParameters);
        return {
            status: 302,
            headers: {
                "Location": authUrl,
                "Set-Cookie": pkceCookie
            }
        };
    } catch (error) {
        context.error("Error generating auth URL:", error);
        return {
            status: 500,
            body: "Error preparing for login."
        };
    }
}

app.http('authLogin', {
    methods: ['GET'],
    authLevel: 'anonymous',
    handler: authLogin,
    route: 'auth/login'
});
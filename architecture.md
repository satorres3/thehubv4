# Application Architecture Documentation

## Introduction

This document provides a technical overview of the "Hub Nice State" application. It outlines the core architecture, data structures, and operational flow to facilitate understanding and modification of the codebase.

The application is a Static Web App (SPA) built with TypeScript, HTML, and CSS, utilizing native browser features and ES modules. It does **not** use a frontend framework like React or Vue. Server-side logic lives in an Azure Functions backend written in Python.

## Development Roadmap

The project's development is structured into multiple phases, detailed in `phases.md`. The overall strategy is to:
1.  Build a functional client-side proof-of-concept. **(Complete)**
2.  Refactor to a secure Backend for Frontend (BFF) architecture. **(Complete)**
3.  Enhance AI capabilities and add collaborative features. **(In Progress)**
4.  Build out administrative and analytics tools.
5.  Prepare for enterprise-level scalability and governance.

Understanding the current phase is critical for making architectural decisions.

## Core Concepts

### 1. Workspaces (formerly Containers)
A **Workspace** is the central concept of the application from a user's perspective. It represents an isolated AI instance.
- **Note on Naming**: While all user-facing text refers to this concept as a "Workspace," the internal codebase (variable names, function names, CSS classes, etc.) still uses the legacy term **`Container`**. This was a deliberate choice to avoid a high-risk, large-scale refactor of the entire codebase. When modifying the code, you will interact with variables like `state.containers`, functions like `renderAllContainers`, and types like `interface Container`.
- **Data Structure**: Defined in `src/types.ts` as the `Container` interface.
- **Key Properties**:
    - `id`: Unique identifier.
    - `name`, `description`, `icon`: Basic display properties.
    - `knowledgeBase`: An array of `KnowledgeFile` objects. These files are used to ground the AI's responses.
    - `theme`: A `ChatTheme` object that defines the workspace's unique color scheme.
    - `functions`: An array of `AppFunction` objects, which are custom AI-powered tools.
    - `chats`: An array of `ChatEntry` objects, storing the entire conversation history for that workspace.

### 2. Backend for Frontend (BFF) Architecture
The application follows a strict BFF pattern to ensure maximum security and scalability. The frontend client is treated as untrusted, and all sensitive operations are handled by the serverless backend API located in the `/api` directory.

- **Security**: All secrets, including the Google Gemini API key and MSAL (Microsoft) client secrets, reside exclusively on the backend. They are loaded from secure environment variables and are never exposed to the client.
- **API Proxying**: All communication with external services is proxied through the backend.
    - **Gemini API**: The client sends requests to `/api/gemini`. The backend function enriches the request (e.g., by fetching knowledge base content) and then securely calls the Google Gemini API with the server-side key.
    - **Microsoft Graph API**: The client sends requests to `/api/graph`. The backend validates the user's session, acquires a Graph API token on the user's behalf, and forwards the request to Microsoft Graph.
- **Session Management**: User sessions are managed via secure, encrypted, `HttpOnly` cookies. The client does not have access to session tokens, preventing token-based XSS attacks.

## Authentication Flow
The application uses a server-side OAuth 2.0 Authorization Code Flow with PKCE for Microsoft authentication. This is a highly secure flow that ensures secrets are never exposed and protects against authorization code interception attacks.

1.  **Login Initiation**: The user clicks the "Sign in with Microsoft" button. The client-side code in `src/auth.ts` simply redirects the browser to `/api/auth/login`.
2.  **PKCE Generation**: The `/api/auth/login` function generates a `code_verifier` and a `code_challenge`. The `code_verifier` is stored in a temporary, secure, `HttpOnly` cookie.
3.  **Redirect to Microsoft**: The backend redirects the user to Microsoft's login page, including the `code_challenge`.
4.  **User Authentication**: The user authenticates with Microsoft and grants consent.
5.  **Callback to Backend**: Microsoft redirects the user back to the registered `redirectUri`, which is `/api/auth/callback`, providing an authorization code.
6.  **Token Exchange**: The `/api/auth/callback` function retrieves the `code_verifier` from the cookie and sends it along with the authorization code and its client secret to Microsoft. Microsoft validates the PKCE codes and, if they match, returns access, refresh, and ID tokens.
7.  **Session Creation**: The backend encrypts the user's unique `homeAccountId` and creates a persistent, secure `HttpOnly` session cookie (`HUB_SESSION`).
8.  **Final Redirect**: The backend responds with a `200 OK` and a simple HTML page containing JavaScript that redirects the user's browser to the application root (`/`). This method ensures the browser reliably sets the session cookie before navigation.
9.  **Authenticated Requests**: For all subsequent requests to `/api/*` endpoints, the browser automatically attaches the `HUB_SESSION` cookie. The backend decrypts this cookie on each request to identify and authenticate the user.

## UI Rendering and Page Navigation
The UI is not framework-based. It relies on dynamically loading HTML partials and manipulating the DOM directly.
- **Page Partials**: All distinct views are stored as separate HTML files in `src/pages/`.
- **Navigation**: The `showPage(pageKey)` function in `src/ui.ts` is the primary method for navigation. It fetches the corresponding HTML from `src/pages/`, injects it into the `<main id="app-root"></main>` element in `index.html`, and then calls `reQueryDOM()` from `src/dom.ts`.
- **Rendering Functions**: `src/ui.ts` contains all functions responsible for rendering data into the DOM (e.g., `renderAllContainers`, `renderChatHistory`, `renderContainerSettings`). These functions read directly from the `state` object.

## Event Handling
All user interactions are handled via event delegation from a single listener on the `<div id="root">` element.
- **File**: `index.tsx`
- **Function**: `bindEventListeners()`
- **Logic**: The listener uses `e.target` and `.closest()` to identify which element was clicked and then calls the appropriate handler function.
- **Handlers**: The actual business logic for events is located in `src/handlers.ts`. These functions are responsible for updating the state and calling UI rendering functions.

## Local Development Architecture
The local development environment requires two servers running concurrently:
1.  **Vite Frontend Server**: Serves the main application (`index.html` and `src/` files) typically on `http://localhost:5173`.
2.  **Azure Functions Backend Server**: Runs the API (`api/` directory) typically on `http://localhost:7071`.

To enable communication, `vite.config.ts` is configured with a **proxy**. Any request made from the frontend to a path starting with `/api` is automatically forwarded to the backend server on port `7071`. The proxy is also configured with `xfwd: true` to forward headers, allowing the backend to be "proxy-aware" and construct correct redirect URLs and cookie domains.

## File Structure Breakdown

- **`index.html`**: The main application shell. Contains the `<div id="root">` and `<main id="app-root">`.
- **`index.tsx`**: The application entry point. Handles initialization, binds the main event listener, and manages the top-level application flow.
- **`api/`**: The server-side Azure Functions project implemented in Python.
    - **Function Directories**: Each HTTP-triggered endpoint is a folder containing an `__init__.py` file. Key examples include `authLogin/`, `authCallback/`, `authLogout/`, `gemini/`, `graphProxy/`, `knowledgeList/`, `knowledgeUpload/`, `knowledgeDelete/`, `publicConfig/`, and `userProfile/`.
    - **`shared/`**: Shared Python modules used by multiple functions:
        - `config.py`: Loads and validates all server-side environment variables.
        - `msal_client.py`: Initializes and exports a singleton MSAL client instance.
        - `session.py`: Handles the encryption, decryption, and creation of secure session cookies.
        - `utils.py`: Helper functions, such as `get_request_origin` for proxy awareness.
    - **`requirements.txt`**: Python dependencies for the function app.
    - **`local.settings.json`**: For local development, stores backend secrets. **This file should not be committed.**
- **`src/`**: Client-side source code directory.
    - **`types.ts`**: Contains all TypeScript interfaces for the application's data structures (`Container`, `Branding`, `User`, etc.).
    - **`state.ts`**: Defines and exports the global `state` object.
    - **`dom.ts`**: Manages all DOM element selections.
    - **`ui.ts`**: Contains all functions that directly manipulate the DOM.
    - **`handlers.ts`**: Contains the business logic for user interactions.
    - **`api.ts`**: Encapsulates all `fetch` calls to the application's own backend API endpoints (e.g., `/api/gemini`, `/api/knowledge/list`).
    - **`auth.ts`**: Manages the client-side stubs for the server-side authentication flow (e.g., `login()` redirects to `/api/auth/login`).
    - **`graph.ts`**: A dedicated service for making calls to our backend's Microsoft Graph proxy at `/api/graph`.
    - **`pages/` & `modals/`**: Directories containing HTML partials for views and dialogs.
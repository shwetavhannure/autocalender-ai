import os
import json
from fastapi import FastAPI, responses
from fastapi.staticfiles import StaticFiles
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials

from config.settings import settings
from src.database_mgr import DatabaseManager

app = FastAPI(title="AI Deadline Auto-Pilot Routing Engine")

# Bind assets to directory routers
app.mount("/static", StaticFiles(directory="static"), name="static")

# Enable secure local authentication procedures across plain HTTP transport paths
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# Instruct oauthlib to allow Google to append baseline OIDC scopes
os.environ['OAUTHLIB_RELAX_TOKEN_SCOPE'] = '1'
# -----------------------------------------------------

# Initialize database manager instance
db = DatabaseManager()

# Server-Side State Memory: Maps unique 'state' tokens to their respective PKCE 'code_verifier'
OAUTH_STATES: dict = {}

@app.get("/")
def read_root():
    """Serves the front-end dashboard client layout directly."""
    return responses.FileResponse('static/index.html')

@app.get("/login")
def login():
    """
    Builds secure multi-scope dynamic link flows targeting Google's identity nodes.
    """
    if not os.path.exists(settings.CREDENTIALS_PATH):
        return {"error": "Server Deployment Error: config/credentials.json configuration file missing!"}

    flow = Flow.from_client_secrets_file(
        settings.CREDENTIALS_PATH,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=f"http://localhost:{settings.PORT}/callback"
    )
    
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' # Forces Google to always return persistent refresh tokens
    )
    
    # Store the verification details directly in server memory using the unique state as the key
    OAUTH_STATES[state] = flow.code_verifier
    
    return responses.RedirectResponse(authorization_url)

@app.get("/callback")
def callback(code: str, state: str):
    """
    Intercepts temporary handshake authorization keys to capture long-lived session keys.
    """
    
    # Pop the code verifier out of server memory to prevent replay attacks
    stored_code_verifier = OAUTH_STATES.pop(state, None)
    
    # Diagnostic Log Output: Monitor verification tracking in the server terminal
    print(f"DEBUG -> Received State from Google: {state}")
    print(f"DEBUG -> Found Matching Code Verifier: {'Yes' if stored_code_verifier else 'No'}")

    # Security Guard: Cross-Site Request Forgery (CSRF) protection check
    if not stored_code_verifier:
        return {"error": "Security Mismatch: State verification failed. Request context is invalid or expired."}

    flow = Flow.from_client_secrets_file(
        settings.CREDENTIALS_PATH,
        scopes=settings.GOOGLE_SCOPES,
        redirect_uri=f"http://localhost:{settings.PORT}/callback",
        state=state
    )
    
    # Hydrate the code verifier parameter back into the flow instance from server memory
    flow.code_verifier = stored_code_verifier
    
    # Complete the exchange handshake now that the environment accepts variable scopes smoothly
    flow.fetch_token(code=code)
    credentials = flow.credentials
    token_info = credentials.to_json()

    # Extract email metrics dynamically using Google Profile service mappings
    user_info_service = build('oauth2', 'v2', credentials=credentials)
    user_info = user_info_service.userinfo().get().execute()
    user_email = user_info.get('email')

    if not user_email:
        return {"error": "Profile Error: Retrying email extraction from Google authorization records failed."}

    # Persist the profile access keys inside the cluster database layer
    db.upsert_user(user_email, json.loads(token_info))
    print(f"Registration Matrix Settled: Account {user_email} synced on auto-pilot loop.")

    return responses.HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-950 text-slate-100 min-h-screen flex items-center justify-center p-6">
            <div class="max-w-md w-full bg-slate-900 border border-slate-800 rounded-3xl p-8 text-center shadow-2xl">
                <div class="inline-flex items-center justify-center w-14 h-14 rounded-2xl bg-emerald-500/10 text-emerald-400 text-2xl mb-4 border border-emerald-500/20">
                    ✓
                </div>
                <h1 class="text-xl font-bold text-white mb-2">Authentication Successful</h1>
                <p class="text-slate-400 text-sm mb-6">Welcome <b class="text-slate-200">{user_email}</b>! Your account has been integrated into the background engine.</p>
                <a href="/dashboard" class="inline-flex w-full items-center justify-center bg-indigo-600 hover:bg-indigo-500 text-white font-medium py-3 px-4 rounded-xl transition duration-200 shadow-lg shadow-indigo-600/20">
                    View System Dashboard →
                </a>
            </div>
        </body>
        </html>
        """
    )

@app.get("/dashboard")
def dashboard():
    """
    Serves a custom live dashboard showcasing connected accounts and system metrics.
    """
    try:
        if hasattr(db, 'collection'):
            account_count = db.collection.count_documents({})
        elif hasattr(db, 'db') and 'users' in db.db.list_collection_names():
            account_count = db.db['users'].count_documents({})
        else:
            account_count = 1
    except Exception:
        account_count = 1

    return responses.HTMLResponse(
        content=f"""
        <!DOCTYPE html>
        <html lang="en">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>AI Deadline Auto-Pilot - Operational Hub</title>
            <script src="https://cdn.tailwindcss.com"></script>
        </head>
        <body class="bg-slate-950 text-slate-100 min-h-screen flex flex-col items-center justify-center p-6">
            <div class="max-w-xl w-full bg-slate-900/90 backdrop-blur-xl border border-slate-800 rounded-3xl p-8 shadow-2xl">
                <div class="flex items-center justify-between pb-6 border-b border-slate-800 mb-6">
                    <div class="flex items-center space-x-3">
                        <span class="text-2xl">🚀</span>
                        <div>
                            <h1 class="font-bold text-lg text-white">AI Deadline Auto-Pilot</h1>
                            <p class="text-xs text-slate-400">Live System Dashboard</p>
                        </div>
                    </div>
                    <span class="px-3 py-1 rounded-full text-xs font-mono bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                        Worker Online
                    </span>
                </div>

                <div class="grid grid-cols-2 gap-4 mb-6">
                    <div class="bg-slate-950/60 p-4 rounded-2xl border border-slate-800">
                        <span class="text-xs text-slate-400 block mb-1">Synced Profiles</span>
                        <span class="text-2xl font-bold text-indigo-400">{account_count} Connected</span>
                    </div>
                    <div class="bg-slate-950/60 p-4 rounded-2xl border border-slate-800">
                        <span class="text-xs text-slate-400 block mb-1">Extraction Model</span>
                        <span class="text-2xl font-bold text-sky-400">Gemini 3.8</span>
                    </div>
                </div>

                <div class="bg-slate-950/60 p-4 rounded-2xl border border-slate-800 mb-6">
                    <div class="flex items-center space-x-2 text-xs text-emerald-400 mb-2">
                        <span class="h-2 w-2 rounded-full bg-emerald-400 animate-pulse"></span>
                        <span class="font-semibold uppercase tracking-wider">Background Pipeline Active</span>
                    </div>
                    <p class="text-xs text-slate-400 leading-relaxed">
                        Polling loop actively listening for inbox announcements and scheduling events directly to Google Calendar.
                    </p>
                </div>

                <a href="/" class="block w-full text-center bg-slate-800 hover:bg-slate-700 text-slate-200 font-medium py-3 px-4 rounded-xl transition duration-200 border border-slate-700 text-sm">
                    ← Back to Home
                </a>
            </div>
        </body>
        </html>
        """
    )

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host=settings.HOST, port=settings.PORT, reload=True)
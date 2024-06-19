from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from authlib.integrations.starlette_client import OAuth
from starlette.config import Config
from starlette.middleware.sessions import SessionMiddleware
from starlette.templating import Jinja2Templates
from urllib.parse import urljoin

app = FastAPI()

# Configuration for OAuth
config = Config('.env')
oauth = OAuth(config)

# Register the Google OAuth client
oauth.register(
    name='google',
    client_id=config('GOOGLE_CLIENT_ID'),
    client_secret=config('GOOGLE_CLIENT_SECRET'),
    server_metadata_url='https://accounts.google.com/.well-known/openid-configuration',
    client_kwargs={'scope': 'openid profile email'}
)

# Register the Facebook OAuth client
oauth.register(
    name='facebook',
    client_id=config('FACEBOOK_CLIENT_ID'),
    client_secret=config('FACEBOOK_CLIENT_SECRET'),
    authorize_url='https://www.facebook.com/v10.0/dialog/oauth',
    access_token_url='https://graph.facebook.com/v10.0/oauth/access_token',
    client_kwargs={'scope': 'email public_profile'}
)

# Secret key for session management
app.add_middleware(SessionMiddleware, secret_key=config('SECRET_KEY'))

templates = Jinja2Templates(directory="templates")


@app.get('/', response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.route('/login/google')
async def login_google(request: Request):
    redirect_uri = urljoin(str(request.base_url), '/auth/google')
    return await oauth.google.authorize_redirect(request, redirect_uri)


@app.route('/auth/google')
async def auth_google(request: Request):
    user = await oauth.google.authorize_access_token(request)
    # id_token = token.get('id_token')
    # user = None
    # if id_token:
    #     user = await oauth.google.parse_id_token(request, token)
    response = JSONResponse(user or {})
    response.set_cookie(key='access_token', value=user['access_token'])
    return response


@app.route('/login/facebook')
async def login_facebook(request: Request):
    redirect_uri = urljoin(str(request.base_url), '/auth/facebook')
    return await oauth.facebook.authorize_redirect(request, redirect_uri)


@app.route('/auth/facebook')
async def auth_facebook(request: Request):
    token = await oauth.facebook.authorize_access_token(request)
    resp = await oauth.facebook.get('https://graph.facebook.com/me?fields=id,name,email', token=token)
    user = resp.json()
    response = JSONResponse(user)
    response.set_cookie(key='access_token', value=token['access_token'])
    return response


@app.get('/logout')
async def logout(request: Request):
    response = RedirectResponse(url='/')
    response.delete_cookie('access_token')
    return response


@app.get('/profile', response_class=HTMLResponse)
async def profile(request: Request):
    access_token = request.cookies.get('access_token')
    if not access_token:
        raise HTTPException(status_code=401, detail='Not authenticated')

    user = None
    try:
        user = await oauth.google.parse_id_token(request, {'access_token': access_token})
    except Exception:
        try:
            resp = await oauth.facebook.get('https://graph.facebook.com/me?fields=id,name,email',
                                            token={'access_token': access_token})
            user = resp.json()
        except Exception:
            raise HTTPException(status_code=401, detail='Could not fetch user information')

    return templates.TemplateResponse("profile.html", {"request": request, "user": user})


if __name__ == '__main__':
    import uvicorn

    uvicorn.run(app, host='0.0.0.0', port=8000)

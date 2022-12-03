from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from routers import route_todo, route_auth
from shemas import SuccessMsg, CsrfSettings
from fastapi_csrf_protect import CsrfProtect
from fastapi.responses import JSONResponse
from fastapi_csrf_protect.exceptions import CsrfProtectError

app = FastAPI()
app.include_router(route_todo.router)
app.include_router(route_auth.router)

# setting cors
# origins=[]の中には、ホワイトリスト化したいurlを入れる
origins = ["http://localhost:3000"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@CsrfProtect.load_config
def get_csrf_config():
    return CsrfSettings()

@app.exception_handler(CsrfProtectError)
def csrf_protect_exception_handler(request: Request, exc: CsrfProtectError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.message}
    )

# response_modelは型を指定
@app.get("/", response_model=SuccessMsg)
def root():
    return {"message": "Welcome to Fast API"}
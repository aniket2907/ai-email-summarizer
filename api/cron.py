from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get('/api/cron')
def cron():
    return JSONResponse({'ok': True, 'message': 'Hello from AI Email Summarizer starter!'})
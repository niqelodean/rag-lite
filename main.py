from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.responses import FileResponse 
from pydantic import BaseModel

from retrieve import Retriever
from ask import answer

retriever = None


@asynccontextmanager
async def lifespan(app):
    global retriever
    retriever = Retriever()
    yield


app = FastAPI(lifespan=lifespan)

@app.get("/")
def serve_frontend():
    return FileResponse("index.html")

class AskBody(BaseModel):
    question: str
    k: int = 3


@app.get("/search")
def search(q: str, k: int = 3):
    return retriever.search(q, k)


@app.post("/ask")
def ask(body: AskBody):
    return answer(body.question, retriever, body.k)
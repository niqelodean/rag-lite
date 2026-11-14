from contextlib import asynccontextmanager
from fastapi import FastAPI
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


class AskBody(BaseModel):
    question: str
    k: int = 3


@app.get("/search")
def search(q: str, k: int = 3):
    return retriever.search(q, k)


@app.post("/ask")
def ask(body: AskBody):
    return answer(body.question, retriever, body.k)
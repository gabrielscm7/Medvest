from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Aluno
from app.schemas.aluno import AlunoCreate, AlunoResponse, BemEstarCreate, BemEstarResponse
from app.schemas.auth import LoginRequest, TokenResponse
from app.services.auth import (
    criar_token,
    get_aluno_atual,
    hash_senha,
    verificar_senha,
)

router = APIRouter(prefix="/api/auth", tags=["Auth"])


@router.post("/register", response_model=AlunoResponse, status_code=status.HTTP_201_CREATED)
def register(body: AlunoCreate, db: Session = Depends(get_db)):
    if db.query(Aluno).filter_by(email=body.email).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email já cadastrado",
        )
    aluno = Aluno(
        nome=body.nome,
        email=body.email,
        senha_hash=hash_senha(body.senha),
        data_prova_dia1=body.data_prova_dia1,
        data_prova_dia2=body.data_prova_dia2,
        meta_instituicao=body.meta_instituicao,
    )
    db.add(aluno)
    db.commit()
    db.refresh(aluno)
    return aluno


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)):
    aluno = db.query(Aluno).filter_by(email=body.email).first()
    if not aluno or not verificar_senha(body.senha, aluno.senha_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email ou senha inválidos",
        )
    token = criar_token(aluno.id)
    return TokenResponse(access_token=token)


@router.get("/me", response_model=AlunoResponse)
def me(aluno: Aluno = Depends(get_aluno_atual)):
    return aluno


@router.post("/bem-estar", response_model=BemEstarResponse, status_code=status.HTTP_201_CREATED)
def registrar_bem_estar(
    body: BemEstarCreate,
    aluno: Aluno = Depends(get_aluno_atual),
    db: Session = Depends(get_db),
):
    from app.models import RegistroBemEstar

    registro = (
        db.query(RegistroBemEstar)
        .filter_by(aluno_id=aluno.id, data=body.data)
        .first()
    )
    if registro:
        registro.sono = body.sono
        registro.energia = body.energia
    else:
        registro = RegistroBemEstar(
            aluno_id=aluno.id, data=body.data, sono=body.sono, energia=body.energia
        )
        db.add(registro)
    db.commit()
    return registro

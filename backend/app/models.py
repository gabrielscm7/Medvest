from typing import List, Optional
from datetime import date as py_date, datetime
from sqlalchemy import ForeignKey, String, Text, Numeric, Boolean, Date, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Area(Base):
    __tablename__ = "area"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255))
    peso_medicina: Mapped[float] = mapped_column(Numeric, default=1.0)

    # Relationships
    competencias: Mapped[List["Competencia"]] = relationship("Competencia", back_populates="area", cascade="all, delete-orphan")


class Competencia(Base):
    __tablename__ = "competencia"

    id: Mapped[int] = mapped_column(primary_key=True)
    area_id: Mapped[int] = mapped_column(ForeignKey("area.id"))
    numero: Mapped[int] = mapped_column()
    descricao: Mapped[str] = mapped_column(Text)

    # Relationships
    area: Mapped["Area"] = relationship("Area", back_populates="competencias")
    habilidades: Mapped[List["Habilidade"]] = relationship("Habilidade", back_populates="competencia", cascade="all, delete-orphan")


class Habilidade(Base):
    __tablename__ = "habilidade"

    id: Mapped[int] = mapped_column(primary_key=True)
    competencia_id: Mapped[int] = mapped_column(ForeignKey("competencia.id"))
    codigo: Mapped[str] = mapped_column(String(10))  # e.g., 'H1', 'H12'
    descricao: Mapped[str] = mapped_column(Text)

    # Relationships
    competencia: Mapped["Competencia"] = relationship("Competencia", back_populates="habilidades")
    questoes: Mapped[List["QuestaoIdentificada"]] = relationship("QuestaoIdentificada", back_populates="habilidade")
    dominios: Mapped[List["DominioHabilidade"]] = relationship("DominioHabilidade", back_populates="habilidade")
    flashcards: Mapped[List["Flashcard"]] = relationship("Flashcard", back_populates="habilidade")


class Aluno(Base):
    __tablename__ = "aluno"

    id: Mapped[int] = mapped_column(primary_key=True)
    nome: Mapped[str] = mapped_column(String(255))
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    senha_hash: Mapped[str] = mapped_column(String(255))
    data_prova_dia1: Mapped[py_date] = mapped_column(Date, default=py_date(2026, 11, 8))
    data_prova_dia2: Mapped[py_date] = mapped_column(Date, default=py_date(2026, 11, 15))
    meta_instituicao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    simulados: Mapped[List["SimuladoUpload"]] = relationship("SimuladoUpload", back_populates="aluno", cascade="all, delete-orphan")
    dominios: Mapped[List["DominioHabilidade"]] = relationship("DominioHabilidade", back_populates="aluno", cascade="all, delete-orphan")
    redacoes: Mapped[List["Redacao"]] = relationship("Redacao", back_populates="aluno", cascade="all, delete-orphan")
    flashcards: Mapped[List["Flashcard"]] = relationship("Flashcard", back_populates="aluno", cascade="all, delete-orphan")
    plano_temporal: Mapped[Optional["PlanoTemporal"]] = relationship("PlanoTemporal", uselist=False, back_populates="aluno", cascade="all, delete-orphan")
    registros_bem_estar: Mapped[List["RegistroBemEstar"]] = relationship("RegistroBemEstar", back_populates="aluno", cascade="all, delete-orphan")


class SimuladoUpload(Base):
    __tablename__ = "simulado_upload"

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id"))
    arquivo_path: Mapped[str] = mapped_column(String(512))
    tipo: Mapped[str] = mapped_column(String(50))  # e.g., 'caderno_prova', 'gabarito_oficial'
    total_questoes_detectado: Mapped[Optional[int]] = mapped_column(nullable=True)
    alternativas_por_questao: Mapped[Optional[int]] = mapped_column(nullable=True)
    processado: Mapped[bool] = mapped_column(Boolean, default=False)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="simulados")
    questoes: Mapped[List["QuestaoIdentificada"]] = relationship("QuestaoIdentificada", back_populates="simulado_upload", cascade="all, delete-orphan")


class QuestaoIdentificada(Base):
    __tablename__ = "questao_identificada"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulado_upload_id: Mapped[int] = mapped_column(ForeignKey("simulado_upload.id"))
    numero_questao: Mapped[int] = mapped_column()
    habilidade_id: Mapped[Optional[int]] = mapped_column(ForeignKey("habilidade.id"), nullable=True)
    tema_livre: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    dificuldade_estimada: Mapped[Optional[float]] = mapped_column(Numeric, nullable=True)
    texto_questao: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resposta_aluno: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    resposta_correta: Mapped[Optional[str]] = mapped_column(String(1), nullable=True)
    acerto: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    classificacao_confirmada_manualmente: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    simulado_upload: Mapped["SimuladoUpload"] = relationship("SimuladoUpload", back_populates="questoes")
    habilidade: Mapped[Optional["Habilidade"]] = relationship("Habilidade", back_populates="questoes")


class DominioHabilidade(Base):
    __tablename__ = "dominio_habilidade"

    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id"), primary_key=True)
    habilidade_id: Mapped[int] = mapped_column(ForeignKey("habilidade.id"), primary_key=True)
    taxa_acerto: Mapped[float] = mapped_column(Numeric, default=0.0)
    ultima_pratica: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    prioridade_calculada: Mapped[float] = mapped_column(Numeric, default=0.0)

    # Relationships
    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="dominios")
    habilidade: Mapped["Habilidade"] = relationship("Habilidade", back_populates="dominios")


class Redacao(Base):
    __tablename__ = "redacao"

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id"))
    arquivo_path: Mapped[str] = mapped_column(String(512))
    texto_ocr: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    nota_c1: Mapped[int] = mapped_column(default=0)
    nota_c2: Mapped[int] = mapped_column(default=0)
    nota_c3: Mapped[int] = mapped_column(default=0)
    nota_c4: Mapped[int] = mapped_column(default=0)
    nota_c5: Mapped[int] = mapped_column(default=0)
    nota_total: Mapped[int] = mapped_column(default=0)
    feedback: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="redacoes")


class Flashcard(Base):
    __tablename__ = "flashcard"

    id: Mapped[int] = mapped_column(primary_key=True)
    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id"))
    habilidade_id: Mapped[int] = mapped_column(ForeignKey("habilidade.id"))
    pergunta: Mapped[str] = mapped_column(Text)
    resposta: Mapped[str] = mapped_column(Text)
    fator_facilidade: Mapped[float] = mapped_column(Numeric, default=2.5)
    intervalo_dias: Mapped[int] = mapped_column(default=1)
    proxima_revisao: Mapped[py_date] = mapped_column(Date)
    criado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="flashcards")
    habilidade: Mapped["Habilidade"] = relationship("Habilidade", back_populates="flashcards")


class PlanoTemporal(Base):
    __tablename__ = "plano_temporal"

    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id"), primary_key=True)
    semanas_f1: Mapped[int] = mapped_column(default=0)
    semanas_f2: Mapped[int] = mapped_column(default=0)
    semanas_f3: Mapped[int] = mapped_column(default=0)
    semanas_f4: Mapped[int] = mapped_column(default=0)
    carga_diaria_questoes: Mapped[int] = mapped_column(default=0)
    recalculado_em: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    # Relationships
    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="plano_temporal")


class RegistroBemEstar(Base):
    __tablename__ = "registro_bem_estar"

    aluno_id: Mapped[int] = mapped_column(ForeignKey("aluno.id"), primary_key=True)
    data: Mapped[py_date] = mapped_column(Date, primary_key=True)
    sono: Mapped[str] = mapped_column(String(50))  # e.g., 'ruim', 'ok', 'bom'
    energia: Mapped[str] = mapped_column(String(50))  # e.g., 'baixa', 'media', 'alta'

    # Relationships
    aluno: Mapped["Aluno"] = relationship("Aluno", back_populates="registros_bem_estar")

import os
import json
from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine, Base
from app.models import Area, Competencia, Habilidade

# Default weights for Medicine (Natural Sciences and Mathematics carry the highest weight)
AREA_WEIGHTS = {
    "Ciências da Natureza e suas Tecnologias": 1.5,
    "Matemática e suas Tecnologias": 1.5,
    "Linguagens, Códigos e suas Tecnologias": 1.0,
    "Ciências Humanas e suas Tecnologias": 1.0
}

def seed_matrix(db: Session, json_path: str):
    print(f"Lendo matriz estruturada a partir de: {json_path}")
    if not os.path.exists(json_path):
        raise FileNotFoundError(f"Arquivo matriz_estruturada.json não encontrado no caminho: {json_path}")

    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)

    for area_nome, area_data in data.items():
        # Check if area already exists
        area = db.query(Area).filter(Area.nome == area_nome).first()
        weight = AREA_WEIGHTS.get(area_nome, 1.0)
        if not area:
            area = Area(nome=area_nome, peso_medicina=weight)
            db.add(area)
            db.commit()
            db.refresh(area)
            print(f"Área criada: {area_nome} (Peso: {weight})")
        else:
            # Update weight if necessary
            area.peso_medicina = weight
            db.commit()
            print(f"Área já existe: {area_nome} (Atualizada para peso {weight})")

        # Seed competencies
        competencias = area_data.get("competencias", [])
        for comp_data in competencias:
            comp_num = comp_data.get("numero")
            comp_desc = comp_data.get("descricao")

            comp = db.query(Competencia).filter(
                Competencia.area_id == area.id,
                Competencia.numero == comp_num
            ).first()

            if not comp:
                comp = Competencia(
                    area_id=area.id,
                    numero=comp_num,
                    descricao=comp_desc
                )
                db.add(comp)
                db.commit()
                db.refresh(comp)
                print(f"  Competência {comp_num} criada.")
            else:
                comp.descricao = comp_desc
                db.commit()

            # Seed skills
            habilidades = comp_data.get("habilidades", [])
            for hab_data in habilidades:
                hab_codigo = hab_data.get("codigo")
                hab_desc = hab_data.get("descricao")

                hab = db.query(Habilidade).filter(
                    Habilidade.competencia_id == comp.id,
                    Habilidade.codigo == hab_codigo
                ).first()

                if not hab:
                    hab = Habilidade(
                        competencia_id=comp.id,
                        codigo=hab_codigo,
                        descricao=hab_desc
                    )
                    db.add(hab)
                    print(f"    Habilidade {hab_codigo} adicionada.")
                else:
                    hab.descricao = hab_desc
            db.commit()

    print("Matriz seed concluída com sucesso!")

if __name__ == "__main__":
    # Ensure tables are created (useful for SQLite local startup)
    print("Criando tabelas do banco de dados (se não existirem)...")
    Base.metadata.create_all(bind=engine)
    
    # Path to json file (workspace root)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    app_dir = os.path.dirname(script_dir)
    backend_dir = os.path.dirname(app_dir)
    root_dir = os.path.dirname(backend_dir)
    json_file_path = os.path.join(root_dir, "matriz_estruturada.json")
    
    session = SessionLocal()
    try:
        seed_matrix(session, json_file_path)
    finally:
        session.close()

import json

from app.core.security import hash_password
from app.db.session import Base, SessionLocal, engine
from app.models.models import Category, Message, Professional, Review, ServiceRequest, User

DEFAULT_AVAILABILITY = json.dumps({
    "monday": ["08:00", "09:00", "14:00"],
    "tuesday": ["08:00", "09:00", "14:00"],
    "wednesday": ["08:00", "14:00"],
    "thursday": ["08:00", "09:00", "14:00"],
    "friday": ["08:00", "14:00"],
    "saturday": ["09:00", "10:00"],
    "sunday": [],
})

DIARISTA_SPECS = json.dumps({
    "tipo_limpeza": "residencial",
    "frequencia": "semanal",
    "traz_material": False,
    "metros_aprox": 80,
    "inclui_cozinha": True,
    "inclui_banheiros": True,
    "inclui_passar_roupa": False,
})

BABA_SPECS = json.dumps({
    "faixa_etaria": "0-3 anos",
    "experiencia_anos": 5,
    "turnos": ["manhã", "tarde"],
    "numero_criancas": 2,
    "primeiros_socorros": True,
    "ajuda_tarefas_domesticas": True,
})


def ensure_extra_categories():
    """Garante que as categorias Diarista e Babá existam."""
    db = SessionLocal()
    try:
        for name, icon, description in [
            ("Diarista", "FaBroom", "Limpeza residencial e comercial"),
            ("Babá", "FaBaby", "Cuidado de crianças e apoio familiar"),
        ]:
            exists = db.query(Category).filter(Category.name == name).first()
            if not exists:
                db.add(Category(name=name, icon=icon, description=description))
        db.commit()
    finally:
        db.close()


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        if db.query(User).first():
            return

        client = User(name="Anderson Cliente", email="cliente@zola.com", password_hash=hash_password("123456"), role="client")
        pro_diarista = User(name="Mariana Costa", email="diarista@zola.com", password_hash=hash_password("123456"), role="professional")
        pro_baba = User(name="Patrícia Souza", email="baba@zola.com", password_hash=hash_password("123456"), role="professional")
        db.add_all([client, pro_diarista, pro_baba])
        db.flush()

        cats = [
            Category(name="Diarista", icon="FaBroom", description="Limpeza residencial e comercial"),
            Category(name="Babá", icon="FaBaby", description="Cuidado de crianças e apoio familiar"),
        ]
        db.add_all(cats)
        db.flush()

        profs = [
            Professional(
                user_id=pro_diarista.id,
                category_id=cats[0].id,
                title="Diarista caprichosa",
                description="Limpeza pesada, pós-obra e organização de ambientes.",
                city="Praia Grande",
                state="SP",
                price_from=160,
                rating=4.8,
                reviews_count=51,
                whatsapp="5513977777777",
                is_featured=True,
                image="https://images.unsplash.com/photo-1581578731548-c64695cc6952",
                professional_type="diarista",
                job_specs=DIARISTA_SPECS,
                availability=DEFAULT_AVAILABILITY,
            ),
            Professional(
                user_id=pro_baba.id,
                category_id=cats[1].id,
                title="Babá experiente",
                description="Cuidado infantil com carinho, rotina educativa e apoio leve nas tarefas domésticas.",
                city="Santos",
                state="SP",
                price_from=140,
                rating=4.9,
                reviews_count=33,
                whatsapp="5513966666666",
                is_featured=True,
                image="https://images.unsplash.com/photo-1584515933487-779824ad3d8f",
                professional_type="baba",
                job_specs=BABA_SPECS,
                availability=DEFAULT_AVAILABILITY,
            ),
        ]
        db.add_all(profs)
        db.flush()

        reviews = [
            Review(professional_id=profs[0].id, client_name="Fernando", rating=5, comment="Minha casa ficou impecável. Recomendo demais."),
            Review(professional_id=profs[1].id, client_name="Camila", rating=5, comment="Babá carinhosa e muito responsável."),
        ]
        db.add_all(reviews)
        db.flush()

        req = ServiceRequest(
            client_id=client.id,
            professional_id=profs[0].id,
            category_id=cats[0].id,
            title="Limpeza residencial completa",
            description="Preciso de faxina semanal em apartamento de 80m².",
            location="Santos - SP",
            status="in_progress",
            budget=160,
        )
        db.add(req)
        db.flush()
        db.add_all([
            Message(request_id=req.id, sender_id=client.id, content="Olá, você consegue atender na quinta?"),
            Message(request_id=req.id, sender_id=pro_diarista.id, content="Consigo sim. Tenho horário às 14h."),
        ])
        db.commit()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
    print("Banco criado e populado com sucesso.")

"""
Script pour lister les utilisateurs de la base de données
"""
from app.database import get_db
from app.models.user import User


def list_users():
    """Liste tous les utilisateurs de la base de données"""
    db = next(get_db())
    try:
        users = db.query(User).all()
        
        if not users:
            print("Aucun utilisateur trouvé dans la base de données.")
            return
        
        print(f"\n{'='*80}")
        print(f"Liste des utilisateurs ({len(users)} utilisateur(s))")
        print(f"{'='*80}\n")
        
        for user in users:
            print(f"ID: {user.id}")
            print(f"Email: {user.email}")
            print(f"Actif: {'Oui' if user.is_active else 'Non'}")
            print(f"Créé le: {user.created_at}")
            print(f"{'-'*80}")
    finally:
        db.close()


if __name__ == "__main__":
    list_users()

import bcrypt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Vérifie si le mot de passe en clair correspond au hash"""
    if not plain_password or not hashed_password:
        return False
    
    try:
        # Les hashs bcrypt sont compatibles entre passlib et bcrypt direct
        # car passlib utilise bcrypt en interne
        password_bytes = plain_password.encode('utf-8')
        hash_bytes = hashed_password.encode('utf-8')
        return bcrypt.checkpw(password_bytes, hash_bytes)
    except (ValueError, TypeError, AttributeError):
        # Si le hash est invalide ou mal formaté
        return False


def get_password_hash(password: str) -> str:
    """Génère un hash bcrypt du mot de passe (compatible avec passlib)"""
    if not password:
        raise ValueError("Le mot de passe ne peut pas être vide")
    
    # Utiliser bcrypt directement pour éviter les problèmes de compatibilité
    # Les hashs générés sont compatibles avec ceux de passlib
    password_bytes = password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password_bytes, salt)
    return hashed.decode('utf-8')

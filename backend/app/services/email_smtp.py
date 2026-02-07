"""
Service pour envoyer des emails via SMTP.
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class EmailSMTPService:
    """
    Service pour envoyer des emails via SMTP.
    Encapsule les fonctionnalités d'envoi d'email dans une classe.
    """
    
    def __init__(self):
        """Initialise le service avec les paramètres de configuration."""
        self.settings = get_settings()
    
    def send_email(
        self,
        to_email: str,
        subject: str,
        text_content: str,
        html_content: Optional[str] = None,
        from_email: Optional[str] = None,
    ) -> bool:
        """
        Envoie un email via SMTP.
        
        Args:
            to_email: Adresse email du destinataire
            subject: Sujet de l'email
            text_content: Corps de l'email en texte brut
            html_content: Corps de l'email en HTML (optionnel)
            from_email: Adresse email de l'expéditeur (par défaut: imap_user)
        
        Returns:
            True si l'email a été envoyé avec succès, False sinon
        """
        return send_email(
            to_email=to_email,
            subject=subject,
            body_text=text_content,
            body_html=html_content,
            from_email=from_email,
        )


def send_email(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    from_email: Optional[str] = None,
) -> bool:
    """
    Envoie un email via SMTP.
    
    Args:
        to_email: Adresse email du destinataire
        subject: Sujet de l'email
        body_text: Corps de l'email en texte brut
        body_html: Corps de l'email en HTML (optionnel)
        from_email: Adresse email de l'expéditeur (par défaut: imap_user)
    
    Returns:
        True si l'email a été envoyé avec succès, False sinon
    """
    try:
        logger.info(f"📧 [EmailSMTP] Démarrage de l'envoi d'email")
        logger.info(f"📧 [EmailSMTP] Destinataire: {to_email}")
        logger.info(f"📧 [EmailSMTP] Sujet: {subject}")
        
        # Utiliser les paramètres IMAP pour SMTP (même serveur généralement)
        smtp_host = settings.imap_host
        smtp_port = 587  # Port SMTP standard avec STARTTLS
        smtp_user = settings.imap_user
        smtp_password = settings.imap_password
        from_addr = from_email or smtp_user
        
        logger.info(f"📧 [EmailSMTP] Configuration SMTP:")
        logger.info(f"📧 [EmailSMTP]   - Serveur: {smtp_host}:{smtp_port}")
        logger.info(f"📧 [EmailSMTP]   - Utilisateur: {smtp_user}")
        logger.info(f"📧 [EmailSMTP]   - Expéditeur: {from_addr}")
        
        # Créer le message
        logger.info(f"📧 [EmailSMTP] Création du message email...")
        msg = MIMEMultipart('alternative')
        msg['From'] = from_addr
        msg['To'] = to_email
        msg['Subject'] = subject
        
        # Ajouter le texte brut
        part_text = MIMEText(body_text, 'plain', 'utf-8')
        msg.attach(part_text)
        logger.info(f"📧 [EmailSMTP] Texte brut ajouté ({len(body_text)} caractères)")
        
        # Ajouter le HTML si fourni
        if body_html:
            part_html = MIMEText(body_html, 'html', 'utf-8')
            msg.attach(part_html)
            logger.info(f"📧 [EmailSMTP] HTML ajouté ({len(body_html)} caractères)")
        
        # Envoyer l'email
        logger.info(f"📧 [EmailSMTP] Connexion au serveur SMTP...")
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            logger.info(f"📧 [EmailSMTP] Activation de STARTTLS...")
            server.starttls()  # Activer le chiffrement TLS
            logger.info(f"📧 [EmailSMTP] Authentification...")
            server.login(smtp_user, smtp_password)
            logger.info(f"📧 [EmailSMTP] Authentification réussie")
            logger.info(f"📧 [EmailSMTP] Envoi du message...")
            server.send_message(msg)
            logger.info(f"📧 [EmailSMTP] Message envoyé au serveur")
        
        logger.info(f"✅ [EmailSMTP] Email envoyé avec succès à {to_email}")
        return True
        
    except smtplib.SMTPException as e:
        logger.error(f"❌ [EmailSMTP] Erreur SMTP lors de l'envoi de l'email: {e}")
        logger.error(f"❌ [EmailSMTP] Type d'erreur: {type(e).__name__}")
        logger.error(f"❌ [EmailSMTP] Détails: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"❌ [EmailSMTP] Erreur lors de l'envoi de l'email: {e}", exc_info=True)
        logger.error(f"❌ [EmailSMTP] Type d'erreur: {type(e).__name__}")
        return False


def send_email_with_attachment(
    to_email: str,
    subject: str,
    body_text: str,
    body_html: Optional[str] = None,
    from_email: Optional[str] = None,
    attachment_bytes: Optional[bytes] = None,
    attachment_filename: str = "attachment",
    attachment_mimetype: str = "application/octet-stream",
) -> bool:
    """
    Envoie un email avec une pièce jointe (ex: fichier audio).

    Args:
        to_email: Destinataire
        subject: Sujet
        body_text: Corps texte
        body_html: Corps HTML (optionnel)
        from_email: Expéditeur (défaut: imap_user)
        attachment_bytes: Contenu binaire de la pièce jointe
        attachment_filename: Nom du fichier joint
        attachment_mimetype: Type MIME (ex: "audio/mpeg" pour MP3)

    Returns:
        True si l'email a été envoyé avec succès, False sinon.
    """
    try:
        logger.info(f"📧 [EmailSMTP] Envoi d'email avec pièce jointe vers {to_email}")
        smtp_host = settings.imap_host
        smtp_port = 587
        smtp_user = settings.imap_user
        smtp_password = settings.imap_password
        from_addr = from_email or smtp_user

        if attachment_bytes:
            msg = MIMEMultipart("mixed")
        else:
            msg = MIMEMultipart("alternative")
        msg["From"] = from_addr
        msg["To"] = to_email
        msg["Subject"] = subject

        part_text = MIMEText(body_text, "plain", "utf-8")
        if attachment_bytes:
            msg.attach(part_text)
            if body_html:
                part_html = MIMEText(body_html, "html", "utf-8")
                msg.attach(part_html)
        else:
            msg.attach(part_text)
            if body_html:
                part_html = MIMEText(body_html, "html", "utf-8")
                msg.attach(part_html)

        if attachment_bytes:
            part = MIMEBase(*attachment_mimetype.split("/", 1))
            part.set_payload(attachment_bytes)
            encoders.encode_base64(part)
            part.add_header(
                "Content-Disposition",
                "attachment",
                filename=("utf-8", "", attachment_filename),
            )
            msg.attach(part)
            logger.info(f"📧 [EmailSMTP] Pièce jointe: {attachment_filename} ({len(attachment_bytes)} octets)")

        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.send_message(msg)
        logger.info(f"✅ [EmailSMTP] Email avec pièce jointe envoyé à {to_email}")
        return True
    except Exception as e:
        logger.error(f"❌ [EmailSMTP] Erreur envoi email avec pièce jointe: {e}", exc_info=True)
        return False


def format_agent_output_as_email(
    output_raw: str,
    output_parsed: Optional[dict] = None,
    agent_name: Optional[str] = None,
    input_text: Optional[str] = None,
    execution_time_ms: Optional[int] = None,
) -> tuple[str, str]:
    """
    Formate la sortie d'un agent en texte et HTML pour l'email.
    
    Returns:
        Tuple (body_text, body_html)
    """
    logger.info(f"📧 [EmailSMTP] Formatage de la sortie de l'agent pour l'email")
    logger.info(f"📧 [EmailSMTP]   - Agent: {agent_name}")
    logger.info(f"📧 [EmailSMTP]   - Input: {input_text[:100] if input_text else 'N/A'}...")
    logger.info(f"📧 [EmailSMTP]   - Sortie brute: {len(output_raw)} caractères")
    
    # Corps texte
    body_text_parts = []
    if agent_name:
        body_text_parts.append(f"Agent: {agent_name}\n")
    if input_text:
        body_text_parts.append(f"Input: {input_text}\n")
    body_text_parts.append("\n" + "="*50 + "\n")
    body_text_parts.append("RÉSULTAT:\n")
    body_text_parts.append("="*50 + "\n\n")
    body_text_parts.append(output_raw)
    if execution_time_ms:
        body_text_parts.append(f"\n\nTemps d'exécution: {execution_time_ms}ms")
    
    body_text = "\n".join(body_text_parts)
    
    # Corps HTML
    body_html_parts = []
    body_html_parts.append("<html><body style='font-family: Arial, sans-serif; line-height: 1.6; color: #333;'>")
    
    if agent_name:
        body_html_parts.append(f"<p><strong>Agent:</strong> {agent_name}</p>")
    if input_text:
        body_html_parts.append(f"<p><strong>Input:</strong> {input_text}</p>")
    
    body_html_parts.append("<hr style='border: 1px solid #ddd; margin: 20px 0;'>")
    body_html_parts.append("<h2 style='color: #00D9FF;'>RÉSULTAT</h2>")
    
    # Convertir le Markdown en HTML basique (ou utiliser une bibliothèque)
    # Pour l'instant, on utilise un simple formatage
    import re
    html_content = output_raw
    
    # Convertir les titres
    html_content = re.sub(r'^# (.*?)$', r'<h1 style="color: #00D9FF;">\1</h1>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^## (.*?)$', r'<h2 style="color: #00D9FF;">\1</h2>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'^### (.*?)$', r'<h3 style="color: #00D9FF;">\1</h3>', html_content, flags=re.MULTILINE)
    
    # Convertir les liens
    html_content = re.sub(r'\[([^\]]+)\]\(([^\)]+)\)', r'<a href="\2" style="color: #00D9FF;">\1</a>', html_content)
    
    # Convertir le texte en gras
    html_content = re.sub(r'\*\*([^\*]+)\*\*', r'<strong>\1</strong>', html_content)
    
    # Convertir les listes
    html_content = re.sub(r'^- (.*?)$', r'<li>\1</li>', html_content, flags=re.MULTILINE)
    html_content = re.sub(r'(<li>.*?</li>)', r'<ul>\1</ul>', html_content, flags=re.DOTALL)
    
    # Convertir les paragraphes (lignes vides)
    html_content = re.sub(r'\n\n', r'</p><p>', html_content)
    html_content = '<p>' + html_content + '</p>'
    
    # Préserver les sauts de ligne
    html_content = html_content.replace('\n', '<br>')
    
    body_html_parts.append(f"<div style='background-color: #f5f5f5; padding: 15px; border-radius: 5px;'>")
    body_html_parts.append(html_content)
    body_html_parts.append("</div>")
    
    if execution_time_ms:
        body_html_parts.append(f"<p style='margin-top: 20px; color: #666; font-size: 0.9em;'>Temps d'exécution: {execution_time_ms}ms</p>")
    
    body_html_parts.append("</body></html>")
    body_html = "\n".join(body_html_parts)
    
    logger.info(f"📧 [EmailSMTP] Formatage terminé:")
    logger.info(f"📧 [EmailSMTP]   - Texte: {len(body_text)} caractères")
    logger.info(f"📧 [EmailSMTP]   - HTML: {len(body_html)} caractères")
    
    return body_text, body_html

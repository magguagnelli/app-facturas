# services/email_service.py
import smtplib
import ssl
from email.message import EmailMessage
from core.email import EMAIL_HOST, EMAIL_PORT, EMAIL_USER, EMAIL_PASS, EMAIL_FROM

def send_password_email(to_email: str, temp_password: str) -> None:
    """
    Envía correo con layout HTML incluyendo datos de acceso.
    
    Params:
        to_email: correo del destinatario
        temp_password: contraseña temporal
        clue: correo o CLUE del usuario
        image_top: imagen codificada en base64 para la parte superior
        image_bottom: imagen codificada en base64 para la parte inferior
    """

    #to_email = to_email.strip().lower()

    # Leer imágenes base64 (ya generadas)
    with open("top_base64.txt") as f:
        image_top = f.read()

    # Crear mensaje
    msg = EmailMessage()
    msg["Subject"] = "DATOS DE ACCESO IMSS-BIENESTAR"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    # HTML con placeholders reemplazados
    html_content = f"""
    <html>
        <body>
            <div style="max-width:800px; margin:0 auto;">
                <img src="data:image/jpeg;base64,{image_top}" style="max-width:100%; height:auto;">
                <div style="max-width:500px; margin:auto; font-family:Montserrat; color:#021B23;">
                    <div style="height:4vh;"></div>
                    <div style="margin:10px auto; font-weight:800; padding:6px; text-align:center;">
                        <h2 style="font-weight:800; color:#235b4e; margin:0;">DATOS DE ACCESO</h2>
                    </div>
                    <div style="width:90%; margin:20px auto; text-align:justify;">
                        <p>Bienvenido al registro de IMSS-BIENESTAR. Sus datos de inicio de sesión son los siguientes:</p>
                        <p style="text-align:center; font-weight:700; font-size:1.1rem; margin:20px 0; border-bottom:3px solid #B38E5D;">
                            <br aria-hidden="true">CORREO: {to_email}
                            <br aria-hidden="true">CONTRASEÑA TEMPORAL: {temp_password}
                        </p>
                        <p>Este usuario fue generado desde el sistema de registro IMSS-BIENESTAR.</p>
                        <p>Puedes ingresar en el siguiente link:</p>
                        <p style="text-align:center; font-weight:700; font-size:1.1rem; margin:20px 0; border-bottom:3px solid #B38E5D;">
                            <a href="https://at-sai.imssbienestar.gob.mx/" style="color:#235b4e; text-decoration:none;">
                                https://at-sai.imssbienestar.gob.mx/
                            </a>
                        </p>
                        <p>Este Programa es público, ajeno a cualquier partido político. Queda prohibido el uso para fines distintos al desarrollo social.</p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """
    msg.set_content("Revisa este correo en un cliente que soporte HTML.")
    msg.add_alternative(html_content, subtype="html")

    # Conexión segura y envío
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)


def send_user_creation_email(to_email: str, temp_password: str) -> None:
    """
    Envía correo HTML notificando la creación de usuario.
    
    Params:
        to_email: correo del destinatario
    """
    #to_email = to_email.strip().lower()
    
    # Leer imagen base64
    with open("top_base64.txt") as f:
        image_top = f.read()

    # Crear mensaje
    msg = EmailMessage()
    msg["Subject"] = "USUARIO CREADO - IMSS-BIENESTAR"
    msg["From"] = EMAIL_FROM
    msg["To"] = to_email

    html_content = f"""
    <html>
        <body>
            <div style="max-width:800px; margin:0 auto;">
                <img src="data:image/jpeg;base64,{image_top}" style="max-width:100%; height:auto;">
                <div style="max-width:500px; margin:auto; font-family:Montserrat; color:#021B23;">
                    <div style="height:4vh;"></div>

                    <div style="margin:10px auto; font-weight:800; padding:6px; text-align:center;">
                        <h2 style="font-weight:800; color:#235b4e; margin:0;">
                            USUARIO CREADO EXITOSAMENTE
                        </h2>
                    </div>

                    <div style="width:90%; margin:20px auto; text-align:justify;">
                        <p>Bienvenido al sistema de registro IMSS-BIENESTAR.</p>

                        <p>Su cuenta ha sido creada correctamente:</p>

                        <p style="text-align:center; font-weight:700; font-size:1.1rem; margin:20px 0; border-bottom:3px solid #B38E5D;">
                            CORREO: {to_email}
                            CONTRASEÑA:{temp_password}
                        </p>

                        <p>
                            Ya puede acceder al sistema utilizando sus credenciales.
                        </p>

                        <p style="font-size:0.9rem;">
                            Este Programa es público, ajeno a cualquier partido político. 
                            Queda prohibido el uso para fines distintos al desarrollo social.
                        </p>
                    </div>
                </div>
            </div>
        </body>
    </html>
    """


    msg.set_content("Revisa este correo en un cliente que soporte HTML.")
    msg.add_alternative(html_content, subtype="html")

    # Conexión segura y envío
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
        server.login(EMAIL_USER, EMAIL_PASS)
        server.send_message(msg)

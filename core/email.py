# Configuración SendGrid
import os
EMAIL_HOST = os.getenv("EMAIL_HOST")
EMAIL_PORT = os.getenv("EMAIL_PORT",465)
EMAIL_USER = os.getenv("EMAIL_USER","apikey")  # siempre "apikey" con SendGrid
EMAIL_PASS = os.getenv("EMAIL_PASS")  # tu API Key real
EMAIL_FROM = os.getenv("EMAIL_FROM")
#EMAIL_TO = "magonzalez@bside.com.mx"  # tu correo de prueba
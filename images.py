import base64

# Imagen superior
with open("static/img/encabezadocorreo.jpg", "rb") as image_file:    
    encoded_top = base64.b64encode(image_file.read()).decode('utf-8')

# Imagen inferior
with open("static/img/piedepaginacorreo.jpg", "rb") as image_file:    
    encoded_bottom = base64.b64encode(image_file.read()).decode('utf-8')

# Guardarlas en archivos txt
with open("top_base64.txt", "w") as f:
    f.write(encoded_top)

with open("bottom_base64.txt", "w") as f:
    f.write(encoded_bottom)

print("Listo ✅ Imágenes convertidas.")

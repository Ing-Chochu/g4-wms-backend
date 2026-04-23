Hola niños
Ya dejé configurado el repositorio central, la estructura de carpetas y las librerías base para nuestro servidor (WMS Backend).

Para que todos podamos trabajar al mismo tiempo sin borrar el código del otro, vamos a usar una regla de oro: Nadie programa directamente en la rama main. Cada uno creará una "rama" para su tarea, y luego uniremos todo.

Aquí tienen el paso a paso exacto de lo que deben hacer. (Abran la terminal en VS Code y copien estos comandos).

🛠️ FASE 1: Descargar el proyecto (Solo se hace la primera vez)
1. Clonar el repositorio:
Vayan a la carpeta donde guardan sus proyectos de la universidad y ejecuten:

git clone https://github.com/Ing-Chochu/g4-wms-backend.git

2. Entrar a la carpeta del proyecto:

cd g4-wms-backend

3. Crear el Entorno Virtual (Nuestra burbuja de trabajo):

python -m venv venv

4. Activar el Entorno:

.\venv\Scripts\activate

(Nota: Si les sale un error rojo en Windows, primero ejecuten "Set-ExecutionPolicy Unrestricted -Scope CurrentUser" y luego intenten de nuevo).

(Deben ver un (venv) verde en su terminal. Si no lo ven, no avancen).

5. Instalar todas las librerías mágicamente:

pip install -r requirements.txt

👨‍💻 FASE 2: Empezar a trabajar en tu tarea (La Regla de Oro)
Antes de escribir una sola línea de código, debes crear tu propia rama para no dañar el proyecto principal.

1. Actualiza tu compu (por si alguien subió algo nuevo):

git pull origin main

2. Crea tu rama y muévete a ella:
(Cambia "mi-tarea" por lo que vayas a hacer, ej: feat/base-de-datos o feat/api-login).

git checkout -b feat/mi-tarea

💾 FASE 3: Guardar y subir tus cambios (El Pan de cada día)
Cuando termines una función o al final del día de trabajo, debes guardar tu progreso en la nube. Ejecuta estos 3 comandos en orden:

1. Prepara todos los archivos que cambiaste:

git add .

2. Toma la "foto" y ponle un mensaje de qué hiciste:

git commit -m "feat: agregue las tablas de usuarios y roles"

3. Sube tu rama a GitHub:
(La primera vez que subas tu rama, usa este comando completo. Las siguientes veces solo bastará con poner git push).

git push -u origin feat/mi-tarea

---

¡Y listo! Cuando su código esté subido, me avisan y yo me encargo de hacer el "Merge" (unir su código con el main de todos). ¡A darle! 💻⚙️
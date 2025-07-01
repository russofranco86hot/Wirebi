$env:PGPASSWORD="Chaca1986!"; psql -h localhost -U fr94901 -d forecaist -f ventas-pronostico-app/src/db/forecaist_schema.sql
$env:DATABASE_URL="postgresql://fr94901:Chaca1986!@localhost:5432/forecaist"
python ventas-pronostico-app/src/db/migrate_data.py
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
cd .\backend
Remove-Item -Recurse -Force .venv_backend
pip install -r requirements.txt
python -m venv .venv_backend


cd ..
cd ./frontend
Remove-Item -Recurse -Force node_modules
Remove-Item package-lock.json
npm install 

echo resta levantar los ambientes Backend I frond End en 2 lugares separados:
pause

cd .\backend
.venv_backend\Scripts\activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

cd ./frontend
npm  run dev

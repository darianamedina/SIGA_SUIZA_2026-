#!/bin/sh
set -e

echo "=========================================="
echo "🚀 Iniciando SIGA Backend (Railway)"
echo "=========================================="

PORT="${PORT:-8000}"
export PORT
echo "📡 Puerto principal: $PORT"

cleanup() {
    echo "🛑 Deteniendo servicios internos..."
    kill 0 2>/dev/null || true
    exit 0
}
trap cleanup EXIT INT TERM

if [ -n "$DATABASE_URL" ]; then
    echo "📦 DATABASE_URL detectada de Railway."
    # Normalizar scheme para Alembic (psycopg3) + SSL para hosts remotos
    _db_url="$DATABASE_URL"
    case "$_db_url" in
        postgres://*)    _db_url="postgresql+psycopg://${_db_url#postgres://}" ;;
        postgresql://*)  _db_url="postgresql+psycopg://${_db_url#postgresql://}" ;;
        postgresql+asyncpg://*) _db_url="postgresql+psycopg://${_db_url#postgresql+asyncpg://}" ;;
    esac
    # Añadir sslmode=require si es host remoto y no trae sslmode
    _host=$(printf '%s' "$_db_url" | sed -E 's#^[^:]+://[^@]*@##; s#[:/].*##')
    case "$_host" in
        localhost|127.0.0.1|::1|host.docker.internal|postgres) ;;
        *)
            if ! printf '%s' "$_db_url" | grep -q 'sslmode='; then
                case "$_db_url" in
                    *\?*) _db_url="${_db_url}&sslmode=require" ;;
                    *)    _db_url="${_db_url}?sslmode=require" ;;
                esac
            fi
            ;;
    esac
    export DB_URL="$_db_url"
    echo "🔗 DB_URL normalizada para migraciones."
fi

if [ "$SKIP_MIGRATIONS" != "true" ]; then
    echo "🔄 Ejecutando migraciones de base de datos..."
    alembic upgrade head || echo "⚠️ Alembic upgrade head falló o fue omitido — continuando..."
fi

export SIGA_MODULE_USUARIOS_URL="http://127.0.0.1:8001"
export SIGA_MODULE_PLANES_ESTUDIO_URL="http://127.0.0.1:8002"
export SIGA_MODULE_PROGRAMAS_ESTUDIO_URL="http://127.0.0.1:8005"
export SIGA_MODULE_GESTION_ACADEMICA_URL="http://127.0.0.1:8006"
export SIGA_MODULE_AUDITORIA_URL="http://127.0.0.1:8007"
export SIGA_MODULE_EVALUACION_URL="http://127.0.0.1:8008"
export SIGA_MODULE_ADMISION_URL="http://127.0.0.1:8009"

echo "⚙️ Levantando 7 microservicios internos..."
python -m uvicorn main:app --host 127.0.0.1 --port 8001 --app-dir modules/mod-usuarios &
python -m uvicorn main:app --host 127.0.0.1 --port 8002 --app-dir modules/mod-planes-estudio &
python -m uvicorn main:app --host 127.0.0.1 --port 8005 --app-dir modules/mod-programas-estudio &
python -m uvicorn main:app --host 127.0.0.1 --port 8006 --app-dir modules/mod-gestion-academica &
python -m uvicorn main:app --host 127.0.0.1 --port 8007 --app-dir modules/mod-auditoria &
python -m uvicorn main:app --host 127.0.0.1 --port 8008 --app-dir modules/mod-evaluacion &
python -m uvicorn main:app --host 127.0.0.1 --port 8009 --app-dir modules/mod-admision &

sleep 2

echo "🌐 Iniciando Core Gateway en 0.0.0.0:$PORT..."
exec python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT"

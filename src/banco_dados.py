
import os
import psycopg
from pathlib import Path
from dotenv import load_dotenv


# Carrega as variáveis do arquivo .env na raiz do projeto
RAIZ_PROJETO = Path(__file__).resolve().parent.parent
load_dotenv(RAIZ_PROJETO / ".env")


def conectar():
    """
    Cria e retorna uma conexão com o banco PostgreSQL.
    """

    try:
        conexao = psycopg.connect(
            dbname=os.getenv("POSTGRES_DB"),
            user=os.getenv("POSTGRES_USER"),
            password=os.getenv("POSTGRES_PASSWORD"),
            host="localhost",
            port=os.getenv("POSTGRES_PORT", "5432"),
        )

        return conexao

    except psycopg.Error as erro:
        print(f"Erro ao conectar ao PostgreSQL: {erro}")
        return None


if __name__ == "__main__":
    conexao = conectar()

    if conexao:
        print("Conexão com PostgreSQL realizada com sucesso!")

        with conexao.cursor() as cursor:
            cursor.execute("SELECT current_database(), current_user;")
            resultado = cursor.fetchone()
            print(f"Banco: {resultado[0]}")
            print(f"Usuário: {resultado[1]}")

        conexao.close()

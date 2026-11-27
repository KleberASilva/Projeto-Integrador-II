
import json
import logging
import time
from queue import Queue, Empty
from threading import Thread, Event

from banco_dados import conectar


logger = logging.getLogger(__name__)


def _json_serializar(valor):
    """Converte valores NumPy e outros tipos para JSON."""
    if hasattr(valor, "tolist"):
        return valor.tolist()

    if hasattr(valor, "item"):
        return valor.item()

    if hasattr(valor, "isoformat"):
        return valor.isoformat()

    raise TypeError(f"Tipo não serializável: {type(valor).__name__}")


class FilaBanco:
    """Grava dados no PostgreSQL em uma thread separada."""

    def __init__(self):
        self.fila = Queue()
        self.encerrar = Event()

        self.thread = Thread(
            target=self._processar,
            daemon=True,
            name="FilaPostgreSQL",
        )
        self.thread.start()

    def enviar(self, comando, dados):
        """Adiciona uma operação à fila."""
        if self.encerrar.is_set():
            raise RuntimeError("A fila já foi encerrada.")

        self.fila.put((comando, dados))

    def _executar(self, conexao, comando, dados):
        with conexao.cursor() as cursor:

            if comando == "sessao":
                cursor.execute(
                    """
                    INSERT INTO sessoes (session_id, inicio_em)
                    VALUES (%s, %s)
                    ON CONFLICT (session_id) DO NOTHING
                    """,
                    (dados["session_id"], dados["inicio_em"]),
                )

            elif comando == "telemetria":
                cursor.execute(
                    """
                    INSERT INTO telemetria (
                        session_id, timestamp, frame, estado,
                        escore_total, escore_olhos, escore_boca,
                        escore_cabeca, perclos, dados
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (session_id, timestamp, frame)
                    DO NOTHING
                    """,
                    (
                        dados["session_id"],
                        dados["timestamp"],
                        dados.get("frame"),
                        dados.get("estado"),
                        dados.get("escore_total"),
                        dados.get("escore_olhos"),
                        dados.get("escore_boca"),
                        dados.get("escore_cabeca"),
                        dados.get("perclos"),
                        json.dumps(
                            dados,
                            ensure_ascii=False,
                            default=_json_serializar,
                        ),
                    ),
                )

            elif comando == "evento":
                cursor.execute(
                    """
                    INSERT INTO eventos (
                        event_id, session_id, origem, tipo,
                        descricao, inicio_em, fim_em,
                        duracao_segundos, confirmado, motivo, dados
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (event_id) DO NOTHING
                    """,
                    (
                        dados["event_id"],
                        dados["session_id"],
                        dados.get("origem"),
                        dados.get("tipo"),
                        dados.get("descricao"),
                        dados.get("inicio_em"),
                        dados.get("fim_em"),
                        dados.get("duracao_segundos"),
                        dados.get("confirmado"),
                        dados.get("motivo"),
                        json.dumps(
                            dados,
                            ensure_ascii=False,
                            default=_json_serializar,
                        ),
                    ),
                )

            elif comando == "encerrar_sessao":
                cursor.execute(
                    """
                    UPDATE sessoes
                    SET fim_em = %s
                    WHERE session_id = %s
                    """,
                    (dados["fim_em"], dados["session_id"]),
                )

            else:
                raise ValueError(f"Comando desconhecido: {comando}")

        conexao.commit()

    def _processar(self):
        conexao = None

        while not self.encerrar.is_set() or not self.fila.empty():
            try:
                comando, dados = self.fila.get(timeout=0.5)
            except Empty:
                continue

            try:
                while True:
                    try:
                        if conexao is None or conexao.closed:
                            conexao = conectar()

                        if conexao is None:
                            raise ConnectionError(
                                "Não foi possível conectar ao PostgreSQL."
                            )

                        self._executar(conexao, comando, dados)
                        break

                    except Exception:
                        logger.exception(
                            "Falha ao gravar no PostgreSQL. "
                            "O registro será tentado novamente."
                        )

                        if conexao is not None:
                            try:
                                conexao.rollback()
                                conexao.close()
                            except Exception:
                                pass

                        conexao = None
                        time.sleep(2)

            finally:
                self.fila.task_done()

        if conexao is not None:
            conexao.close()

    def fechar(self):
        """Aguarda os registros pendentes e encerra a thread."""
        self.fila.join()
        self.encerrar.set()
        self.thread.join()

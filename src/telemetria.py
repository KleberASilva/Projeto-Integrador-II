"""Persistência de medições e eventos de uma sessão de monitoramento.

As durações são calculadas com ``time.monotonic``. Os timestamps ISO 8601
servem para correlacionar a sessão com anotações externas e são derivados do
mesmo instante monotônico, evitando que ajustes do relógio do sistema alterem
as durações.
"""

import csv
import json
import os
import time
import uuid
from datetime import datetime
from threading import RLock

import cv2
import numpy as np

from fila_banco import FilaBanco

class Telemetria:
    """Escreve medições por frame e eventos estruturados sem sobrescrever sessões."""

    def __init__(self, pasta=None, session_id=None, agora=None):
        if pasta is None:
            pasta = os.path.join(
                os.path.dirname(__file__),
                "data",
                "telemetry",
            )

        self.session_id = session_id or self._novo_session_id()
        self.pasta_sessao = os.path.join(pasta, self.session_id)
        self.pasta_capturas = os.path.join(self.pasta_sessao, "capturas")
        os.makedirs(self.pasta_capturas, exist_ok=True)
        self.inicio_monotonic = time.monotonic() if agora is None else agora
        self.inicio_datetime = datetime.now().astimezone()

        self.caminho = os.path.join(
            self.pasta_sessao, "telemetria.csv"
        )
        self.caminho_eventos = os.path.join(
            self.pasta_sessao, "eventos.csv"
        )

        self.colunas = [
            "session_id", "frame", "timestamp", "tempo_execucao", "estado",
            "ear", "ear_direito", "ear_esquerdo", "ear_referencia",
            "ear_referencia_direito", "ear_referencia_esquerdo",
            "limiar_ear", "limiar_ear_direito", "limiar_ear_esquerdo",
            "mar", "mar_referencia", "limiar_mar",
            "pitch", "yaw", "roll", "limiar_pitch", "limiar_yaw",
            "limiar_roll",
            "pitch_original", "yaw_original", "roll_original",
            "pitch_filtrado", "yaw_filtrado", "roll_filtrado",
            "pitch_relativo", "yaw_relativo", "roll_relativo",
            "estado_olhos", "olhos_fechados", "tempo_olho_fechado",
            "perclos", "perclos_valido",
            "cobertura_perclos", "tempo_observado_perclos",
            "frequencia_fechamentos", "frequencia_fechamentos_prolongados",
            "estado_boca", "boca_aberta", "tempo_abertura", "bocejo",
            "frequencia_bocejos",
            "estado_cabeca", "movimento_cabeca", "tempo_movimento",
            "frequencia_movimentos",
            "calibracao_olhos", "calibracao_boca", "calibracao_cabeca",
            "evento_olhos", "evento_olhos_duracao", "evento_olhos_json",
            "evento_boca", "evento_boca_duracao", "evento_boca_json",
            "evento_cabeca", "evento_cabeca_duracao", "evento_cabeca_json",
            "escore_olhos", "escore_boca", "escore_cabeca", "peso_olhos",
            "peso_boca", "peso_cabeca", "limiar_fadiga_individual",
            "persistencia_fadiga_individual", "escore_total",
            "categorias_significativas", "motivo_classificacao",
            "motivo_alerta", "fadiga_individual", "fadiga_combinada",
            "modo_fadiga", "fatores_fadiga",
            "nivel_olhos", "nivel_boca", "nivel_cabeca",
            "sinal_atencao", "sinal_fadiga", "sinal_fadiga_individual",
            "sinal_fadiga_combinada", "fadiga_persistente",
            "persistencia_fadiga_decorrida", "persistencia_fadiga_necessaria",
            "persistencia_transicao_decorrida",
            "persistencia_transicao_necessaria", "candidato_transicao",
            "captura_arquivo", "captura_timestamp", "captura_tipo",
            "captura_motivo",
        ]

        self.colunas_eventos = [
            "session_id", "event_id", "origem", "tipo", "descricao",
            "inicio_timestamp", "fim_timestamp", "inicio_monotonic",
            "fim_monotonic", "duracao", "confirmado", "motivo",
            "frame_inicio", "frame_fim",
        ]

        self.arquivo = open(
            self.caminho, "w", newline="", encoding="utf-8"
        )
        self.escritor = csv.DictWriter(
            self.arquivo, fieldnames=self.colunas, extrasaction="ignore"
        )
        self.escritor.writeheader()

        self.arquivo_eventos = open(
            self.caminho_eventos, "w", newline="", encoding="utf-8"
        )
        self.escritor_eventos = csv.DictWriter(
            self.arquivo_eventos,
            fieldnames=self.colunas_eventos,
            extrasaction="ignore",
        )
        self.escritor_eventos.writeheader()
        self.arquivo.flush()
        self.arquivo_eventos.flush()

        self._eventos_registrados = set()
        self._lock = RLock()

        self.fila_banco = FilaBanco()

        self.fila_banco.enviar(
            "sessao",
            {
                "session_id": self.session_id,
                "inicio_em": self.inicio_datetime.isoformat(),
            },
        )

    @staticmethod
    def _novo_session_id():
        instante = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S_%f")
        return f"{instante}_{uuid.uuid4().hex[:8]}"

    def _iso_timestamp(self, monotonic):
        delta = monotonic - self.inicio_monotonic
        instante = self.inicio_datetime.timestamp() + delta
        return datetime.fromtimestamp(
            instante, tz=self.inicio_datetime.tzinfo
        ).isoformat(timespec="milliseconds")

    @staticmethod
    def _evento_id(evento, origem):
        inicio = evento.get("inicio")
        tipo = evento.get("tipo", "EVENTO")
        return f"{origem}:{tipo}:{inicio}"

    def _registrar_evento(self, evento, origem, frame=None, agora=None):
        with self._lock:
            return self._registrar_evento_protegido(
                evento, origem, frame, agora
            )

    def _registrar_evento_protegido(
        self, evento, origem, frame=None, agora=None
    ):
        if not evento:
            return False

        inicio = evento.get("inicio", agora)
        fim = evento.get("fim", agora if agora is not None else inicio)
        if inicio is None:
            inicio = self.inicio_monotonic
        if fim is None:
            fim = inicio

        event_id = evento.get("event_id") or self._evento_id(evento, origem)
        if event_id in self._eventos_registrados:
            return False

        confirmado = evento.get("confirmado")
        if confirmado is None:
            confirmado = evento.get("prolongado", False)

        linha = {
            "session_id": self.session_id,
            "event_id": event_id,
            "origem": origem,
            "tipo": evento.get("tipo", "EVENTO"),
            "descricao": evento.get("descricao"),
            "inicio_timestamp": self._iso_timestamp(inicio),
            "fim_timestamp": self._iso_timestamp(fim),
            "inicio_monotonic": inicio,
            "fim_monotonic": fim,
            "duracao": evento.get("duracao", max(0.0, fim - inicio)),
            "confirmado": confirmado,
            "motivo": evento.get("motivo"),
            "frame_inicio": evento.get("frame_inicio", frame),
            "frame_fim": evento.get("frame_fim", frame),
        }
        self.escritor_eventos.writerow(linha)
        self.arquivo_eventos.flush()
        self._eventos_registrados.add(event_id)

        dados_evento = {
            "event_id": event_id,
            "session_id": self.session_id,
            "origem": origem,
            "tipo": linha["tipo"],
            "descricao": linha["descricao"],
            "inicio_em": linha["inicio_timestamp"],
            "fim_em": linha["fim_timestamp"],
            "duracao_segundos": linha["duracao"],
            "confirmado": linha["confirmado"],
            "motivo": linha["motivo"],
            "frame_inicio": linha["frame_inicio"],
            "frame_fim": linha["frame_fim"],
            "evento_original": evento,
        }

        dados_evento = json.loads(
            json.dumps(
                dados_evento,
                ensure_ascii=False,
                default=lambda valor: (
                    valor.item() if hasattr(valor, "item")
                    else valor.tolist() if hasattr(valor, "tolist")
                    else valor.isoformat() if hasattr(valor, "isoformat")
                    else str(valor)
                ),
            )
        )

        self.fila_banco.enviar("evento", dados_evento)

        return True

    def registrar_evento(self, evento, origem="sistema", frame=None, agora=None):
        """Registra um evento fechado ou uma marcação instantânea."""
        return self._registrar_evento(evento, origem, frame, agora)

    def registrar_marcacao(self, tipo, descricao, frame=None, agora=None):
        """Registra uma marcação manual sem alterar a classificação automática."""
        momento = time.monotonic() if agora is None else agora
        evento = {
            "tipo": tipo,
            "descricao": descricao,
            "inicio": momento,
            "fim": momento,
            "duracao": 0.0,
            "confirmado": True,
        }
        return self._registrar_evento(evento, "manual", frame, momento)

    @staticmethod
    def _texto(valor):
        if valor is None:
            return "-"
        if isinstance(valor, float):
            return f"{valor:.3f}"
        return str(valor)

    def _salvar_captura(self, imagem, info, frame, momento, captura_tipo="automatica"):
        timestamp = self._iso_timestamp(momento)
        nome_timestamp = timestamp.replace("-", "").replace(":", "").replace("+", "_").replace(".", "")
        nome = f"{captura_tipo}_frame_{int(frame or 0):06d}_{nome_timestamp}.png"
        caminho = os.path.join(self.pasta_capturas, nome)

        linhas = [
            f"sessao: {self.session_id}",
            f"timestamp: {timestamp}",
            f"frame: {frame}",
            f"estado: {info.get('estado')}",
            f"olhos: {info.get('estado_olhos')} EAR D/E {self._texto(info.get('ear_direito'))}/{self._texto(info.get('ear_esquerdo'))}",
            f"boca: {info.get('estado_boca')} MAR {self._texto(info.get('mar'))} aberta={info.get('boca_aberta')}",
            f"cabeca: {info.get('estado_cabeca')} yaw/pitch/roll {self._texto(info.get('yaw'))}/{self._texto(info.get('pitch'))}/{self._texto(info.get('roll'))}",
            f"escores O/B/C: {self._texto(info.get('escore_olhos'))}/{self._texto(info.get('escore_boca'))}/{self._texto(info.get('escore_cabeca'))}",
            f"total: {self._texto(info.get('escore_total'))} categorias: {info.get('categorias_significativas')}",
            f"pesos O/B/C: {self._texto(info.get('peso_olhos'))}/{self._texto(info.get('peso_boca'))}/{self._texto(info.get('peso_cabeca'))}",
            f"motivo: {info.get('motivo_classificacao') or '-'}",
            f"alerta: {info.get('motivo_alerta') or '-'}",
            f"modo fadiga: {info.get('modo_fadiga') or '-'} fatores={info.get('fatores_fadiga') or '-'}",
        ]
        altura, largura = imagem.shape[:2]
        painel_largura = 620
        painel = cv2.rectangle(
            np.zeros((max(altura, 420), painel_largura, 3), dtype=np.uint8),
            (0, 0), (painel_largura, max(altura, 420)), (12, 18, 30), -1,
        )
        for indice, linha in enumerate(linhas):
            cv2.putText(
                painel, linha[:95], (18, 30 + indice * 30),
                cv2.FONT_HERSHEY_SIMPLEX, 0.55, (225, 235, 248), 1,
                cv2.LINE_AA,
            )
        imagem_final = cv2.hconcat([imagem, painel[:altura]])
        if not cv2.imwrite(caminho, imagem_final):
            raise OSError(f"Nao foi possivel salvar captura: {caminho}")
        caminho_relativo = os.path.relpath(caminho, self.pasta_sessao)
        return caminho_relativo.replace(os.sep, "/"), timestamp

    def registrar(
        self,
        info,
        frame=None,
        agora=None,
        imagem=None,
        captura_tipo=None,
        captura_motivo=None,
    ):
        """Registra uma linha e, opcionalmente, uma captura sincronizada."""
        with self._lock:
            momento = time.monotonic() if agora is None else agora
            captura_arquivo = None
            captura_timestamp = None
            if imagem is not None:
                captura_arquivo, captura_timestamp = self._salvar_captura(
                    imagem,
                    info or {},
                    frame,
                    momento,
                    captura_tipo or "automatica",
                )
            linha = {coluna: None for coluna in self.colunas}
            linha.update(info or {})
            if isinstance(linha.get("fatores_fadiga"), (list, tuple)):
                linha["fatores_fadiga"] = json.dumps(
                    linha["fatores_fadiga"], ensure_ascii=False
                )
            linha.update(
                {
                    "session_id": self.session_id,
                    "frame": frame,
                    "timestamp": self._iso_timestamp(momento),
                    "tempo_execucao": round(
                        momento - self.inicio_monotonic, 3
                    ),
                    "captura_arquivo": captura_arquivo,
                    "captura_timestamp": captura_timestamp,
                    "captura_tipo": captura_tipo,
                    "captura_motivo": captura_motivo,
                }
            )

            for coluna in ("evento_olhos", "evento_boca", "evento_cabeca"):
                evento = info.get(coluna) if info else None
                linha[coluna] = evento.get("tipo") if evento else None
                linha[coluna + "_duracao"] = (
                    evento.get("duracao") if evento else None
                )
                linha[coluna + "_json"] = (
                    json.dumps(evento, ensure_ascii=False, sort_keys=True)
                    if evento else None
                )
                origem = coluna.removeprefix("evento_")
                self._registrar_evento_protegido(
                    evento, origem, frame, momento
                )

            self.escritor.writerow(linha)
            self.arquivo.flush()

            dados_banco = json.loads(
                json.dumps(
                    linha,
                    ensure_ascii=False,
                    default=lambda valor: (
                        valor.item() if hasattr(valor, "item")
                        else valor.tolist() if hasattr(valor, "tolist")
                        else valor.isoformat() if hasattr(valor, "isoformat")
                        else str(valor)
                    ),
                )
            )

            self.fila_banco.enviar("telemetria", dados_banco)

            return captura_arquivo

    def fechar(self):
        """Fecha os CSVs e encerra a sessão no PostgreSQL."""
        with self._lock:
            if not self.arquivo.closed:
                self.arquivo.close()

            if not self.arquivo_eventos.closed:
                self.arquivo_eventos.close()

            if getattr(self, "fila_banco", None) is not None:
                self.fila_banco.enviar(
                    "encerrar_sessao",
                    {
                        "session_id": self.session_id,
                        "fim_em": datetime.now().astimezone().isoformat(),
                    },
                )

                self.fila_banco.fechar()
                self.fila_banco = None

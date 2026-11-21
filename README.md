# Detector de Fadiga Automotivo Baseado em Visão Computacional

Protótipo desenvolvido para a disciplina de Projeto Integrador II, do curso de Engenharia de Computação da Universidade Federal de Santa Maria (UFSM).

O sistema utiliza uma câmera para acompanhar indicadores visuais associados à sonolência: olhos, boca e orientação da cabeça. O processamento é local e não utiliza celular, GPS, acelerômetro ou outros sensores externos.

## Equipe

- **Kléberson do Amaral da Silva** — [GitHub](https://github.com/KleberASilva/)
- **Pedro Lucca Menezes Vitalis** — [GitHub](https://github.com/pedrovitalis)
- **Vitor Carvalho de Araujo** — [GitHub](https://github.com/arauvitor)
- **Yuri Silveira Pereira** — [GitHub](https://github.com/slaycker13)

**Orientador:** Prof. Lucas Feksa Ramos

## Estado atual

O projeto está em estágio de **protótipo funcional em validação experimental**.

Já estão implementados:

- captura de vídeo e detecção facial com MediaPipe Tasks;
- calibração dos indicadores de olhos, boca e cabeça;
- EAR para acompanhamento da abertura dos olhos e fechamentos prolongados;
- MAR para acompanhamento da abertura da boca e bocejos;
- estimativa de pitch, yaw e roll da cabeça;
- filtragem temporal e persistência dos eventos;
- classificação em `ATENTO`, `ATENCAO`, `FADIGA`, `SEM_ROSTO` e `CALIBRANDO`;
- distinção diagnóstica entre `FADIGA_INDIVIDUAL` e `FADIGA_COMBINADA`;
- indicação dos fatores que contribuíram para a decisão;
- interface PySide6 com indicadores, eventos, alertas sonoros e recalibração;
- coleta de telemetria controlada por botão;
- capturas automáticas durante sinais de alerta;
- capturas manuais independentes da coleta;
- marcações manuais para comparação posterior;
- testes automatizados dos detectores, classificador e telemetria.

Os parâmetros ainda são experimentais. O sistema não é um dispositivo clínico e não deve ser utilizado como único mecanismo de segurança durante a condução.

## Indicadores e classificação

### Olhos

O EAR é calculado para os dois olhos e a decisão de fechamento utiliza o EAR médio. A calibração inicial registra a referência da abertura dos olhos. Fechamentos prolongados e PERCLOS podem contribuir para a classificação quando os dados possuem cobertura válida. O PERCLOS está desabilitado por padrão até que a cobertura da janela seja validada experimentalmente.

### Boca

O MAR é comparado com uma referência calibrada. A abertura da boca é acompanhada enquanto permanece aberta; um bocejo isolado não confirma fadiga individual. A quantidade mínima atual é de dois bocejos dentro da janela de análise para que eventos repetidos contribuam para a classificação.

### Cabeça

O head pose estima pitch, yaw e roll usando landmarks faciais e `solvePnP`. Os limiares atuais do detector são:

- pitch: `15°`;
- yaw: `50°`;
- duração mínima de movimento: `1,5 s`.

Quando um movimento de cabeça já foi confirmado e o rosto desaparece brevemente, a evidência pode ser preservada temporariamente. Isso não substitui a detecção facial e ainda precisa ser validado com dados reais.

### Classificador geral

O classificador trabalha com janelas temporais, escores e pesos:

- olhos: `0,45`;
- boca: `0,35`;
- cabeça: `0,20`.

Um indicador acima do limiar pode gerar `ATENCAO`. Uma evidência individual persistente pode gerar `FADIGA_INDIVIDUAL`. Evidências significativas de múltiplas categorias podem gerar `FADIGA_COMBINADA`. Os motivos, fatores, escores, pesos, limiares e persistências são registrados na telemetria.

Os valores atuais são parâmetros de protótipo e devem ser ajustados após a coleta anotada.

## Interface e atalhos

Recursos disponíveis:

- visualização da câmera com a imagem completa e preservação da proporção;
- indicadores EAR, MAR e head pose;
- cartão de estado geral e motivo da classificação;
- distinção visual entre indicador em atenção e indicador em fadiga individual;
- eventos e alertas sonoros;
- botão **Iniciar coleta** / **Parar coleta**;
- botão **Capturar (C)**;
- botão **Recalibrar**;
- botão **Testar som**.

| Tecla | Função |
|---|---|
| `F9` | Ativar ou desativar o modo de teste |
| `1` a `5` | Simular estados no modo de teste |
| `R` | Recalibrar os detectores |
| `C` | Capturar a tela manualmente |
| `F11` | Alternar tela cheia |
| `Esc` | Sair da tela cheia |
| `F1` | Marcar início do teste |
| `F2` / `F3` | Marcar rotação para esquerda / direita |
| `F4` / `F5` | Marcar inclinação para cima / baixo |
| `F6` | Marcar piscadas |
| `F7` | Marcar fechamento prolongado |
| `F8` | Marcar bocejo |
| `End` | Marcar fim do teste |

As marcações manuais só são gravadas quando uma coleta está ativa. Elas não alteram a classificação automática.

## Estrutura do repositório

```text
Projeto-Integrador-II/
├── src/
│   ├── main.py                  # ponto de entrada
│   ├── interface.py             # interface, atalhos e visualização
│   ├── monitoramento.py         # câmera, MediaPipe e integração dos detectores
│   ├── eye_detection.py         # EAR, piscadas, fechamentos e PERCLOS
│   ├── boca.py                  # MAR e bocejos
│   ├── head_pose.py             # orientação e eventos da cabeça
│   ├── classificador_fadiga.py  # escores, persistência e estados gerais
│   ├── telemetria.py            # CSVs, eventos e capturas sincronizadas
│   ├── models/
│   │   └── face_landmarker.task
│   ├── sons/
│   │   ├── atencao.wav
│   │   └── fadiga.wav
│   └── data/telemetry/           # dados gerados, ignorados pelo Git
├── tests/                        # testes automatizados
├── .gitignore
├── LICENSE
└── README.md
```

## Instalação e execução

### Criar o ambiente

No Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### Instalar dependências

```powershell
python -m pip install opencv-python mediapipe numpy PySide6
```

### Executar

```powershell
python src/main.py
```

É necessário possuir uma webcam funcional e o arquivo `src/models/face_landmarker.task`. O sistema foi estruturado para Windows por utilizar `winsound` nos alertas sonoros.

## Coleta de dados

O monitoramento pode permanecer ativo sem salvar dados. A gravação começa somente após clicar em **Iniciar coleta**. Ao clicar em **Parar coleta** ou fechar o programa, a sessão é encerrada e os arquivos são fechados.

Cada coleta cria uma pasta própria:

```text
src/data/telemetry/<session_id>/
├── telemetria.csv
├── eventos.csv
└── capturas/
```

### `telemetria.csv`

Possui uma linha por frame, incluindo timestamp, frame, estado, EAR, MAR, pitch, yaw, roll, referências, limiares, estados individuais, durações, PERCLOS, eventos, escores, pesos, modo de fadiga, fatores contribuintes e critérios de persistência.

### `eventos.csv`

Registra eventos automáticos e marcações manuais com origem, tipo, descrição, timestamps, duração, confirmação, motivo e frames associados.

### Capturas

Capturas automáticas são salvas durante uma coleta quando ocorre uma entrada em condição relevante, como fechamento prolongado dos olhos, abertura prolongada da boca, movimento confirmado da cabeça, `ATENCAO` ou `FADIGA`.

Capturas manuais podem ser feitas com `C` ou pelo botão **Capturar (C)**, mesmo sem coleta ativa. Elas são salvas em:

```text
src/data/telemetry/manual_capturas/
```

Arquivos de telemetria, imagens de rosto e capturas locais não devem ser adicionados ao Git.

## Testes automatizados

Executar todos os testes:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Os testes cobrem cálculo geométrico e temporal, calibração sintética, limiares de olhos, eventos de boca, head pose, perda de rosto, transições do classificador, coleta controlada e persistência dos CSVs. Eles não substituem testes reais com webcam.

## Próximos passos

1. **Coletar sessões controladas:** testar diferentes pessoas, iluminação, distância, posições e câmeras.
2. **Anotar a referência real:** registrar manualmente olhos, bocejos, cabeça, atenção e fadiga.
3. **Criar o analisador dos CSVs:** gerar matrizes de confusão e métricas por detector e para o classificador geral.
4. **Ajustar os parâmetros:** usar os resultados para revisar EAR, MAR, head pose, persistências e quantidade mínima de eventos.
5. **Documentar a avaliação:** registrar protocolo, resultados, falsos positivos, falsos negativos e limitações.
6. **Avaliar Grafana:** integrar somente depois de estabilizar o formato dos dados e as métricas.

## Limitações

- Os limiares não são clínicos nem cientificamente validados.
- A qualidade da câmera, iluminação e posição do rosto afetam os landmarks.
- Inclinações extremas podem causar perda temporária do rosto.
- Os testes automatizados não medem desempenho em condições reais.
- O resultado do próprio detector não pode ser usado como verdade de referência.
- O protótipo não deve ser utilizado como único mecanismo de segurança ao dirigir.

## Licença

Consulte o arquivo [LICENSE](LICENSE) para informações sobre os termos de utilização e distribuição do projeto.

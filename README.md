# Detector de Fadiga Automotivo Baseado em Visão Computacional

Repositório destinado ao desenvolvimento do projeto da disciplina de **Projeto Integrador II**, do curso de **Engenharia de Computação da Universidade Federal de Santa Maria (UFSM)**.

O projeto consiste no desenvolvimento de um protótipo de monitoramento de sinais comportamentais associados à fadiga ao volante, utilizando visão computacional para análise facial em tempo real.

---

## Equipe

- **Kléberson do Amaral da Silva** — [GitHub](https://github.com/KleberASilva/)
- **Pedro Lucca Menezes Vitalis** — [GitHub](https://github.com/pedrovitalis)
- **Vitor Carvalho de Araujo** — [GitHub](https://github.com/arauvitor)
- **Yuri Silveira Pereira** — [GitHub](https://github.com/slaycker13)

**Orientador:** Prof. Lucas Feksa Ramos

---

## Sobre o Projeto

A fadiga ao volante representa um importante fator de risco para a segurança no trânsito. Alterações no comportamento do motorista, como fechamento prolongado dos olhos, bocejos frequentes e mudanças na orientação da cabeça, podem indicar condições de sonolência e redução do estado de alerta.

O projeto propõe o desenvolvimento de um sistema capaz de monitorar esses sinais por meio de uma câmera, utilizando técnicas de visão computacional e processamento de landmarks faciais.

O processamento é realizado localmente, sem necessidade de transmissão das imagens para servidores externos.

### Indicadores Monitorados

O sistema utiliza três indicadores principais:

- **EAR (Eye Aspect Ratio):** relação geométrica utilizada para estimar a abertura dos olhos e identificar períodos de fechamento prolongado.
- **MAR (Mouth Aspect Ratio):** relação geométrica utilizada para identificar abertura prolongada da boca e detectar possíveis bocejos.
- **Head Pose Estimation:** estimativa da orientação da cabeça nos eixos de rotação, permitindo identificar inclinações e movimentos potencialmente associados à desatenção.

Os indicadores são utilizados em conjunto com mecanismos de calibração e filtragem temporal, buscando adaptar as referências às características individuais e reduzir detecções ocasionadas por movimentos momentâneos.

### Interface e Monitoramento

O sistema conta com uma interface gráfica desenvolvida em PySide6, que permite acompanhar o monitoramento em tempo real.

Entre os recursos disponíveis estão:

- Exibição da imagem capturada pela câmera.
- Apresentação dos indicadores EAR, MAR e orientação da cabeça.
- Identificação de estados de atenção e possíveis sinais de fadiga.
- Alertas sonoros associados aos eventos detectados.
- Registro de eventos durante a execução.
- Recalibração dos indicadores.
- Modo de teste para simulação dos estados da interface.

---

## Tecnologias Utilizadas

### Linguagem e Processamento

- **Python:** linguagem principal do projeto.
- **OpenCV:** captura e processamento de imagens.
- **MediaPipe Tasks:** identificação de landmarks faciais.
- **NumPy:** operações matemáticas e processamento de dados.

### Interface e Alertas

- **PySide6:** desenvolvimento da interface gráfica.
- **Winsound:** reprodução de alertas sonoros no Windows.

### Desenvolvimento e Controle de Versão

- **Git:** controle de versão.
- **GitHub:** hospedagem do repositório e colaboração entre integrantes.
- **Visual Studio Code:** ambiente de desenvolvimento.

---

## Estrutura do Repositório

```text
Projeto-Integrador-II/
│
├── src/
│   ├── main.py
│   ├── monitoramento.py
│   ├── interface.py
│   ├── eye_detection.py
│   ├── boca.py
│   ├── head_pose.py
│   │
│   ├── models/
│   │   └── face_landmarker.task
│   │
│   ├── data/
│   │   └── telemetry/
│   │       └── .gitkeep
│   │
│   └── sons/
│       ├── atencao.wav
│       └── fadiga.wav
│
├── .gitignore
├── LICENSE
└── README.md
```

---

## Instalação e Execução

### 1. Clonar o repositório

```bash
git clone https://github.com/KleberASilva/Projeto-Integrador-II.git

cd Projeto-Integrador-II
```

### 2. Criar ambiente virtual

```bash
python -m venv .venv
```

Ativação no Windows:

```powershell
.venv\Scripts\Activate.ps1
```

### 3. Instalar dependências

```bash
pip install opencv-python mediapipe numpy PySide6
```

### 4. Executar o sistema

```bash
python src/main.py
```

É necessário disponibilizar uma webcam para a captura das imagens e o modelo `face_landmarker.task` no diretório `src/models/`.

---

## Modo de Teste

A interface disponibiliza um modo de teste para demonstração dos estados do sistema, permitindo simular situações sem depender da ocorrência de um evento real diante da câmera.

| Tecla | Função |
|---|---|
| F9 | Ativar/desativar modo de teste |
| 1 | Atento |
| 2 | Bocejo |
| 3 | Inclinação da cabeça |
| 4 | Possível fadiga |
| 5 | Rosto não detectado |
| R | Recalibrar |
| F11 | Alternar tela cheia |

Os estados simulados não representam resultados reais dos algoritmos de detecção.

---

## Status do Projeto

**Em desenvolvimento.**

O protótipo possui monitoramento facial em tempo real, interface gráfica e integração dos módulos de detecção de olhos, boca e orientação da cabeça.

As próximas etapas envolvem aprimoramento dos critérios de detecção, avaliação conjunta dos indicadores e validação experimental do sistema.

---

## Disciplina

**Projeto Integrador II**  
**Curso:** Engenharia de Computação  
**Instituição:** Universidade Federal de Santa Maria (UFSM)  
**Orientador:** Prof. Lucas Feksa Ramos

---

## Licença

Consulte o arquivo [LICENSE](LICENSE) para informações sobre os termos de utilização e distribuição do projeto.

## Telemetria por sessão

Cada execução cria um identificador próprio e dois arquivos em
`src/data/telemetry/`:

- `<session_id>/telemetria.csv`: uma linha por frame, com timestamp ISO 8601,
  tempo monotônico desde o início, número do frame, estado, indicadores,
  calibração, PERCLOS e orientação original, filtrada e relativa.
- `<session_id>_eventos.csv`: eventos deduplicados com origem, tipo, início,
  fim, duração, confirmação, motivo de interrupção e frames associados.

Os arquivos existentes não são sobrescritos. Os CSVs gerados são ignorados
por [`.gitignore`](.gitignore) para não entrarem no repositório.

## Marcações manuais

Durante uma sessão, as teclas abaixo registram uma marcação no arquivo de
eventos sem alterar a classificação automática:

| Tecla | Marcação |
|---|---|
| F1 | Início do teste |
| F2 / F3 | Rotação para esquerda / direita |
| F4 / F5 | Inclinação para cima / baixo |
| F6 | Piscadas |
| F7 | Fechamento prolongado |
| F8 | Simulação de bocejo |
| End | Fim do teste |

## Capturas de diagnóstico

O monitoramento da câmera pode permanecer ativo sem gravar arquivos. O botão
**Iniciar coleta** cria uma nova sessão; **Parar coleta** fecha a sessão e
interrompe a gravação de frames e capturas. Fechar a janela também encerra
uma coleta ativa.

Cada sessão possui uma pasta `capturas/` dentro do diretório da sessão. A tecla
`C` ou o botão **Capturar (C)** solicita uma imagem no próximo frame processado.
A linha correspondente em `telemetria.csv` registra o caminho da captura,
mantendo o mesmo `session_id`, timestamp e número do frame.

## Testes automatizados

Execute a suíte determinística com o Python do ambiente virtual:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -p "test_*.py" -v
```

Os testes cobrem cálculo temporal de eventos, calibração sintética dos
detectores, interrupção por ausência de rosto, simetria sintética do yaw,
transições do classificador e persistência dos CSVs. Eles não substituem
testes com webcam.

## Limitações e validação experimental

Os parâmetros de calibração, duração mínima, frequência, cobertura do
PERCLOS, persistência de estados e quantidade mínima de evidências são
configuráveis no código e representam parâmetros de protótipo. Eles não são
limiares clínicos ou uma validação científica de fadiga.

Antes de interpretar o estado `FADIGA`, ainda é necessário realizar testes
com webcam, iluminação e posições variadas, comparando as marcações manuais
com os eventos dos CSVs. Também é necessário avaliar falsos positivos,
falsos negativos, perda de rosto, variação de taxa de quadros e assimetria
residual da orientação da cabeça.

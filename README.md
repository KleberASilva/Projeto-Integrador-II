# Detector de Fadiga Automotivo Baseado em Visão Computacional Embarcada e IoT

Repositório destinado ao desenvolvimento do projeto da disciplina de **Projeto Integrador II**, do curso de **Engenharia de Computação da Universidade Federal de Santa Maria (UFSM)**.

O projeto propõe o desenvolvimento de um **protótipo embarcado, funcional e de baixo custo**, para monitoramento de motoristas, utilizando **visão computacional (Edge Computing)** e, experimentalmente, **sensores fisiológicos**, para identificar sinais de fadiga, sonolência e distração ao volante.

---

### Equipe

* **Kléberson do Amaral da Silva** — [GitHub](https://github.com/KleberASilva/)
* **Pedro Lucca Menezes Vitalis** — [GitHub](https://github.com/pedrovitalis)
* **Vitor Carvalho de Araujo** — [GitHub](https://github.com/arauvitor)
* **Yuri Silveira Pereira** — [GitHub](https://github.com/slaycker13)

**Orientador:** Prof. Lucas Feksa Ramos

---

### Sobre o Projeto

A fadiga ao volante é uma das principais causas de acidentes de trânsito, respondendo por uma parcela significativa dos sinistros no país. Grande parte das soluções comerciais de detecção de fadiga exige hardware proprietário de alto custo ou depende do envio contínuo de imagens do motorista para processamento em nuvem, o que gera custos de conectividade e levanta questões de privacidade.

Este projeto propõe uma alternativa: um dispositivo embarcado que realiza **todo o processamento localmente (Edge Computing)**, sem transmitir imagens para fora do veículo, utilizando uma **câmera modular conectada a um microcontrolador da família ESP**.

A partir da imagem capturada, o sistema extrai landmarks faciais e calcula três indicadores principais:

* **EAR (Eye Aspect Ratio)** — abertura/fechamento dos olhos, usado para detectar micro-sonos e fechamento prolongado das pálpebras;
* **MAR (Mouth Aspect Ratio)** — identificação de bocejos;
* **Head Pose Estimation** — orientação e inclinação da cabeça, usada para detectar relaxamento cervical ("cabeceadas").

Para viabilizar o processamento em hardware modesto e evitar sobreaquecimento, a captura de vídeo utiliza **baixo framerate (subamostragem temporal)**, o que também ajuda a filtrar piscadas normais e focar em anomalias prolongadas.

O sistema também prevê a possibilidade de integração experimental de **sensores fisiológicos de contato no volante** (ex.: ECG via divisor de tensão), como validação complementar, dependendo do avanço do cronograma.

Quando um limiar de fadiga é ultrapassado, o dispositivo aciona um **alarme local (buzzer/LEDs)** e envia via **Wi-Fi** apenas dados textuais mínimos (timestamp + classificação do evento) para fins de **telemetria e posterior validação do algoritmo**, sem transmitir imagens.

---

### Áreas de Exploração

#### Visão Computacional
Processamento das imagens da câmera para identificação do rosto, olhos, boca e orientação da cabeça do motorista.

#### Inteligência Artificial
Exploração de técnicas de reconhecimento e classificação de padrões relacionados à fadiga e distração.

#### Sistemas Embarcados
Desenvolvimento da unidade embarcada utilizando microcontroladores da família ESP e integração com sensores e dispositivos de captura.

#### Internet das Coisas (IoT)
Comunicação entre o dispositivo embarcado, servidor e sistemas de monitoramento, restrita ao envio de dados de telemetria.

#### Processamento de Sinais
Aquisição e análise experimental de sinais fisiológicos obtidos por sensores de contato no volante.

#### Monitoramento e Análise de Dados
Armazenamento, processamento e visualização dos dados coletados durante os testes, incluindo o cruzamento entre eventos registrados e gravações de validação (ground truth).

---

### Tecnologias e Ferramentas

#### Desenvolvimento
* **Python** — desenvolvimento dos algoritmos;
* **OpenCV** — processamento de imagens;
* **MediaPipe / Dlib ou equivalente** — extração de landmarks e geometria facial;
* **VS Code ou outros** — ambiente de desenvolvimento.

#### Hardware e Sistemas Embarcados
* **ESP32/ESP8266** — plataforma embarcada (ajustar escolha ainda);
* **Câmera modular** — captura das imagens do motorista;
* **Sensores de contato** — aquisição experimental de sinais fisiológicos;
* **LEDs, buzzer e outros atuadores** — geração de alertas locais;
* **ElegantOTA** — atualização remota do firmware.

#### IoT e Infraestrutura
* **Ubuntu Server** — servidor para hospedagem dos serviços;
* **Node-RED** — integração, automação e comunicação entre os componentes;
* **InfluxDB** — armazenamento de séries temporais (telemetria);
* **Grafana** — dashboards e visualização dos dados;
* **ZeroTier** — comunicação remota e rede virtual.

#### Desenvolvimento e Prototipagem
* **Git** — controle de versão;
* **GitHub** — hospedagem e colaboração no código;
* **Tinkercad** — prototipagem e simulação de circuitos eletrônicos.

---

### Estrutura do Repositório


### Como Clonar

---

### Status do Projeto

**Em desenvolvimento**

---

### Disciplina

**Projeto Integrador II**
**Curso:** Engenharia de Computação
**Instituição:** Universidade Federal de Santa Maria — UFSM
**Orientador:** Prof. Lucas Feksa Ramos

---

### Licença

Definir licença do repositório (ex.: MIT, GPL-3.0) — ver seção de configuração recomendada abaixo.

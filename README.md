# NOME do projeto — Sistema Embarcado de Monitoramento de Motoristas

Repositório destinado ao desenvolvimento do projeto da disciplina de **Projeto Integrador II**, do curso de **Engenharia de Computação da Universidade Federal de Santa Maria (UFSM)**.

O **Nome do projeto definir** propõe o desenvolvimento de um protótipo embarcado para monitoramento de motoristas, utilizando **visão computacional e sensores fisiológicos** para identificar possíveis sinais de fadiga, distração e alterações nos parâmetros monitorados.

---

### Equipe

* **Kléberson do Amaral da Silva** — [GitHub](https://github.com/KleberASilva/)
* **Pedro Lucca Menezes Vitalis** — [GitHub](https://github.com/)
* **Vitor Carvalho de Araujo** — [GitHub](https://github.com/)
* **Yuri Silveira Pereira** — [GitHub](https://github.com/)

---

### Sobre o Projeto

O **NOME** é um protótipo de sistema embarcado voltado ao **monitoramento de motoristas**, com foco na identificação de possíveis situações de **fadiga e distração durante a condução**.

O sistema utilizará uma **câmera modular conectada a um microcontrolador da família ESP** para capturar informações visuais do motorista. A partir das imagens, serão analisados indicadores como:

* Abertura e fechamento dos olhos;
* Duração dos períodos com os olhos fechados;
* Frequência de piscadas;
* Possíveis bocejos;
* Orientação e movimentação da cabeça;
* Permanência da cabeça desviada da posição considerada normal.

O projeto também prevê a utilização de **sensores de contato no volante** para aquisição experimental de sinais fisiológicos, permitindo complementar o monitoramento visual com informações relacionadas ao estado do motorista.

A partir dos dados coletados, o sistema poderá gerar indicadores de **fadiga, distração e sinais fisiológicos**, além de um nível geral de risco. Em situações que ultrapassem determinados parâmetros, serão gerados **alertas ao motorista** e os eventos poderão ser registrados para posterior análise.

> **Observação:** Nao temos observação ainda

---

### Áreas de Exploração

#### Visão Computacional

Processamento das imagens da câmera para identificação do rosto, olhos, boca e orientação da cabeça do motorista.

#### Inteligência Artificial

Exploração de técnicas de reconhecimento e classificação de padrões relacionados à fadiga e distração.

#### Sistemas Embarcados

Desenvolvimento da unidade embarcada utilizando microcontroladores da família ESP e integração com os sensores e dispositivos de captura.

#### Internet das Coisas (IoT)

Comunicação entre o dispositivo embarcado, servidor e sistemas de monitoramento.

#### Processamento de Sinais

Aquisição e análise experimental de sinais fisiológicos obtidos por sensores de contato no volante.

#### Monitoramento e Análise de Dados

Armazenamento, processamento e visualização dos dados coletados durante os testes.

---

### Tecnologias e Ferramentas

#### Desenvolvimento

* **Python** — desenvolvimento dos algoritmos;
* **OpenCV** — processamento de imagens;
* **MediaPipe ou ferramenta equivalente** — detecção de características faciais;
* **VS Code ou outros** — ambiente de desenvolvimento.

#### Hardware e Sistemas Embarcados

* **ESP32/ESP8266** — plataforma embarcada; (Ajustar escolha ainda)
* **Câmera modular** — captura das imagens do motorista;
* **Sensores de contato** — aquisição experimental de sinais fisiológicos;
* **LEDs, buzzer e outros atuadores** — geração de alertas;
* **ElegantOTA** — atualização remota do firmware.

#### IoT e Infraestrutura

* **Ubuntu Server** — servidor para hospedagem dos serviços;
* **Node-RED** — integração, automação e comunicação entre os componentes;
* **InfluxDB** — armazenamento de séries temporais;
* **Grafana** — dashboards e visualização dos dados;
* **ZeroTier** — comunicação remota e rede virtual.

#### Desenvolvimento e Prototipagem

* **Git** — controle de versão;
* **GitHub** — hospedagem e colaboração no código;
* **Tinkercad** — prototipagem e simulação de circuitos eletrônicos.

---

### Estrutura do Repositório

#### Definir organização do repo ainda
---

### Status do Projeto

**EM desenvolvimento**

---

### Disciplina

**Projeto Integrador II**
**Curso:** Engenharia de Computação
**Instituição:** Universidade Federal de Santa Maria — UFSM

#### Orientação

* **Prof. Lucas Feksa Ramos** — *a confirmar com ele ;-;*

---

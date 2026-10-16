import math

# Pontos da boca no MediaPipe (cantos e lábios superior/inferior)
BOCA = [61, 37, 267, 291, 314, 84]

def distancia(p1, p2):
    # math.hypot é mais rápido e otimizado em C do que fazer a raiz quadrada manual
    return math.hypot(p1.x - p2.x, p1.y - p2.y)

def calcular_mar(landmarks, pontos):
    p_esq, p_dir = landmarks[pontos[0]], landmarks[pontos[3]]
    distancia_horizontal = distancia(p_esq, p_dir)
    
    if distancia_horizontal == 0:
        return 0.0

    # Pares verticais da boca (p1 com p5, p2 com p4)
    pares_verticais = [
        (landmarks[pontos[1]], landmarks[pontos[5]]),
        (landmarks[pontos[2]], landmarks[pontos[4]])
    ]
    
    # Soma direta usando list comprehension
    soma_vertical = sum(distancia(p_cima, p_baixo) for p_cima, p_baixo in pares_verticais)

    return soma_vertical / (2 * distancia_horizontal)

class DetectorBocejo:
    def __init__(self, tempo_calibracao=5, tempo_minimo_bocejo=1.0):
        self.tempo_calibracao = tempo_calibracao
        self.tempo_minimo_bocejo = tempo_minimo_bocejo
        self.inicio = None
        self.calibrando = True
        self.valores_calibracao = []
        self.mar_referencia = None
        self.limiar_mar = None
        
        self.inicio_bocejo = None

    def atualizar(self, mar_atual, tempo_atual):
        if self.inicio is None:
            self.inicio = tempo_atual

        if self.calibrando:
            self.valores_calibracao.append(mar_atual)
            
            if (tempo_atual - self.inicio) >= self.tempo_calibracao:
                self.mar_referencia = sum(self.valores_calibracao) / len(self.valores_calibracao)
                self.limiar_mar = self.mar_referencia * 1.5 
                self.calibrando = False
            return False, 0

        # Verifica se a boca está aberta acima do limiar
        if mar_atual > self.limiar_mar:
            if self.inicio_bocejo is None:
                self.inicio_bocejo = tempo_atual
            
            tempo_aberto = tempo_atual - self.inicio_bocejo
            
            # Retorna True CONTINUAMENTE enquanto a boca estiver aberta por mais de 1s
            if tempo_aberto >= self.tempo_minimo_bocejo:
                return True, tempo_aberto 
            
            # Boca aberta, mas ainda não deu 1 segundo
            return False, tempo_aberto 
        
        else:
            # Boca fechou, zera o cronômetro
            self.inicio_bocejo = None
            return False, 0
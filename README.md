# diablo-auto-fish

## Introdução

O script se baseia nos gráficos na tela e emula funções de mouse e teclado para realizar a pesca automática no Diablo Immortal. Devido à sua natureza, o jogo deve estar em primeiro plano para que o script funcione corretamente. Além disso, por causa das possíveis diferenças na renderização de cores em diferentes sistemas operacionais e versões de software/hardware, o script pode exigir edições (especialmente em termos de cores RGB) para funcionar corretamente em uma máquina específica.

Observação: o script é para fins de discussão e estudo e não deve ser usado para quebrar a justiça do jogo.

## Para usuários Windows:

### $\color{red}\text{Atualizações em destaque}$
- Agora suporta salvamento automático (funciona muito melhor com o Tesseract, consulte as seções posteriores para instalação). Com essa função ativada, ele verifica a capacidade da mochila após cada ciclo de pesca (quando 20 peixes são obtidos) e retorna à cidade para salvar se a capacidade da mochila estiver abaixo do nível definido.
- Agora a tecla de pesca pode ser definida como uma tecla personalizada, com o padrão sendo '5' (anteriormente fixada no botão direito do mouse).
- A coleta de itens foi otimizada para reduzir a chance de perder ouro dropado.

### Requisitos
- Python 3 (Python 3.10 testado)
- numpy
- opencv-python
- Pillow
- pyautogui
- $\color{red}\text{pytesseract}$

### Instalação
- Instale o Python 3;
- Após baixar o código para o local, abra o prompt de comando (Winkey + R, digite cmd e pressione Enter), execute:


```
cd <caminho-para-o-diretório>
python -m pip install -r requirements.txt
```

- $\color{red}\text{Instale o Tesseract}$ (para reconhecer texto em imagens e encontrar NPCs):
  - Baixe o [arquivo de instalação](https://digi.bib.uni-mannheim.de/tesseract/tesseract-ocr-w64-setup-5.3.1.20230401.exe) (ou [aqui](https://github.com/UB-Mannheim/tesseract/wiki));
  - Execute o arquivo de instalação e siga as instruções. Certifique-se de que o $\color{red}\text{caminho de instalação}$ seja: `C:/Program Files/Tesseract-OCR/`.

### Configurações no jogo
- Defina a resolução do monitor para 1920x1080 e execute o jogo na **versão em inglês** (pode haver suporte para a interface em chinês no futuro);
- Configurações de exibição:
  - Modo de imagem: Clássico
  - Modo de janela: Tela cheia
  - Brilho do ambiente: 50%
- Configurações gráficas:
  - Defina todas as opções de qualidade para o nível mais baixo;
  - Desative todos os efeitos.
- Configurações de teclas:
  - Mover/Atacar: **Não** defina como botão esquerdo do mouse
  - Habilidade de pesca: ~~Botão direito do mouse~~ $\color{red}\text{Agora pode ser definida como uma tecla, padrão: 5}$
  - **Não defina o botão esquerdo do mouse para nenhuma habilidade ou ação**
- Posicione-se no ponto de pesca, não fique muito longe do NPC (deve estar dentro da distância de diálogo).

### Iniciar a pesca
- Certifique-se de que o jogo está em execução, use ALT + TAB para alternar para a janela do script e abra `fishing.py`;
- Selecione o tipo de peixe e a localização, mantenha a barra de brilho no padrão;
- Atualmente há 3 modos:
  - **Pesca automática contínua**: vende peixes e compra iscas automaticamente;
  - **Apenas uma rodada de pesca**: pesca até acabar as iscas ou obter 20 peixes;
  - **Apenas vender/comprar**: não pesca, apenas gerencia itens.
- Para parar, alterne para a janela do script e clique em "Parar".

### Contato

Se tiver dúvidas ou preocupações, entre em contato: q30zhang@gmail.com.
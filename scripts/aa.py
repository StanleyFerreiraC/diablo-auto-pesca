from gui import GUI
from util import *

# Remove capturas de tela temporárias antes de iniciar
clear_temp_screenshots()


def pull(brightness=50):
    """
    Realiza a ação de puxar o peixe, ajustando a barra de acordo com o brilho atual.
    
    Em sistemas macOS, captura uma linha da tela e converte a imagem para escala de cinza.
    Em Windows, utiliza uma imagem capturada e salva temporariamente.
    
    Args:
        brightness (int, opcional): Nível de brilho para ajustar o limiar da barra. Padrão é 50.
    
    Returns:
        int ou None: O intervalo de limites da barra (bound_range) se a ação for bem-sucedida,
        ou None se não for possível realizar a operação (ex.: se a posição atual não for válida).
    """
    if sys.platform == "darwin":
        # Para macOS: captura uma linha da tela e converte a imagem (inverte canais)
        im_bar = screenshot(region=(x0 + 612, y0 + 214, 882, 1))[:, :, ::-1]
        dark_color_gray = 70
        bright_color_gray = 165
        n_dark = 10     # Número de pixels escuros consecutivos para determinar a posição atual
        n_offset = 8    # Offset para retroceder após encontrar os pixels escuros
        lb_range = 150
        ub_range = 350
        lb_right_end = 650
        amount_pull = 80  # Quantidade de mudança na posição para cada puxão
    else:
        # Para Windows: utiliza uma captura de tela salva temporariamente
        im_bar = screenshot(os.path.join(TEMP_DIR, "temp.png"), region=(x0 + 560, y0 + 145, 806, 1))
        dark_color_gray = 70
        bright_color_gray = int(brightness / 10) + 150
        n_dark = 9     # Número de pixels escuros consecutivos para determinar a posição atual
        n_offset = 7    # Offset para retroceder após encontrar os pixels escuros
        lb_range = 130
        ub_range = 300
        lb_right_end = 600
        amount_pull = 65  # Quantidade de mudança na posição para cada puxão

    # Converte a linha capturada para escala de cinza usando ponderação dos canais RGB
    bar_g = np.dot(np.array(im_bar)[0, :, :3], [0.2989, 0.5870, 0.1140])
    dark = np.where(bar_g < dark_color_gray)[0]  # Índices de pixels escuros
    diff_dark = np.diff(dark)  # Diferença entre pixels consecutivos

    bounds = np.where(bar_g > bright_color_gray)[0]  # Índices de pixels brilhantes
    bound_range = bounds.ptp() if bounds.shape[0] > 1 else 0
    current = None
    j = 0
    # Procura por uma sequência de pixels escuros consecutivos para determinar a posição atual da barra
    while j < len(diff_dark) - n_dark:
        next_dark = np.where(diff_dark[j:j + n_dark] != 1)[0]
        if next_dark.shape[0] == 0:
            current = dark[j] - n_offset
            break
        j += next_dark[-1] + 1
    if current is None or current < 0 or bounds.shape[0] == 0:
        return None

    # Verifica condições baseadas na quantidade de pixels brilhantes e intervalo para decidir a ação
    if (2 <= bounds.shape[0] <= 10 and lb_range < bound_range < ub_range) or (bounds[0] > lb_right_end and bound_range < 10):
        if bounds[0] < current < bounds[-1] - amount_pull:
            if sys.platform == "darwin":
                p.press('n')
            else:
                click_box(boxes[READY])
        elif bound_range < 10:
            pull_count = (bar_g.shape[0] - current) // amount_pull
            if sys.platform == "darwin":
                p.write('n' * pull_count)
            else:
                click_box(boxes[READY], pull_count)
        elif current < bounds[0]:
            pull_count = (bounds[-1] - current) // amount_pull
            if sys.platform == "darwin":
                p.write('n' * pull_count)
            else:
                click_box(boxes[READY], pull_count)
        else:
            p.sleep(random.random() * 0.03)
        return bound_range
    return None


def check_status(prev_status, fish_type="yellow"):
    """
    Verifica o status atual da pesca, comparando as imagens da tela com referências conhecidas.
    
    A função checa, na ordem, por interrupções (lair, party, raid), pela ação de puxar,
    pelo estado pronto para pescar, esperando o peixe morder ou em standby, registrando
    os tempos de execução para log.
    
    Args:
        prev_status (str): Status anterior, utilizado para evitar logs repetitivos.
        fish_type (str, opcional): Tipo de peixe ("yellow", "white", "blue"). Padrão é "yellow".
    
    Returns:
        tuple: (status, box), onde status é uma string representando o estado atual e box é a área (Box) detectada.
    """
    t0 = time.time()
    box = check(INTERRUPTED_LAIR)
    if box:
        if prev_status != INTERRUPTED_LAIR:
            log(f"interrupted by lair, check took {time.time() - t0:.2f} seconds.")
        return INTERRUPTED_LAIR, box
    box = check(INTERRUPTED_PARTY)
    if box:
        if prev_status != INTERRUPTED_PARTY:
            log(f"interrupted by party, check took {time.time() - t0:.2f} seconds.")
        return INTERRUPTED_PARTY, box
    if sys.platform == "win32":
        box = check(INTERRUPTED_RAID)
        if box:
            if prev_status != INTERRUPTED_RAID:
                log(f"interrupted by raid, check took {time.time() - t0:.2f} seconds.")
            return INTERRUPTED_RAID, box
    box = check(PULLING)
    if box:
        if prev_status != PULLING:
            log(f"pulling fish, check took {time.time() - t0:.2f} seconds.")
        return PULLING, box
    box = check(READY, confidence=0.99)
    if box and (sys.platform == "darwin" or not image_is_gray(screenshot(region=box))):
        if prev_status not in [WAITING, BONUS_NOT_REACHED]:
            log(f"fish up, check took {time.time() - t0:.2f} seconds.")
        fish_type_coords = (x0 + FISH_TYPE_X_COORD[fish_type], y0 + FISH_TYPE_Y_COORD)
        if pixel_match_color(*fish_type_coords, FISH_TYPE_COLOR, FISH_TYPE_X_COORD_TOLERANCE) or fish_type == "white":
            if prev_status != READY:
                log(f"ready to fish, check took {time.time() - t0:.2f} seconds.")
            return READY, box
        if prev_status not in [WAITING, BONUS_NOT_REACHED]:
            log(f"bonus did not reach yellow, check took {time.time() - t0:.2f} seconds.")
        return BONUS_NOT_REACHED, box
    box = check(WAITING, confidence=0.99)
    if box and (sys.platform == "darwin" or image_is_gray(screenshot(region=box))):
        if prev_status not in [WAITING, BONUS_NOT_REACHED]:
            log(f"waiting for fish, check took {time.time() - t0:.2f} seconds.")
        return WAITING, box
    box = check(STANDBY, confidence=0.8)
    if box:
        if prev_status != STANDBY:
            log(f"standby, check took {time.time() - t0:.2f} seconds.")
        return STANDBY, box
    box = check(PICK)
    if box:
        if prev_status != PICK:
            log(f"pick an item, check took {time.time() - t0:.2f} seconds.")
        return PICK, box
    return None, None


def fish(fish_type="yellow", fish_key='5', brightness=50, stop=None):
    """
    Controla o ciclo completo de pesca, integrando a detecção de status e as ações correspondentes.
    
    O método ativa a janela do jogo e executa um loop que:\n
      - Verifica o status atual (ex.: puxando, standby, pronto, etc.)\n
      - Executa a ação correspondente (puxar, clicar, pressionar teclas, etc.)\n
      - Gerencia contagens de tentativas e intervalos entre ações
    
    Args:
        fish_type (str, opcional): Tipo de peixe desejado ("yellow", "white", "blue"). Padrão é "yellow".
        fish_key (str, opcional): Tecla de pesca a ser utilizada. Padrão é '5'.
        brightness (int, opcional): Nível de brilho para ajuste da barra. Padrão é 50.
        stop (callable, opcional): Função que retorna True para interromper o ciclo. Se None, o ciclo não é interrompido.
    
    Returns:
        bool: True se o ciclo de pesca concluir sem interrupção, False caso contrário.
    """
    if stop is None:
        def stop():
            return False
    prev_status = ''
    pickup_attempted = 0
    last_pickup_time = time.time()
    fishing_attempted = 0
    n_standby_cont = 0
    last_fish_up_time = 0  # Tempo do último evento de peixe levantado sem atingir o bônus amarelo
    activate_diablo()
    while fishing_attempted < 30 and n_standby_cont < 3:
        if stop():
            return False
        status, box = check_status(prev_status, fish_type)
        if not status:
            continue
        if status == PULLING:
            t = time.time()
            bar_or_bounds_not_found_time = time.time()
            while time.time() - t < MAX_FISHING_TIME and time.time() - bar_or_bounds_not_found_time < MAX_TIMEOUT:
                if pull(brightness):  # Se o puxão foi bem-sucedido, atualiza o tempo\n
                    bar_or_bounds_not_found_time = time.time()
            continue
        if status in [INTERRUPTED_PARTY, INTERRUPTED_LAIR, INTERRUPTED_RAID]:
            activate_diablo()
            click_box(box)
        elif status == PICK:
            activate_diablo()
            click_box(box)
        elif status == STANDBY:
            activate_diablo()
            if sys.platform == "darwin":
                click_box(box)
            else:
                # Para Windows, simula o lançamento da vara de pesca\n
                cast_fishing_rod(fish_key, box)
                p.moveTo(box.left, box.top)
                if fishing_attempted == 0:
                    p.sleep(0.5)
                    for _ in range(10):
                        DIKeys.press(hexKeyMap.DIK_E, 0.01)
                        p.sleep(round(0.05 + random.random() * 0.1, 1))
            fishing_attempted += 1
            if time.time() - last_pickup_time > 600:
                pickup_attempted = 0
            if prev_status == STANDBY:
                n_standby_cont += 1
            else:
                n_standby_cont = 1
            p.sleep(1)
            log(f"number of fishing attempts: {fishing_attempted}")
        elif status == READY and time.time() - last_fish_up_time > 10:
            activate_diablo()
            p.sleep(0.1)
            click_box(box)
            p.sleep(0.1)
            status = PULLING
            t = time.time()
            bar_or_bounds_not_found_time = time.time()
            while time.time() - t < MAX_FISHING_TIME and time.time() - bar_or_bounds_not_found_time < MAX_TIMEOUT:
                if pull(brightness):  # Se o puxão foi bem-sucedido\n
                    bar_or_bounds_not_found_time = time.time()
            if sys.platform == "win32":
                p.moveTo(find_npc() or (960, 540))
        elif status == BONUS_NOT_REACHED:
            last_fish_up_time = time.time()
        elif status == WAITING and sys.platform == "win32" and pickup_attempted < PICKUP_LIMIT:
            log("pick up items...")
            last_pickup_time = time.time()
            for _ in range(15):
                DIKeys.press(hexKeyMap.DIK_E, 0.01)
                p.sleep(round(0.05 + random.random() * 0.1, 1))
            if pickup_win32(pickup_attempted):
                pickup_attempted += 1
            else:
                pickup_attempted = PICKUP_LIMIT
        prev_status = status
        p.sleep(1)
    return True


def check_npc_or_fish():
    """
    Verifica a presença de NPCs ou a disponibilidade de peixes na tela.
    
    Returns:
        tuple: (status, box), onde status pode ser INTERRUPTED_PARTY, TALK, STANDBY ou PICK, e box é a área (Box) detectada.
    """
    box = check(INTERRUPTED_PARTY)
    if box:
        return INTERRUPTED_PARTY, box

    box = check(TALK)
    if box:
        return TALK, box

    box = check(STANDBY)
    if box:
        return STANDBY, box

    box = check(PICK)
    if box:
        log("picking up items")
        return PICK, box

    return None, None


def walk(key, duration=0.1):
    """
    Simula o movimento do personagem pressionando uma tecla por um determinado tempo.
    
    Args:
        key (str): A tecla a ser pressionada para mover o personagem.
        duration (float, opcional): Duração (em segundos) do movimento. Padrão é 0.1.
    """
    activate_diablo()
    p.sleep(0.3)
    p.keyDown(key)
    p.sleep(duration)
    p.keyUp(key)


def trade_fish_buy_bait_go_back(key_to_npc, key_to_fish):
    """
    Executa a sequência de troca de peixes, compra de iscas e retorno à pesca.
    
    A função realiza um loop que:\n
      - Verifica o status atual para lidar com interrupções ou diálogos.\n
      - Executa a troca (trade), a compra (buy) e, por fim, o retorno (back) ao local de pesca.
    
    Args:
        key_to_npc (str): Tecla para se aproximar do NPC.\n
        key_to_fish (str): Tecla para retornar à pesca.
    
    Returns:
        int: 0 ao concluir a sequência.
    """
    stage = "trade"
    while True:
        log(stage)
        status, box = check_npc_or_fish()

        if status == INTERRUPTED_PARTY:
            activate_diablo()
            click_box(box)
        elif status == TALK and stage == "trade":
            trade_fish()
            stage = "buy"
            p.sleep(1)
        elif status == TALK and stage == "buy":
            buy_bait()
            p.sleep(0.5)
            walk('d', 0.02)
            stage = "back"
        elif status == STANDBY and stage == "back":
            return 0
        elif status == PICK:
            activate_diablo()
            p.sleep(0.1)
            p.press('space')
        elif stage == "trade":
            walk(key_to_npc)
        elif stage == "buy":
            walk(key_to_npc, 0.05)
        elif stage == "back":
            walk(key_to_fish)
        p.sleep(2)


def trade_fish():
    """
    Realiza a troca de peixes com o NPC.
    
    A sequência inclui:\n
      - Pressionar a barra de espaço.\n
      - Executar cliques em posições pré-definidas para selecionar e confirmar a troca.
    
    Após a troca, aguarda um tempo para que a operação seja concluída.
    """
    log("selling fish to npc...")
    p.press('space')
    p.sleep(1)
    p.click(x0 // 2 + 850, y0 // 2 + 540)
    p.sleep(0.5)
    p.click(x0 // 2 + 530, y0 // 2 + 660)
    p.sleep(0.2)
    p.click(x0 // 2 + 880, y0 // 2 + 650)
    p.sleep(0.2)
    p.click(x0 // 2 + 1010, y0 // 2 + 170)
    p.sleep(15)
    walk('w', 0.2)


def buy_bait():
    """
    Realiza a compra de iscas por meio de uma sequência de cliques em posições específicas na tela.
    
    A função simula cliques com intervalos curtos para assegurar o registro correto da ação.
    """
    log("buying baits...")
    p.press('space')
    p.sleep(1)
    p.click(x0 // 2 + 840, y0 // 2 + 600)
    p.sleep(1)
    p.click(x0 // 2 + 890, y0 // 2 + 600)
    p.sleep(0.2)
    p.click(x0 // 2 + 960, y0 // 2 + 470)
    p.sleep(0.2)
    p.click(x0 // 2 + 960, y0 // 2 + 470)
    p.sleep(0.2)
    p.click(x0 // 2 + 960, y0 // 2 + 470)
    p.sleep(0.2)
    p.click(x0 // 2 + 900, y0 // 2 + 655)
    p.sleep(0.2)
    p.click(x0 // 2 + 1010, y0 // 2 + 170)
    p.sleep(0.2)
    p.click(x0 // 2 + 1010, y0 // 2 + 170)


def trade_with_gui(attempts_trade=3, attempts_sell=3):
    """
    Gerencia a troca de peixes utilizando a interface gráfica (GUI).
    
    Tenta vender e, se necessário, comprar iscas, realizando múltiplas tentativas em caso de erro.
    
    Args:
        attempts_trade (int, opcional): Número de tentativas para a troca. Padrão é 3.
        attempts_sell (int, opcional): Número de tentativas para a venda. Padrão é 3.
    
    Returns:
        int: 0 se a operação for concluída com sucesso.
    """
    if attempts_trade > 0:
        p.sleep(1)
        log("selling based on gui")
        position = find_npc()
        if not position:
            return trade_with_gui(attempts_trade - 1)
        p.click(position)
        error = 0
        error += click_image("trade", time.time(), 3)
        error += click_image("select", time.time(), 3)
        error += click_image("exchange", time.time(), 3, confidence=0.97)
        p.sleep(1)
        if error > 0:
            p.click(window.center)
            p.sleep(0.3)
            p.click(window.center)
            p.sleep(0.3)
            click_image("x", time.time(), 1)
            p.sleep(0.5)
            p.click(window.center)
            p.sleep(1)
            return trade_with_gui(attempts_trade - 1)
        else:
            return trade_with_gui(0)
    elif attempts_sell > 0:
        p.sleep(3)
        log("buying baits...")
        while True:
            for status in [INTERRUPTED_LAIR, INTERRUPTED_PARTY, INTERRUPTED_RAID]:
                box = check(status)
                if box:
                    click_box(box)
            if not box:
                break
        position = find_npc()
        if not position:
            return trade_with_gui(0, attempts_sell - 1)
        p.click(position)
        error = 0
        error += click_image("shop", time.time(), 3)
        error += click_image("amount", time.time(), 3, offset=(0.2, 0.7, -0.2, -0.1))
        error += click_image("9", time.time(), 3, clicks=3, interval=0.5)
        error += click_image("buy", time.time(), 3, confidence=0.97, region_boarder_x=15, region_boarder_y=15)
        error += click_image("x", time.time(), 3)
        if error > 0:
            return trade_with_gui(0, attempts_sell - 1)
        p.sleep(1)
        DIKeys.press(hexKeyMap.DIK_Q)
        p.sleep(0.1)
        DIKeys.press(hexKeyMap.DIK_D, 1)
        p.sleep(0.1)
        DIKeys.press(hexKeyMap.DIK_A, 1)
    return 0


def pickup_win32(attempted=0, pickup_blue=True, legendary_alarm=False):
    """
    Realiza a coleta de itens na tela (para Windows) com base na detecção de cores específicas.
    
    A função detecta itens com cores pré-definidas (azul, amarelo e laranja) e simula cliques em uma região para coletá-los.
    Se a coleta encontrar muitos itens lendários (laranja), dispara um alarme.
    
    Args:
        attempted (int, opcional): Número da tentativa atual. Padrão é 0.
        pickup_blue (bool, opcional): Se True, considera itens azuis; caso contrário, apenas itens amarelos. Padrão é True.
        legendary_alarm (bool, opcional): Se True, dispara um alarme ao detectar muitos itens lendários. Padrão é False.
    
    Returns:
        bool: True se a coleta foi realizada com sucesso, False se nenhum item for detectado.
    """
    blue_rgb = np.array([89, 96, 241])
    yellow_rgb = np.array([233, 231, 77])
    orange_rgb = np.array([243, 143, 36])
    color_threshold = 5
    min_y_offset = 30
    max_y_offset = 150
    click_span = 120
    click_flex = 30
    region = (400, 240, 1120, 600)  # (x, y, largura, altura)
    im = screenshot(os.path.join(TEMP_DIR, "items_check.png"), region=region)
    if pickup_blue:
        pts = np.argwhere((np.abs(np.array(im)[:, :, :3] - blue_rgb) <= color_threshold).all(axis=2) |
                          (np.abs(np.array(im)[:, :, :3] - yellow_rgb) <= color_threshold).all(axis=2) |
                          (np.abs(np.array(im)[:, :, :3] - orange_rgb) <= color_threshold).all(axis=2))
    else:
        pts = np.argwhere((np.abs(np.array(im)[:, :, :3] - yellow_rgb) <= color_threshold).all(axis=2) |
                          (np.abs(np.array(im)[:, :, :3] - blue_rgb) <= color_threshold).all(axis=2))
    if pts.shape[0] == 0:
        return False
    top_left = pts.min(axis=0)  # Determina o canto superior esquerdo da região dos itens\n
    height_width = pts.max(axis=0) - top_left
    click_region = (region[0] + top_left[1], region[1] + top_left[0] + min_y_offset,
                    height_width[1], height_width[0] + max_y_offset - min_y_offset)
    for j in range(0, click_region[3] // click_span + 1):
        y = int(click_region[1] + click_span * (j + 0.5) + (random.random() - 0.5) * click_flex)
        for i in range(0, click_region[2] // click_span + 1):
            x = int(click_region[0] + click_span * (i + 0.5) + (random.random() - 0.5) * click_flex)
            p.click(x, y)
            p.sleep(0.1)
    if legendary_alarm and attempted >= PICKUP_LIMIT - 1:
        if np.where((np.abs(np.array(im)[:, :, :3] - orange_rgb) <= color_threshold).all(axis=2))[0].shape[0] > 10:
            alarm_legendary()
    log(f"finished picking attempt #{attempted + 1}")
    return True


def salvage(location, tries=3, stuck_limit=30, navigation_time_limit=60, stop=None):
    """
    Realiza o processo de salvamento de itens (salvage) quando a bolsa está cheia.
    
    A função navega pelo mapa até o NPC apropriado (ex.: blacksmith) para vender os itens,
    ou retorna à pesca caso o NPC não seja encontrado, utilizando múltiplos estágios.\n
    Se a operação travar por muito tempo, tenta novamente com um número reduzido de tentativas.
    
    Args:
        location (str): Localização atual do personagem (ex.: 'bilefen', 'tundra', 'ashwold').
        tries (int, opcional): Número de tentativas para a operação. Padrão é 3.
        stuck_limit (int, opcional): Número máximo de ciclos sem mudança de estágio antes de considerar travado. Padrão é 30.
        navigation_time_limit (int, opcional): Tempo máximo para navegar até o NPC (em segundos). Padrão é 60.
        stop (callable, opcional): Função que retorna True para interromper a operação. Se None, a operação não é interrompida.
    
    Returns:
        bool: True se o salvamento for concluído com sucesso, False caso contrário.
    """

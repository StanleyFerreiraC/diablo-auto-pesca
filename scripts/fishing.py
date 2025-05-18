from gui import GUI
from util import *

# Remove capturas de tela temporárias antes de iniciar
clear_temp_screenshots()


def pull(box):
    """
    Verifica a presença da cor verde na barra e pressiona espaço se não estiver verde.
    """
    # Coordenadas da região da barra (ajuste conforme necessário)
    bar_region = (x0 + 560, y0 + 160, 806, 2)
    
    # Captura a região da barra EM CORES (não escala de cinza)
    im_bar = screenshot(os.path.join(TEMP_DIR, "temp.png"), region=bar_region)
    
    # Define a cor verde desejada (RGB) e tolerância (ajuste conforme seu jogo)
    target_green = [111, 44, 35] 
    tolerance = 20  # Margem para variação de cor
    
    # Converte a imagem para array numpy e verifica pixels verdes
    im_array = np.array(im_bar)
    green_pixels = np.abs(im_array[:, :, :3] - target_green) < tolerance
    green_percentage = np.mean(green_pixels.all(axis=2)) * 100  # % de pixels verdes
    # Lógica de ação
    if green_percentage > 1:  # Se menos de % da barra estiver verde
        click_box(box)
        print(f"Barra fora do verde ({green_percentage:.1f}% verde). Espaço pressionado.")
        return green_percentage
    else:
        print(f"Barra estável ({green_percentage:.1f}% verde).")

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
            log(f"interrompido por covil, cheque levou {time.time() - t0:.2f} seconds.")
        return INTERRUPTED_LAIR, box
    box = check(INTERRUPTED_PARTY)
    if box:
        if prev_status != INTERRUPTED_PARTY:
            log(f"interrompido pela festa, cheque levou {time.time() - t0:.2f} seconds.")
        return INTERRUPTED_PARTY, box
    if sys.platform == "win32":
        box = check(INTERRUPTED_RAID)
        if box:
            if prev_status != INTERRUPTED_RAID:
                log(f"interrompido por ataque, cheque levou {time.time() - t0:.2f} seconds.")
            return INTERRUPTED_RAID, box
    box = check(PULLING)
    if box:
        if prev_status != PULLING:
            log(f"puxando peixe, verifique levou {time.time() - t0:.2f} seconds.")
        return PULLING, box
    box = check(READY, confidence=0.99)
    if box:
        # Certifique-se de que todos os valores são inteiros
        region_tuple = (int(box.left), int(box.top), int(box.width), int(box.height))
        try:
            img = screenshot(region=region_tuple)
            is_gray = image_is_gray(img)
            if sys.platform == "darwin" or not is_gray:
                if prev_status not in [WAITING, BONUS_NOT_REACHED]:
                    log(f"pescar, check took {time.time() - t0:.2f} seconds.")
                fish_type_coords = (x0 + FISH_TYPE_X_COORD[fish_type], y0 + FISH_TYPE_Y_COORD)
                if pixel_match_color(*fish_type_coords, FISH_TYPE_COLOR, FISH_TYPE_X_COORD_TOLERANCE) or fish_type == "white":
                    if prev_status != READY:
                        log(f"pronto para pescar {time.time() - t0:.2f} seconds.")
                    return READY, box
                if prev_status not in [WAITING, BONUS_NOT_REACHED]:
                    log(f"bônus não chegou amarelo, check took {time.time() - t0:.2f} segundos.")
                return BONUS_NOT_REACHED, box
        except Exception as e:
            print(f"Erro ao capturar ou analisar a tela: {e}")
            return None, None
    box = check(WAITING, confidence=0.99)
    if box:
        try:
            # Certifique-se de que todos os valores são inteiros
            region_tuple = (int(box.left), int(box.top), int(box.width), int(box.height))
            img = screenshot(region=region_tuple)
            if sys.platform == "darwin" or image_is_gray(img):
                if prev_status not in [WAITING, BONUS_NOT_REACHED]:
                    log(f"waiting for fish, check took {time.time() - t0:.2f} seconds.")
                return WAITING, box
        except Exception as e:
            print(f"Erro ao capturar ou analisar a tela: {e}")
            return None, None
    
    box = check(STANDBY, confidence=0.8)
    if box:
        if prev_status != STANDBY:
            log(f"standby, check took {time.time() - t0:.2f} seconds.")
        return STANDBY, box
    
    box = check(PICK)
    if box:
        if prev_status != PICK:
            log(f"escolha um item, check took {time.time() - t0:.2f} seconds.")
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
    global boxes
    
    if 'boxes' not in globals() or READY not in boxes:
        boxes = {}
    
    # Verifica se todas as chaves necessárias estão no dicionário boxes
    for status in [STANDBY, WAITING, READY, PULLING, INTERRUPTED_LAIR, INTERRUPTED_PARTY, INTERRUPTED_RAID, TALK, PICK]:
        box = check(status)
        if box:
            boxes[status] = box
            
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
            time.sleep(1)
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
            log(f"número de tentativas de pesca: {fishing_attempted}")
        elif status == READY and time.time() - last_fish_up_time > 10:
            activate_diablo()
            p.sleep(0.1)
            click_box(box)
            p.sleep(0.1)
            status = PULLING
            t = time.time()
            bar_or_bounds_not_found_time = time.time()
            while time.time() - t < MAX_FISHING_TIME and time.time() - bar_or_bounds_not_found_time < MAX_TIMEOUT:
                if pull(box):  # Se o puxão foi bem-sucedido\n
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
        error += click_image("trade", time.time(), 5)
        time.sleep(1)
        error += click_image("select", time.time(), 3, confidence=0.30)
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
        log("comprando iscas...")
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
    if stop is None:
        def stop():
            return False
    # if tries == 0:
    #     return False
    stuck_count = 0
    activate_diablo()

    stage = "opening_map"
    prev_stage = ""
    destination = "bs" if tries > 0 else "fish"  # blacksmith or fish
    t = 0
    minimap_box = Box(x0 + 1700, y0 + 100, 250, 180) if sys.platform == "darwin" else Box(1620, 10, 220, 150)
    npc_box = None
    while True:
        if stop():
            return False
        for status in [INTERRUPTED_LAIR, INTERRUPTED_PARTY, INTERRUPTED_RAID]:
            box = check(status)
            if box:
                click_box(box)
                break
        if box:
            continue

        if stage == "opening_map":
            box = check("find_npc")
            if box:
                click_box(box)
                stage = "find_npc"
            else:
                click_box(minimap_box)
                p.sleep(2)
        elif stage == "find_npc":
            box = check(f"icon_{destination}")
            if box:
                click_box(box)
                stage = "found_npc"
            else:
                scroll_down(x=x0+250+int(random.random()*100), y=y0+400+int(random.random()*200))
        elif stage == "found_npc":
            box = check("navigate")
            if box:
                click_box(box)
                if sys.platform == "win32":
                    p.moveTo(960, 1000)
                stage = "navigating"
                t = time.time()
        elif stage == "navigating":
            p.sleep(2)
            # new_npc_box = find_npc_2(im_data[f"npc_{destination}"])
            new_npc_box = find_npc_3(destination)
            if npc_box and new_npc_box:
                if match_box(npc_box, new_npc_box):
                    stage = "reached_npc"
                    if sys.platform == "win32":
                        boxes.update({f"npc_{destination}": new_npc_box})  # test save npc box
            npc_box = new_npc_box
        elif stage == "reached_npc":
            if destination == "bs":
                stage = "salv"
                destination = "fish"
            else:  # back to fish
                if sys.platform == "win32":
                    DIKeys.press(KEY_MOVE.get(location), 0.3)
                    # p.click(BACK_TO_FISHING_COORD[location], button=p.MIDDLE)  # test: trying to go to the ideal spot
                return True
        elif stage == "npc_name_not_found":
            if destination == "bs" and (sys.platform == "darwin" or boxes.get("npc_bs")):
                stage = "salv_without_box"
                destination = "fish"
            elif destination == "fish":
                if sys.platform == "win32":
                    p.click(BACK_TO_FISHING_COORD[location], button=p.MIDDLE)  # test: trying to go to the ideal spot
                log("Fisher npc not found, possibly blocked by other players. Assuming it reached Fisher npc.")
                return True
        elif stage == "salv" or stage == "salv_without_box":
            if sys.platform == "darwin":
                box = check(TALK)
                if box:
                    click_box(box)
                    stage = "dialog_bs"
            else:
                if stage == "salv":
                    click_center(npc_box)
                else:
                    click_center(boxes.get("npc_bs"))  # test using saved box
                stage = "dialog_bs"
        elif stage == "dialog_bs":
            box = check("services")
            if box:
                click_box(box)
                stage = "salvaging"
        elif stage == "salvaging":
            salvage_attempts_left = 5
            while stage != "salvaged":
                for item_color in ["white", "blue", "yellow"]:
                    box = check(f"{item_color}_unticked")
                    if box:
                        click_box(box)
                    p.sleep(1)
                box = check("salvage", confidence=0.98)
                if not box:
                    box = check("salvage", confidence=0.95)
                if box:
                    click_box(box)
                    p.sleep(1)
                salvage_attempts_left -= 1
                if (check("no_white") and check("no_blue") and check("no_yellow")) or salvage_attempts_left <= 0:
                    stage = "salvaged"
        elif stage == "salvaged":
            box = check("x")
            if box:
                click_box(box)
                stage = "opening_map"
        if prev_stage == stage and stage != "navigating":
            stuck_count += 1
        elif prev_stage != stage:
            stuck_count = 0
        elif stage == "navigating" and time.time() - t > navigation_time_limit:
            if tries > 1:
                stuck_count = stuck_limit + 1
            else:
                stage = "npc_name_not_found"
        prev_stage = stage
        # log(stuck_count)
        log(stage)
        if stuck_count > stuck_limit:
            log(f"salvage got stuck at stage: {stage}, tries left: {tries}")
            while not check("icon_bag"):  # improved logic of returning to normal game screen
                if sys.platform == "darwin":
                    cross_box = check("x", confidence=0.8)
                    if cross_box:
                        click_box(cross_box)
                    else:
                        p.press("space")
                else:
                    DIKeys.press(hexKeyMap.DIK_ESCAPE)
                p.sleep(3)
            # cross_box = check("x", confidence=0.8)
            # if cross_box:
            #     click_box(cross_box)
            # p.sleep(0.5)
            # if sys.platform == "darwin":
            #     p.press("space")
            # else:
            #     p.click(960, 1000)
            # for _ in range(2):
            #     p.sleep(1)
            #     cross_box = check("x", confidence=0.8)
            #     if cross_box:
            #         click_box(cross_box)
            return salvage(location, tries=tries - 1)
        p.sleep(1)


def check_bag_capacity():
    """
    Verifica a capacidade atual da bolsa de itens.

    A função ativa o jogo, clica no ícone da bolsa e captura uma região específica da tela para analisar a
    diferença de brilho, a qual indica a capacidade restante da bolsa.

    Returns:
        float ou None: Valor entre 0.0 e 1.0 representando a capacidade restante da bolsa, ou None
        se não for possível verificar (por exemplo, se a captura da região falhar).
    """
    activate_diablo()
    p.sleep(1)
    box = check("icon_bag")
    if box:
        click_box(box)
        t = time.time()
        p.sleep(3)
        box = check("x")
        while not box and time.time() - t < 10:
            p.sleep(1)
            box = check("x")
        if not box:
            return None
        if sys.platform == "darwin":
            total_h = 76
            # Para macOS, captura uma pequena região da tela e inverte os canais (BGR para RGB)
            im = screenshot(region=(x0 + 1710, y0 + 1290, 1, total_h))[:, :, ::-1]
        else:
            total_h = 70
            im = screenshot(region=(1560, 947, 1, total_h))
        im_array = np.array(im)
        im_gray = np.dot(im_array[:, 0, :3], [0.2989, 0.5870, 0.1140])
        diff = np.diff(im_gray)
        if diff.max() > 15:
            capacity = min(diff.argmax() / total_h + 0.02, 1.0)
        else:
            if im_array[:, 0, 0].mean() > 100:
                capacity = 0.0
            else:
                capacity = 1.0
        click_box(box)
        return capacity
    return None


def alarm_legendary():
    """
    Exibe um alerta informando que há itens lendários que não podem ser coletados.

    A função utiliza o mecanismo de log para notificar que existem itens lendários impossíveis de serem coletados.
    """
    log("há itens lendários que você não pode pegar")


def trade(location):
    """
    Inicia a sequência de troca com o NPC, de acordo com a localização do personagem.

    A função ativa o jogo e, com base na plataforma (macOS ou Windows), utiliza as teclas e movimentos
    apropriados para realizar a troca. Para Windows, são enviadas simulações de pressionamento de teclas
    específicas conforme a localização (por exemplo, 'ashwold', 'bilefen', etc.).

    Args:
        location (str): Nome da localização, que determina as teclas e ações específicas para a troca.
    """
    activate_diablo()
    if sys.platform == "darwin":
        key_to_npc, key_to_fish = KEY_MOVE[location]
        trade_fish_buy_bait_go_back(key_to_npc, key_to_fish)
    else:
        trade_with_gui()
        if location == "ashwold":
            DIKeys.press(hexKeyMap.DIK_D, 0.5)
            DIKeys.press(hexKeyMap.DIK_W, 1.5)
        elif location == "bilefen":
            activate_diablo()
            DIKeys.press(hexKeyMap.DIK_A, 0.05)
        else:
            DIKeys.press(hexKeyMap.DIK_D, 0.05)
            
def fish_and_trade(location, fish_type, fish_key, auto_salv, salv_capacity, brightness=50, stop=None):
    """
    Integra as operações de pesca e troca.

    Após executar a pesca com os parâmetros fornecidos, a função:
      - Verifica a capacidade da bolsa e, se estiver abaixo do limite (salv_capacity),
        inicia o processo de salvamento automático.
      - Em seguida, inicia a troca com o NPC.

    Args:
        location (str): Localização atual do personagem.
        fish_type (str): Tipo de peixe a ser pescado.
        fish_key (str): Tecla de pesca a ser utilizada.
        auto_salv (bool): Se True, executa o salvamento automático quando a bolsa estiver cheia.
        salv_capacity (int): Percentual mínimo da capacidade da bolsa para disparar o salvamento.
        brightness (int, opcional): Nível de brilho para ajustar a barra. Padrão é 50.
        stop (callable, opcional): Função que retorna True para interromper a operação. Se None, a operação não é interrompida.
    """
    if stop is None:
        def stop():
            return False
    if fish(fish_type, fish_key, brightness, stop):
        p.sleep(1)
        # Verifica a capacidade da bolsa e realiza o salvamento, se necessário
        if auto_salv:
            bag_capacity = check_bag_capacity()
            p.sleep(1)
            if bag_capacity is None:
                log("Falha ao verificar a capacidade da bagagem.")
            else:
                log(f"Capacidade da bolsa verificada: aproximadamente {round(bag_capacity * 100)}% left.")
                if bag_capacity * 100 < salv_capacity:
                    if salvage(location):
                        log("Successfully salvaged items.")
                    else:
                        log("Failed to salvage.")
                p.sleep(1)
        trade(location)
        p.sleep(1)


def auto_fishing(location, fish_type, fish_key=None, auto_salv=False, salv_capacity=25, brightness=50, stop=None):
    """
    Executa um loop contínuo de pesca e troca.

    A função permanece em execução chamando o método fish_and_trade repetidamente, permitindo
    a pesca automatizada. O loop só é interrompido se a função 'stop' retornar True.

    Args:
        location (str): Localização do personagem.
        fish_type (str): Tipo de peixe a ser pescado.
        fish_key (str, opcional): Tecla de pesca a ser utilizada. Se None, utiliza a configuração padrão.
        auto_salv (bool, opcional): Se True, realiza o salvamento automático. Padrão é False.
        salv_capacity (int, opcional): Percentual mínimo da capacidade da bolsa para acionar o salvamento. Padrão é 25.
        brightness (int, opcional): Nível de brilho para ajustar a barra. Padrão é 50.
        stop (callable, opcional): Função que retorna True para interromper o loop. Se None, o loop é infinito.
    """
    if stop is None:
        def stop():
            return False
    while True:
        try:
            fish_and_trade(location, fish_type, fish_key, auto_salv, salv_capacity, brightness, stop)
            if stop():
                break
        except p.FailSafeException:
            # Registrar o erro
            log("Fail-safe do PyAutoGUI acionado. Reposicionando o mouse para o centro e continuando...")
            # Mover o mouse para o centro da tela
            largura_tela, altura_tela = p.size()
            p.moveTo(largura_tela // 2, altura_tela // 2)
            # Aguardar um momento antes de continuar
            p.sleep(2)


if __name__ == '__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] in ["bilifen", "ashwold", "tundra"]:
            location = sys.argv[1]
        else:
            location = "tundra"
        if len(sys.argv) > 2 and sys.argv[2] in ["white", "blue", "yellow"]:
            fish_type = sys.argv[2]
        else:
            fish_type = "yellow"
        auto_fishing(location, fish_type, auto_salv=True)
    else:
        import threading
        root = GUI()
        log = root.log

        def start_auto_fishing():
            """
            Inicia o processo de pesca automática em uma thread separada.
            
            Configura os parâmetros de pesca a partir da interface gráfica e atualiza os estados dos botões.
            """
            root.not_fishing = False
            if sys.platform == "darwin":
                fish_key_bind = None
            else:
                fish_key_bind = root.get_fishing_key(hexKeyMap.DI_KEYS)
                if fish_key_bind is None:
                    return 1
            args = (root.loc_var.get(), root.type_var.get(), fish_key_bind, root.auto_salv_var.get(),
                    root.salv_capacity_var.get(), root.bright_var.get(), lambda: root.not_fishing)
                        
            root.thread = threading.Thread(target=auto_fishing, args=args, daemon=True)
            root.thread.start()
            root.auto_fish_button.config(text="Stop Fishing", command=lambda: stop_auto_fishing())
            root.reset_button["state"] = "disabled"
            root.trade_button["state"] = "disabled"
            root.salv_button["state"] = "disabled"
            root.attack_button["state"] = "disabled"
     


        def stop_auto_fishing():
            """
            Interrompe a pesca automática, aguarda a thread finalizar e reativa os botões da interface.
            """
            root.not_fishing = True
            root.thread.join()
            root.auto_fish_button.config(text="Auto Fishing", command=lambda: start_auto_fishing())
            root.reset_button["state"] = "normal"
            root.trade_button["state"] = "normal"
            root.salv_button["state"] = "normal"
            root.attack_button["state"] = "normal"

        def auto_salv():
            """
            Inicia o processo de salvamento automático em uma thread separada.
            
            Atualiza os botões da interface durante a operação de salvamento.
            """
            root.not_fishing = False
            args = (root.loc_var.get(), 3, 30, 60, lambda: root.not_fishing)
            root.thread = threading.Thread(target=salvage, args=args, daemon=True)
            root.thread.start()
            root.salv_button.config(text="Stop Salvaging", command=lambda: stop_salv())
            root.auto_fish_button["state"] = "disabled"
            root.trade_button["state"] = "disabled"
            root.reset_button["state"] = "disabled"

        def stop_salv():
            """
            Interrompe o salvamento automático, aguarda a thread finalizar e reativa os botões da interface.
            """
            root.not_fishing = True
            root.thread.join()
            root.salv_button.config(text="Auto Salvage", command=lambda: auto_salv())
            root.auto_fish_button["state"] = "normal"
            root.trade_button["state"] = "normal"
            root.reset_button["state"] = "normal"
            
                    
        def start_auto_attack():
            """
            Inicia o processo de ataque automático em uma thread separada.
            
            Configura os parâmetros de ataque a partir da interface gráfica e atualiza os estados dos botões.a2 3 s3sss sss1ssss sssss
            """
            root.not_fishing = False
            root.attack_threads = []
            
            # Iniciar thread de ataque primário (corrigido o '4' no início da linha)
            primary_thread = threading.Thread(target=auto_primary_attack, args=(lambda: root.not_fishing,), daemon=True)
            primary_thread.start()
            root.attack_threads.append(primary_thread)
            
            # Iniciar thread de ataque primário (corrigido o '4' no início da linha)
            cura_thread = threading.Thread(target=auto_cura, args=(lambda: root.not_fishing,), daemon=True)
            cura_thread.start()
            root.attack_threads.append(cura_thread)
            
            # Iniciar thread de habilidades
            skills_thread = threading.Thread(target=auto_attack, args=(lambda: root.not_fishing,), daemon=True)
            skills_thread.start()
            root.attack_threads.append(skills_thread)
            
            # Atualiza os botões da interface
            root.attack_button.config(text="Stop Attack", command=lambda: stop_auto_attack())
            root.auto_fish_button["state"] = "disabled"
            root.reset_button["state"] = "disabled"
            root.trade_button["state"] = "disabled"
            root.salv_button["state"] = "disabled"

            
            
            # Thread para pressionar espaço constantemente
        def auto_primary_attack(stop=None):
            """
            Pressiona constantemente a tecla de espaço (ataque primário).
            
            Args:
                stop (callable, opcional): Função que retorna True para interromper o loop.
            """
            if stop is None:
                def stop():
                    return False
                    
            while not stop():
                DIKeys.press(hexKeyMap.DIK_SPACE, 0.01)
                p.sleep(0.3)
        def auto_cura(stop=None):
            if stop is None:
                def stop():
                    return False
                    
            while not stop():
                DIKeys.press(hexKeyMap.DIK_Q, 0.01)
                p.sleep(3)
            
        def auto_attack(stop=None):
            """
            Executa o loop de ataque automático.
            
            Args:
                stop (callable, opcional): Função que retorna True para interromper o loop.
            """
            if stop is None:
                def stop():
                    return False
                    
            try:
                activate_diablo()
            except Exception as e:
                print(f"Aviso: Não foi possível ativar a janela do Diablo: {e}")
                
            while not stop():
                # Lógica de ataque automático aqui
                # Por exemplo:
                p.sleep(2)
                DIKeys.press(hexKeyMap.DIK_2, 0.01)  # Tecla 2
                p.sleep(0.2)
                DIKeys.press(hexKeyMap.DIK_3, 0.01)  # Tecla 3
                p.sleep(0.2)
                DIKeys.press(hexKeyMap.DIK_1, 0.01)  # Tecla 1
                p.sleep(0.2)
                DIKeys.press(hexKeyMap.DIK_4, 0.01)  # Tecla 4
                p.sleep(0.2)
                
                # Verificar interrupções como em outras funções
                for status in [INTERRUPTED_LAIR, INTERRUPTED_PARTY, INTERRUPTED_RAID]:
                    box = check(status)
                    if box:
                        click_box(box)
                        break
            
            
            
        def stop_auto_attack():
            """
            Interrompe o ataque automático, aguarda a thread finalizar e reativa os botões da interface.
            """
            root.not_fishing = True
            
            # Aguardar todas as threads de ataque terminarem
            for thread in root.attack_threads:
                if thread.is_alive():
                    thread.join()
            
            root.attack_button.config(text="Auto Attack", command=lambda: start_auto_attack())
            root.auto_fish_button["state"] = "normal"
            root.reset_button["state"] = "normal"
            root.trade_button["state"] = "normal"
            root.salv_button["state"] = "normal"
            
        root.reset_button.config(command=lambda: reset_game_ui_positions())
        root.trade_button.config(command=lambda: trade(root.loc_var.get()))
        root.auto_fish_button.config(command=lambda: start_auto_fishing())
        root.attack_button.config(command=lambda: start_auto_attack())
        root.salv_button.config(command=lambda: auto_salv())

        if sys.platform == "win32":
            for title in p.getAllTitles():
                if title.endswith("py.exe") or "python" in title:
                    p.getWindowsWithTitle(title)[0].minimize()

        root.lift()
        root.attributes('-topmost', True)
        root.after_idle(root.attributes, '-topmost', False)

        root.mainloop()
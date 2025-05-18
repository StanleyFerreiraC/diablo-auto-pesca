import collections, sys, os, random, time, json
from datetime import datetime

DIR = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))

try:
    from pytesseract import pytesseract
    import pyautogui as p
    import numpy as np
except ImportError:
    import subprocess
    subprocess.run(["python", "-m", "pip", "install", "-r", os.path.join(DIR, "requirements.txt")])
    import pyautogui as p
    import numpy as np
    from pytesseract import pytesseract

Box = collections.namedtuple('Box', 'left top width height')

RESOURCES_DIR = os.path.join(DIR, "resources")
RESOURCES_TEMPEST_DIR = os.path.join(DIR, "resources/tempest")
TEMP_DIR = os.path.join(DIR, "temp_im")

STANDBY = 's'           # não em estado de pesca
WAITING = 'w'           # pesca pré-estágio 1, esperando a fisgada do peixe
BONUS_NOT_REACHED = 'b' # taxa de bônus não atingiu amarelo
READY = 'r'             # pesca pré-estágio 3, pronto para pescar
PULLING = 'p'           # palco principal da pesca, puxando os peixes para cima
INTERRUPTED_LAIR = 'l'  # interrompido pela navegação automática do covil
INTERRUPTED_PARTY = 'i' # interrompido por convite para festa
INTERRUPTED_RAID = 'd'  # interrompido por convite de ataque
TALK = 't'              # quando a conversa do npc estiver disponível
PICK = 'k'              # quando a coleta de itens estiver disponível

im_data = {
    STANDBY:            os.path.join(RESOURCES_DIR, "standby.png"),
    WAITING:            os.path.join(RESOURCES_DIR, "not_ready.png"),
    READY:              os.path.join(RESOURCES_DIR, "pull.png"),
    PULLING:            os.path.join(RESOURCES_DIR, "pulling.png"),
    INTERRUPTED_LAIR:   os.path.join(RESOURCES_DIR, "cancel_lair.png"),
    INTERRUPTED_PARTY:  os.path.join(RESOURCES_DIR, "cancel.png"),
    INTERRUPTED_RAID:   os.path.join(RESOURCES_DIR, "cancel.png"),
    TALK:               os.path.join(RESOURCES_DIR, "talk.png"),
    PICK:               os.path.join(RESOURCES_DIR, "pick.png"),
    "npc":              os.path.join(RESOURCES_DIR, "npc.png"),
    "trade":            os.path.join(RESOURCES_DIR, "trade.png"),
    "select":           os.path.join(RESOURCES_DIR, "select_all.png"),
    "exchange":         os.path.join(RESOURCES_DIR, "exchange.png"),
    "x":                os.path.join(RESOURCES_DIR, "x.png"),
    "shop":             os.path.join(RESOURCES_DIR, "shop.png"),
    "amount":           os.path.join(RESOURCES_DIR, "amount.png"),
    "9":                os.path.join(RESOURCES_DIR, "number9.png"),
    "buy":              os.path.join(RESOURCES_DIR, "buy.png"),
    "find_npc":         os.path.join(RESOURCES_DIR, "find_npc.png"),
    "navigate":         os.path.join(RESOURCES_DIR, "navigate.png"),
    "icon_fish":        os.path.join(RESOURCES_DIR, "icon_fish.png"),
    "icon_bs":          os.path.join(RESOURCES_DIR, "icon_bs.png"),
    "npc_fish":         os.path.join(RESOURCES_DIR, "npc_fish.png"),
    "npc_bs":           os.path.join(RESOURCES_DIR, "npc_bs.png"),
    "services":         os.path.join(RESOURCES_DIR, "services.png"),
    "white_unticked":   os.path.join(RESOURCES_DIR, "white_unticked.png"),
    "blue_unticked":    os.path.join(RESOURCES_DIR, "blue_unticked.png"),
    "yellow_unticked":  os.path.join(RESOURCES_DIR, "yellow_unticked.png"),
    "no_white":         os.path.join(RESOURCES_DIR, "no_white.png"),
    "no_blue":          os.path.join(RESOURCES_DIR, "no_blue.png"),
    "no_yellow":        os.path.join(RESOURCES_DIR, "no_yellow.png"),
    "salvage":          os.path.join(RESOURCES_DIR, "salvage.png"),
    "icon_bag":         os.path.join(RESOURCES_DIR, "icon_bag.png"),
    "pull":             os.path.join(RESOURCES_DIR, "pull.png"),
    "ataque_fluido":    os.path.join(RESOURCES_TEMPEST_DIR, "ataque_fluido.png"),
    "surf":             os.path.join(RESOURCES_TEMPEST_DIR, "surf.png"),
    "furia":            os.path.join(RESOURCES_TEMPEST_DIR, "furia.png"),
    "cruzados":         os.path.join(RESOURCES_TEMPEST_DIR, "cruzados.png"),

}

FISH_TYPE_COLOR = (125, 125, 100)
FISH_TYPE_X_COORD_TOLERANCE = 100
TESSERACT_CONFIG = "-c tessedit_char_whitelist=aBceFhlkimrst"
if os.path.exists("../resources/tesseract_path.txt"):
    with open("../resources/tesseract_path.txt", 'r') as f:
        path_ = f.readline().strip().replace("\\", "/")
        if path_.endswith(".exe"):
            TESSERACT_PATH_WIN32 = path_
        else:
            TESSERACT_PATH_WIN32 = os.path.join(path_, "tesseract.exe")
else:
    TESSERACT_PATH_WIN32 = "C:/Program Files/Tesseract-OCR/tesseract.exe"

if sys.platform == 'darwin':
    from locate_im import locate_on_screen, pixel_match_color, screenshot, locate
    import subprocess
    FISH_TYPE_X_COORD = {"white": 0, "blue": 910, "yellow": 1047}
    FISH_TYPE_Y_COORD = 137
    MAX_FISHING_TIME = 20
    MAX_TIMEOUT = 2
    KEY_MOVE = {'bilefen': ('w', 's'), 'tundra': ('w', 's'), 'ashwold': ('a', 'w')}
    NPC_NAME_COLOR = (230, 190, 135)

    pos = subprocess.run(["osascript", "-e",
                          'tell application "System Events" to tell process "Diablo Immortal" to get position of window 1'],
                         stdout=subprocess.PIPE)
    x0, y0 = [int(n) for n in pos.stdout.decode("utf-8").strip().split(", ")]
    x0, y0 = x0 * 2, y0 * 2

    regions = {
        INTERRUPTED_LAIR: (x0 + 735, y0 + 945, 180, 40),
        INTERRUPTED_PARTY: (x0 + 760, y0 + 1255, 225, 45),
        INTERRUPTED_RAID: (x0 + 760, y0 + 1255, 225, 45),
        PULLING: (x0 + 528, y0 + 200, 83, 31),
        READY: (x0 + 1800, y0 + 1100, 230, 230),
        WAITING: (x0 + 1800, y0 + 1100, 230, 230),
        STANDBY: (x0 + 1540, y0 + 860, 100, 100),
        TALK: (x0 + 1540, y0 + 860, 100, 100),
        PICK: (x0 + 1540, y0 + 860, 100, 100)
    }

    window = None

else:
    # assume windows
    import DIKeys, hexKeyMap
    locate_on_screen, pixel_match_color, screenshot, locate = p.locateOnScreen, p.pixelMatchesColor, p.screenshot, p.locate

    FISH_TYPE_X_COORD = {"white": 0, "blue": 826, "yellow": 955}
    FISH_TYPE_Y_COORD = 75
    MAX_FISHING_TIME = 40
    MAX_TIMEOUT = 5
    PICKUP_LIMIT = 10
    NPC_NAME_COLOR = (248, 198, 134)
    KEY_MOVE = {'bilefen': hexKeyMap.DIK_S, 'tundra': hexKeyMap.DIK_S, 'ashwold': hexKeyMap.DIK_D}
    BACK_TO_FISHING_COORD = {'bilefen': (970, 670), 'tundra': (1100, 670), 'ashwold': (1400, 385)}

    window = p.getWindowsWithTitle("Diablo Immortal")[0]
    x0, y0 = window.left, window.top
    boxes = {}

    if os.path.exists(os.path.join(RESOURCES_DIR, "regions.json")):
        try:
            with open(os.path.join(RESOURCES_DIR, "regions.json"), 'r') as f:
                regions = json.load(f)
        except:
            regions = {}
    else:
        regions = {}


def clear_temp_screenshots():
    """
    Remove capturas de tela temporárias do diretório atual e recria o diretório de armazenamento temporário.
    """
    for filename in os.listdir(os.getcwd()):
        if "screenshot" in filename:
            os.unlink(os.path.join(os.getcwd(), filename))
    if not os.path.exists(TEMP_DIR):
        os.mkdir(TEMP_DIR)

def reset_game_ui_positions():
    """
    Remove o arquivo JSON que armazena as posições da interface do usuário no jogo, resetando as posições salvas.
    """
    file_path = os.path.join(RESOURCES_DIR, "regions.json")
    if os.path.exists(file_path):
        os.unlink(file_path)

def activate_diablo():
    """
    Ativa a janela do jogo 'Diablo Immortal'.
    Se rodando no macOS, utiliza AppleScript para ativar a aplicação.
    Se rodando no Windows, ativa a janela diretamente.
    """
    if sys.platform == "darwin":
        result = subprocess.run(["osascript", "get_active_window.scpt"], stdout=subprocess.PIPE)
        if result.stdout.decode("utf-8").strip() != "Immortal":
            subprocess.run(["osascript", "-e", 'tell application "Diablo Immortal" to activate'])
            p.sleep(0.3)
    else:
        window.activate()

def click_box(box: Box, clicks=1, interval=0.01, button=p.PRIMARY,
              offset_left=0.2, offset_top=0.2, offset_right=-0.2, offset_bottom=-0.2):
    """
    Simula um clique em uma região da tela representada por um objeto Box.
    
    Args:
        box (Box): Área da tela onde o clique será realizado.
        clicks (int, optional): Número de cliques a serem executados. Padrão é 1.
        interval (float, optional): Intervalo entre cliques múltiplos. Padrão é 0.01s.
        button (str, optional): Botão do mouse a ser clicado (ex: PRIMARY, SECONDARY). Padrão é PRIMARY.
        offset_left (float, optional): Offset percentual à esquerda da caixa. Padrão é 0.2.
        offset_top (float, optional): Offset percentual no topo da caixa. Padrão é 0.2.
        offset_right (float, optional): Offset percentual à direita da caixa. Padrão é -0.2.
        offset_bottom (float, optional): Offset percentual na parte inferior da caixa. Padrão é -0.2.
    """
    left = box.left + offset_left * box.width
    width = box.width * (1 - offset_left + offset_right)
    top = box.top + offset_top * box.height
    height = box.height * (1 - offset_top + offset_bottom)
    x = left + random.random() * width
    y = top + random.random() * height
    if sys.platform == "darwin":
        x, y = x // 2, y // 2
    else:
        x, y = int(x), int(y)
    p.click(x, y, clicks=clicks, interval=interval, button=button)

def cast_fishing_rod(key, box):
    """
    Simula o lançamento da vara de pesca no jogo.
    
    Args:
        key (str): Tecla a ser pressionada para lançar a vara de pesca.
        box (Box): Área da tela onde a ação deve ocorrer.
    
    Raises:
        KeyError: Se a tecla fornecida não for válida.
    """
    print(box)
    if key == "mouseRight":
        click_box(box, button=p.SECONDARY)
    else:
        if key not in hexKeyMap.DI_KEYS:
            raise KeyError(f"The key {key} is not an accepted keyboard key.")
        DIKeys.press(hexKeyMap.DI_KEYS[key])

def image_is_gray(image_or_box, threshold=5):
    """
    Verifica se uma imagem é predominantemente cinza.
    
    Args:
        image_or_box: Imagem a ser analisada ou um objeto Box para capturar a região.
        threshold (int, optional): Tolerância para considerar uma imagem cinza. Padrão é 5.
    
    Returns:
        bool: True se a imagem for cinza, False caso contrário.
    """
    if isinstance(image_or_box, Box):
        # Se for um objeto Box, captura a região correspondente
        image = screenshot(region=(image_or_box.left, image_or_box.top, image_or_box.width, image_or_box.height))
    else:
        # Se já for uma imagem, usa diretamente
        image = image_or_box
        
    return (np.abs(np.diff(np.array(image)[:, :, :3], axis=2)) < threshold).all()  # gray if R,G,B are all the same

 


def check(im_name, confidence=0.8, region=None, region_boarder_x=0, region_boarder_y=0):
    """
    Verifica se uma imagem está presente na tela.
    
    Args:
        im_name (str): Nome da imagem a ser procurada ou uma constante que mapeia para um caminho de imagem.
        confidence (float, opcional): Nível de confiança para a correspondência. Padrão é 0.8.
        region (tuple, opcional): Região da tela para procurar (x, y, largura, altura).
        region_boarder_x (int, opcional): Borda adicional em x para a região. Padrão é 0.
        region_boarder_y (int, opcional): Borda adicional em y para a região. Padrão é 0.
    
    Returns:
        Box ou None: Objeto Box representando a região onde a imagem foi encontrada, ou None se não encontrada.
    """
    # Obtém o caminho da imagem do dicionário im_data se im_name for uma chave
    image_path = im_data.get(im_name, im_name)
    
    # Se im_name não estiver no dicionário, assume que é o próprio caminho ou nome do arquivo
    if image_path == im_name and im_name in im_data:
        image_path = im_data[im_name]
    
    try:
        # Verifica se a região específica para esta imagem está definida
        if region is None and im_name in regions:
            region = regions[im_name]
        
        box = locate_on_screen(image_path, region=region, confidence=confidence)
        if box and (region_boarder_x > 0 or region_boarder_y > 0):
            box = Box(box.left - region_boarder_x, box.top - region_boarder_y,
                    box.width + 2 * region_boarder_x, box.height + 2 * region_boarder_y)
        return box
    except Exception as e:
        return None


def match_box(box1: Box, box2: Box, max_diff=5):
    return (np.abs(np.array([[1, 0, 0, 0],
                             [0, 1, 0, 0],
                             [1, 0, 1, 0],
                             [0, 1, 0, 1]]).dot(np.array(box1) - np.array(box2))) <= max_diff).all()


def scroll_down(x, y, amount=200):
    if sys.platform == "darwin":
        p.moveTo(x // 2, y // 2 + 200)
        p.sleep(0.1)
        p.drag(yOffset=-amount, duration=0.3 + 0.2 * random.random(), button='left')
    else:
        p.moveTo(x, y)
        p.sleep(0.1)
        p.scroll(-1, x=x, y=y)


def click_image(im_state, start_time, max_time, clicks=1, interval=0.01, confidence=0.9, region_boarder_x=10,
                region_boarder_y=10, offset=(0.2, 0.2, -0.2, -0.2)):
    while True:
        box = check(im_state, confidence=confidence,
                    region_boarder_x=region_boarder_x, region_boarder_y=region_boarder_y)
        if not box:
            box = check(im_state, confidence=confidence - 0.02,
                        region_boarder_x=region_boarder_x, region_boarder_y=region_boarder_y)
        if box:
            p.sleep(1)
            click_box(box, clicks, interval, offset_left=offset[0], offset_top=offset[1],
                      offset_right=offset[2], offset_bottom=offset[3])
            return 0  # success
        if time.time() - start_time > max_time:
            return 1  # fail


def click_center(box):
    x = box.left + box.width // 2
    y = box.top + box.height // 2
    p.click(x, y)


def find_npc(npc_color_rgb=np.array(NPC_NAME_COLOR)):
    im = p.screenshot()
    matches = np.argwhere((np.abs(np.array(im)[:, :, :3] - npc_color_rgb) <= 5).all(axis=2))
    print(matches.shape)
    if matches.shape[0] > 20:
        position = np.median(matches, axis=0)[::-1]
        return int(position[0]), int(position[1]) + 20


def find_npc_2(npc_name_im, npc_color_rgb=np.array(NPC_NAME_COLOR)):
    # if sys.platform == "darwin":
    #     find_region = (x0, y0, 2100, 1630)
    #     color_threshold = 40  # could tune higher or lower depending on brightness.
    #     rgb_image = False  # screenshot uses opencv for macos, image in BGR mode.
    # else:
    #     find_region = None
    #     color_threshold = 30  # could tune higher or lower depending on brightness.
    #     rgb_image = True
    # im_array = np.array(screenshot(region=find_region))  # uses Pillow for windows, so image in RGB mode
    # if rgb_image:
    #     im_array = im_array[:, :, ::-1]  # convert RGB to BGR
    # im_array[np.where((np.abs(im_array - npc_color_rgb[::-1]) >= color_threshold).any(axis=2))] = np.array([0, 0, 0])
    im_array = extract_color_from_screen(npc_color_rgb)
    # from PIL import Image
    # Image.fromarray(im_array[:,:,::-1]).save("npc_im_black.png")
    return locate(npc_name_im, im_array, confidence=0.5)


def find_npc_3(npc_name, npc_color_rgb=np.array(NPC_NAME_COLOR), config=TESSERACT_CONFIG, tesseract_path=TESSERACT_PATH_WIN32):
    """
    Detecta a presença do nome de um NPC na tela usando OCR.
    
    Esta função utiliza o Tesseract OCR para detectar e localizar o nome de um NPC, seja "Fisher" ou "Blacksmith",
    com base no 'npc_name' fornecido. Ele processa uma imagem de tela para extrair dados de texto e identificar se os NPCs
    o nome completo está presente. Se o Tesseract OCR não estiver disponível, ele retornará à detecção baseada em imagem.
    
    Argumentos:
    npc_name (str): Abreviação do nome do NPC, como "fish" para "Fisher" ou "bs" para "Blacksmith".
    npc_color_rgb (np.ndarray, opcional): matriz de cores RGB para filtrar a imagem da tela. O padrão é NPC_NAME_COLOR.
    config (str, opcional): string de configuração do Tesseract para personalizar o comportamento do OCR. O padrão é TESSERACT_CONFIG.
    tesseract_path (str, opcional): Caminho para o executável Tesseract. O padrão é TESSERACT_PATH_WIN32.
    
    Retorna:
    Box or None: Retorna uma caixa chamada tupla que representa a posição e o tamanho do nome do NPC detectado, se encontrado;
    caso contrário, Nenhum se o nome do NPC não for detectado ou o Tesseract não for 
    """

    full_name = {"fish": "Fisher", "bs": "Ferretre"}[npc_name]
    im_array = extract_color_from_screen(npc_color_rgb)
    # config = "-c tessedit_char_whitelist=aBceFhlkimrst"
    if sys.platform == "win32":
        pytesseract.tesseract_cmd = tesseract_path
    try:
        outputs = pytesseract.image_to_data(im_array, config=config, output_type=pytesseract.Output.DICT)
        print(outputs)
        if full_name in outputs["text"]:
            i_row = outputs["text"].index(full_name)
            return Box(outputs["left"][i_row], outputs["top"][i_row] + 20, outputs["width"][i_row], outputs["height"][i_row])
    except pytesseract.TesseractNotFoundError:
        log("Tesseract not installed. Follow the instruction on the project homepage.")
        return locate(im_data[f"npc_{npc_name}"], im_array, confidence=0.5)


def extract_color_from_screen(color_rgb: np.ndarray):
    if sys.platform == "darwin":
        find_region = (x0, y0, 2100, 1630)
        color_threshold = 40  # could tune higher or lower depending on brightness.
        rgb_image = False  # screenshot uses opencv for macos, image in BGR mode.
    else:
        find_region = None
        color_threshold = 30  # could tune higher or lower depending on brightness.
        rgb_image = True
    im_array = np.array(screenshot(region=find_region))  # uses Pillow for windows, so image in RGB mode
    if rgb_image:
        im_array = im_array[:, :, ::-1]  # convert RGB to BGR
    im_array[np.where((np.abs(im_array - color_rgb[::-1]) >= color_threshold).any(axis=2))] = np.array([0, 0, 0])
    return im_array


def log(contents):
    print(f"[{datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')}] {contents}")
